"""
JSON file storage for config and monthly send history.
"""

import json
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Lock

_APP_DIR = Path(__file__).resolve().parent
_DEFAULT_ROOT = _APP_DIR.parent
DATA_DIR = Path(os.getenv("INVOICE_DATA_DIR", str(_DEFAULT_ROOT / "data")))
GENERATED_DIR = Path(
    os.getenv("INVOICE_GENERATED_DIR", str(_DEFAULT_ROOT / "generated"))
)
CONFIG_PATH = DATA_DIR / "config.json"
SENT_PATH = DATA_DIR / "sent.json"

MAX_SENT_MONTHS = 12

_lock = Lock()


def ensure_dirs():
    """
    Create data and generated directories if missing.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    """
    Load app config from JSON.
    """
    with _lock:
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)


def save_config(config):
    """
    Persist app config to JSON.
    """
    ensure_dirs()
    with _lock:
        with CONFIG_PATH.open("w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
            handle.write("\n")


def load_sent():
    """
    Load monthly send history.
    """
    if not SENT_PATH.exists():
        return {}
    with _lock:
        with SENT_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)


def save_sent(sent):
    """
    Persist monthly send history trimmed to the last 12 months.
    """
    ensure_dirs()
    trimmed = trim_sent_history(sent)
    with _lock:
        with SENT_PATH.open("w", encoding="utf-8") as handle:
            json.dump(trimmed, handle, indent=2)
            handle.write("\n")
    return trimmed


def trim_sent_history(sent):
    """
    Keep only the most recent 12 month keys (YYYY-MM).
    """
    keys = sorted(sent.keys())
    if len(keys) <= MAX_SENT_MONTHS:
        return sent
    keep = keys[-MAX_SENT_MONTHS:]
    return {key: sent[key] for key in keep}


def month_key(dt=None):
    """
    Build YYYY-MM key for a date.
    """
    dt = dt or datetime.now()
    return dt.strftime("%Y-%m")


def was_sent_for_month(key=None):
    """
    Return True if an invoice was already sent for the month.
    """
    key = key or month_key()
    return key in load_sent()


def record_sent(key, invoice_number, pdf_path, recipient, forced=False):
    """
    Record a successful send and trim history to 12 months.
    """
    sent = load_sent()
    sent[key] = {
        "invoice_number": invoice_number,
        "sent_at": datetime.now().isoformat(timespec="seconds"),
        "pdf_path": str(pdf_path),
        "recipient": recipient,
        "forced": forced,
    }
    return save_sent(sent)


def next_invoice_number(config):
    """
    Return the next invoice number without mutating config.
    """
    invoice = config["invoice"]
    number = int(invoice.get("last_number", 0)) + 1
    prefix = invoice.get("prefix", "UWHPL-")
    return number, f"{prefix}{number:04d}"


def bump_invoice_number(config, number):
    """
    Persist the latest used invoice sequence number.
    """
    updated = deepcopy(config)
    updated["invoice"]["last_number"] = number
    save_config(updated)
    return updated
