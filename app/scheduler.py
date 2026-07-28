"""
Background scheduler for monthly invoice auto-send.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from service import send_invoice
from service import should_auto_send

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_scheduled_send():
    """
    Attempt auto-send when the configured day has arrived.
    """
    try:
        if not should_auto_send():
            logger.info("Auto-send skipped (not due or already sent).")
            return
        result = send_invoice(force=False)
        logger.info("Auto-send result: %s", result.get("message"))
    except Exception:
        logger.exception("Auto-send failed.")


def start_scheduler():
    """
    Start hourly checks so catch-up works after laptop wake.
    """
    if scheduler.running:
        return
    scheduler.add_job(
        run_scheduled_send,
        trigger="interval",
        hours=1,
        id="invoice_auto_send",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started (hourly catch-up check).")
    run_scheduled_send()


def stop_scheduler():
    """
    Stop the background scheduler.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
