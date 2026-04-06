"""Booking logic with desk iteration, fallback, and retry."""

import time
import random

import config
from core.url_builder import build_booking_url, get_target_date
from core.auth import _find_element
from utils.humanize import human_click, human_delay, random_mouse_movement
from utils.logger import ExecutionLogger


def _find_booking_button(page, logger: ExecutionLogger) -> str | None:
    """Find the booking/submit button using multiple selectors.

    Args:
        page: Playwright page object.
        logger: ExecutionLogger instance.

    Returns:
        Matching selector string, or None.
    """
    selector = _find_element(page, config.BOOKING_SUBMIT_SELECTORS, timeout=config.CLICK_TIMEOUT)
    if selector:
        logger.debug(f"Found booking button with selector: {selector}")
    else:
        logger.warning("Could not find booking button with any known selector")
    return selector


def _check_booking_result(page, logger: ExecutionLogger) -> str:
    """Check if the booking was successful after clicking submit.

    Returns:
        'success' — booking confirmed
        'already_booked' — user already has a booking for this period (stop all)
        'desk_unavailable' — this desk is taken (try next desk)
        'failure' — generic failure
    """
    human_delay(2.0, 4.0)

    page_text = ""
    try:
        page_text = page.inner_text("body", timeout=3000)
    except Exception:
        pass

    # Check: user already has a booking for this period → stop entirely
    if "já possui um agendamento" in page_text and "coincidente" in page_text:
        logger.info(f"User already has a booking for this period — no action needed")
        logger.screenshot(page, "already_booked")
        return "already_booked"

    # Check: desk is taken by someone else → try next desk
    if "Colisão de agenda" in page_text or "não está disponível no período" in page_text:
        logger.warning(f"Desk is unavailable (taken by someone else)")
        logger.screenshot(page, "desk_unavailable")
        return "desk_unavailable"

    # Check for success indicators
    success_selectors = [
        "text=sucesso",
        "text=success",
        "text=confirmado",
        "text=confirmed",
        "text=agendado",
        "text=booked",
        ".alert-success",
        ".success-message",
    ]
    success = _find_element(page, success_selectors, timeout=5000)
    if success:
        text = page.locator(success).first.text_content()
        logger.info(f"Booking confirmed: {text}")
        return "success"

    # Check for other failure indicators
    failure_selectors = [
        "text=indisponível",
        "text=unavailable",
        "text=ocupado",
        "text=already booked",
        "text=não disponível",
        "text=erro",
        "text=error",
        ".alert-danger",
        ".error-message",
    ]
    failure = _find_element(page, failure_selectors, timeout=3000)
    if failure:
        text = page.locator(failure).first.text_content()
        logger.warning(f"Booking failed: {text}")
        return "failure"

    logger.warning("Booking result is ambiguous — could not determine success/failure")
    return "failure"


def attempt_single_booking(
    page,
    desk_id: str,
    days_ahead: int,
    start_time: str,
    end_time: str,
    logger: ExecutionLogger,
    dry_run: bool = False,
    site_params: dict | None = None,
) -> str:
    """Attempt to book a single desk.

    Returns:
        'success' — booking confirmed
        'dry_run_success' — dry run completed
        'already_booked' — user already has a booking (stop all)
        'desk_unavailable' — desk taken by someone else (try next)
        'failure' — generic failure
    """
    url = build_booking_url(desk_id, days_ahead, start_time, end_time, site_params=site_params)
    logger.info(f"Navigating to booking URL for desk {desk_id}")
    logger.debug(f"URL: {url}")

    try:
        page.goto(url, wait_until="networkidle", timeout=config.PAGE_LOAD_TIMEOUT)
    except Exception as e:
        logger.error(f"Failed to load booking page for desk {desk_id}: {e}")
        logger.screenshot(page, f"error_load_{desk_id}")
        return "failure"

    human_delay(1.5, 3.0)
    random_mouse_movement(page)
    logger.screenshot(page, f"booking_page_{desk_id}")

    # Find the booking button
    button_selector = _find_booking_button(page, logger)
    if not button_selector:
        logger.error(f"Booking button not found for desk {desk_id}")
        logger.screenshot(page, f"error_no_button_{desk_id}")
        return "failure"

    logger.screenshot(page, f"before_submit_{desk_id}")

    if dry_run:
        logger.info(f"DRY RUN — would click booking button for desk {desk_id}")
        return "dry_run_success"

    # Click the booking button
    logger.info(f"Clicking booking button for desk {desk_id}")
    try:
        human_click(page, button_selector)
    except Exception as e:
        logger.error(f"Failed to click booking button for desk {desk_id}: {e}")
        logger.screenshot(page, f"error_click_{desk_id}")
        return "failure"

    # Wait and check result
    try:
        page.wait_for_load_state("networkidle", timeout=config.PAGE_LOAD_TIMEOUT)
    except Exception:
        logger.debug("Page load after booking click may be slow")

    logger.screenshot(page, f"result_{desk_id}")
    return _check_booking_result(page, logger)


def book_desk(
    page,
    desk_ids: list[str],
    days_ahead: int,
    start_time: str,
    end_time: str,
    logger: ExecutionLogger,
    dry_run: bool = False,
    site_params: dict | None = None,
) -> dict:
    """Attempt to book a desk from the priority list.

    Iterates through desk IDs in order, trying each one with retries.

    Args:
        page: Playwright page with active session.
        desk_ids: Ordered list of desk IDs (priority order).
        days_ahead: Days ahead for booking date.
        start_time: Booking start time.
        end_time: Booking end time.
        logger: ExecutionLogger instance.
        dry_run: If True, navigate but don't click submit.
        site_params: Per-account site parameters.

    Returns:
        Dict with booking result details.
    """
    target_date = get_target_date(days_ahead)
    desks_attempted = []

    logger.info(f"Starting booking process for date: {target_date}")
    logger.info(f"Time: {start_time} - {end_time}")
    logger.info(f"Desk priority list: {desk_ids}")

    for i, desk_id in enumerate(desk_ids):
        logger.info(f"--- Attempt {i + 1}/{len(desk_ids)}: Desk {desk_id} ---")
        desks_attempted.append(desk_id)

        for retry in range(config.RETRY_PER_DESK):
            if retry > 0:
                delay = random.uniform(config.RETRY_DELAY_MIN, config.RETRY_DELAY_MAX)
                logger.info(f"Retry {retry + 1}/{config.RETRY_PER_DESK} for desk {desk_id} (waiting {delay:.1f}s)")
                time.sleep(delay)

            result = attempt_single_booking(
                page, desk_id, days_ahead, start_time, end_time, logger, dry_run,
                site_params=site_params,
            )

            # User already has a booking for this period — stop entirely
            if result == "already_booked":
                logger.info("User already has a booking — nothing to do")
                return {
                    "result": "already_booked",
                    "booked_desk": None,
                    "target_date": target_date,
                    "desks_attempted": desks_attempted,
                    "attempts": i + 1,
                }

            # Desk taken — skip to next desk (no more retries for this one)
            if result == "desk_unavailable":
                logger.warning(f"Desk {desk_id} is taken — moving to next")
                break

            if result in ("success", "dry_run_success"):
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Booking successful for desk {desk_id}!")
                return {
                    "result": result,
                    "booked_desk": desk_id,
                    "target_date": target_date,
                    "desks_attempted": desks_attempted,
                    "attempts": i + 1,
                }

        else:
            logger.warning(f"All retries exhausted for desk {desk_id} — moving to next")

    logger.error("All desks exhausted — booking failed")
    return {
        "result": "failure",
        "booked_desk": None,
        "target_date": target_date,
        "desks_attempted": desks_attempted,
        "attempts": len(desk_ids),
    }
