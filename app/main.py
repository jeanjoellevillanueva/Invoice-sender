"""
FastAPI app for invoice config UI and manual resend.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from scheduler import start_scheduler
from scheduler import stop_scheduler
from service import merge_config
from service import send_invoice
from storage import ensure_dirs
from storage import load_config
from storage import load_sent
from storage import month_key
from storage import next_invoice_number
from storage import save_config
from storage import was_sent_for_month

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Start and stop the invoice scheduler with the app.
    """
    ensure_dirs()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Invoice Sender", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def public_config(config=None):
    """
    Return config with SMTP password masked for the UI.
    """
    config = config or load_config()
    safe = dict(config)
    smtp = dict(config.get("smtp", {}))
    smtp["password"] = ""
    smtp["password_set"] = bool(config.get("smtp", {}).get("password"))
    safe["smtp"] = smtp
    number, preview = next_invoice_number(config)
    safe["next_invoice_preview"] = preview
    safe["next_invoice_number"] = number
    safe["current_month"] = month_key()
    safe["already_sent_this_month"] = was_sent_for_month()
    safe["sent_history"] = load_sent()
    return safe


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """
    Render the configuration and resend UI.
    """
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "config": public_config()},
    )


@app.get("/api/config")
def get_config():
    """
    Return masked config and send status.
    """
    return public_config()


@app.put("/api/config")
async def update_config(request: Request):
    """
    Save configuration from the UI.
    """
    payload = await request.json()
    try:
        updated = merge_config(load_config(), payload)
        save_config(updated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return public_config(updated)


@app.post("/api/send")
async def manual_send(request: Request):
    """
    Manually send an invoice for the current or a selected past month.
    """
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    force = bool(body.get("force", False))
    month = body.get("month")
    try:
        result = send_invoice(force=force, month=month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Manual send failed.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(result)


@app.get("/api/status")
def status():
    """
    Return current month send status.
    """
    return {
        "month": month_key(),
        "already_sent": was_sent_for_month(),
        "sent": load_sent(),
        "config": public_config(),
    }
