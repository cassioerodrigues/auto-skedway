"""Execution runner — orchestrates a single booking run for an account."""

import os
import time

from core.browser import setup_browser, teardown_browser
from core.auth import login
from core.booking import book_desk
from utils.logger import ExecutionLogger


def run_booking(account: dict, debug: bool = False, dry_run: bool = False) -> dict:
    """Execute a full booking flow for a single account.

    Args:
        account: Account dict with credentials, preferences, schedules.
        debug: Enable debug mode (slower, verbose).
        dry_run: Navigate but don't click submit.

    Returns:
        Dict with execution result.
    """
    account_id = account["id"]
    prefs = account.get("preferences", {})
    creds = account.get("credentials", {})

    desk_ids = prefs.get("desks", [])
    days_ahead = prefs.get("days_ahead", 7)
    start_time = prefs.get("start_time", "08:30")
    end_time = prefs.get("end_time", "17:00")
    site_params = prefs.get("site_params")
    timeout = prefs.get("timeout", 300)

    log_base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    logger = ExecutionLogger(base_dir=log_base, debug=debug, account_id=account_id)

    logger.info(f"Starting booking for account: {account.get('label', account_id)}")
    logger.info(f"Desks (priority order): {desk_ids}")
    logger.info(f"Days ahead: {days_ahead} | Time: {start_time} - {end_time}")
    logger.info(f"Dry run: {dry_run}")

    if not desk_ids:
        logger.error("No desks configured for this account")
        logger.save_summary(target_date="N/A", desks_attempted=[], result="no_desks_configured")
        logger.finalize("failed")
        return {"result": "no_desks_configured", "account_id": account_id}

    if not creds.get("user") or not creds.get("passwd"):
        logger.error("Missing credentials for this account")
        logger.save_summary(target_date="N/A", desks_attempted=[], result="missing_credentials")
        logger.finalize("failed")
        return {"result": "missing_credentials", "account_id": account_id}

    pw = None
    browser = None
    context = None
    start_ts = time.time()

    def check_timeout():
        if time.time() - start_ts > timeout:
            raise TimeoutError(f"Execution exceeded {timeout}s timeout")

    try:
        logger.info("Launching browser with stealth mode...")
        pw, browser, context, page = setup_browser(debug=debug)
        logger.info("Browser launched successfully")
        logger.update_summary(target_date=None, desks_attempted=[])

        check_timeout()

        # Login
        logger.info("Starting login flow...")
        login_success = login(page, logger, credentials=creds)
        if not login_success:
            logger.warning("Login failed — retrying...")
            page.goto("about:blank")
            time.sleep(2)
            login_success = login(page, logger, credentials=creds)

        if not login_success:
            logger.error("Login failed after retry — aborting")
            logger.save_summary(target_date="N/A", desks_attempted=[], result="login_failed")
            logger.finalize("failed")
            return {"result": "login_failed", "account_id": account_id}

        logger.update_summary(target_date=None, desks_attempted=[])
        check_timeout()

        # Booking
        result = book_desk(
            page=page,
            desk_ids=desk_ids,
            days_ahead=days_ahead,
            start_time=start_time,
            end_time=end_time,
            logger=logger,
            dry_run=dry_run,
            site_params=site_params,
        )

        logger.update_summary(
            target_date=result["target_date"],
            desks_attempted=result["desks_attempted"],
            result=result["result"],
            booked_desk=result["booked_desk"],
        )

        logger.save_summary(
            target_date=result["target_date"],
            desks_attempted=result["desks_attempted"],
            result=result["result"],
            booked_desk=result["booked_desk"],
        )

        status = "success" if result["result"] in ("success", "dry_run_success") else "failed"
        logger.finalize(status)

        return {**result, "account_id": account_id, "log_dir": logger.log_dir}

    except TimeoutError as e:
        logger.error(str(e))
        try:
            logger.screenshot(page, "timeout")
        except Exception:
            pass
        logger.save_summary(target_date="N/A", desks_attempted=desk_ids, result="timeout")
        logger.finalize("timeout")
        return {"result": "timeout", "account_id": account_id}

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        try:
            logger.screenshot(page, "unexpected_error")
        except Exception:
            pass
        logger.save_summary(target_date="N/A", desks_attempted=desk_ids, result=f"error: {str(e)[:100]}")
        logger.finalize("error")
        return {"result": "error", "account_id": account_id, "error": str(e)}

    finally:
        if pw and browser and context:
            logger.info("Closing browser...")
            teardown_browser(pw, browser, context)
