"""Authentication flow for Skedway login."""

import config
from utils.humanize import human_type, human_delay, human_click, random_mouse_movement
from utils.logger import ExecutionLogger


def _find_element(page, selectors: list, timeout: int = 5000) -> str | None:
    """Try multiple selectors and return the first one that matches.

    Args:
        page: Playwright page object.
        selectors: List of CSS/text selectors to try.
        timeout: Timeout per selector in ms.

    Returns:
        The matching selector string, or None if none matched.
    """
    for selector in selectors:
        try:
            locator = page.locator(selector)
            if locator.count() > 0 and locator.first.is_visible():
                return selector
        except Exception:
            continue

    # Second pass with wait
    for selector in selectors:
        try:
            page.wait_for_selector(selector, state="visible", timeout=timeout)
            return selector
        except Exception:
            continue

    return None


def handle_mobile_warning(page, logger: ExecutionLogger):
    """Dismiss the 'Continue anyway' mobile warning if present."""
    try:
        continue_btn = page.locator(config.CONTINUE_BUTTON_SELECTOR)
        if continue_btn.is_visible(timeout=3000):
            logger.info("Mobile warning detected — clicking 'Continue anyway'")
            logger.screenshot(page, "continue_warning")
            human_click(page, config.CONTINUE_BUTTON_SELECTOR)
            human_delay(1.0, 2.0)
            logger.info("Mobile warning dismissed")
    except Exception:
        logger.debug("No mobile warning found — proceeding")


def login(page, logger: ExecutionLogger) -> bool:
    """Execute the login flow on Skedway.

    Args:
        page: Playwright page with stealth applied.
        logger: ExecutionLogger instance.

    Returns:
        True if login succeeded, False otherwise.
    """
    logger.info(f"Navigating to {config.LOGIN_URL}")
    page.goto(config.LOGIN_URL, wait_until="networkidle", timeout=config.PAGE_LOAD_TIMEOUT)
    logger.screenshot(page, "login_page")

    # Handle mobile warning
    handle_mobile_warning(page, logger)
    human_delay(1.0, 2.0)

    # Simulate human reading the page
    random_mouse_movement(page)

    # Find and fill email field
    email_selector = _find_element(page, config.LOGIN_EMAIL_SELECTORS)
    if not email_selector:
        logger.error("Could not find email/login input field")
        logger.screenshot(page, "error_no_email_field")
        return False

    logger.info("Filling email field")
    human_type(page, email_selector, config.SKEDWAY_USER)
    human_delay(0.5, 1.0)

    logger.screenshot(page, "email_filled")

    # Step 2: Click "Próximo" (Next) button to proceed to password step
    next_selector = _find_element(page, config.LOGIN_NEXT_SELECTORS)
    if not next_selector:
        logger.error("Could not find 'Próximo' / Next button")
        logger.screenshot(page, "error_no_next_button")
        return False

    logger.info("Clicking 'Próximo' button")
    human_click(page, next_selector)

    # Wait for password field to appear
    human_delay(1.5, 3.0)
    try:
        page.wait_for_load_state("networkidle", timeout=config.LOGIN_TIMEOUT)
    except Exception:
        pass

    logger.screenshot(page, "password_step")

    # Step 3: Find and fill password field
    password_selector = _find_element(page, config.LOGIN_PASSWORD_SELECTORS, timeout=config.LOGIN_TIMEOUT)
    if not password_selector:
        logger.error("Could not find password input field after clicking 'Próximo'")
        logger.screenshot(page, "error_no_password_field")
        return False

    logger.info("Filling password field")
    human_type(page, password_selector, config.SKEDWAY_PASSWD)
    human_delay(0.5, 1.5)

    logger.screenshot(page, "password_filled")

    # Step 4: Click login/submit button
    submit_selector = _find_element(page, config.LOGIN_SUBMIT_SELECTORS)
    if not submit_selector:
        logger.error("Could not find login submit button")
        logger.screenshot(page, "error_no_submit_button")
        return False

    logger.info("Clicking login button")
    human_click(page, submit_selector)

    # Wait for navigation after login
    try:
        page.wait_for_load_state("networkidle", timeout=config.LOGIN_TIMEOUT)
        human_delay(2.0, 3.0)
    except Exception as e:
        logger.warning(f"Page load after login may be slow: {e}")

    logger.screenshot(page, "after_login")

    # Validate login success
    current_url = page.url
    if "console.skedway.com" in current_url or "volvo.skedway.com" in current_url:
        # Check if we're no longer on the login page
        login_form_gone = _find_element(page, config.LOGIN_EMAIL_SELECTORS, timeout=2000) is None
        if login_form_gone:
            logger.info(f"Login successful — redirected to: {current_url}")
            return True

    # If still on login page, check for error messages
    error_selectors = [
        ".alert-danger",
        ".error-message",
        ".login-error",
        "text=Invalid",
        "text=incorrect",
        "text=Inválido",
    ]
    error_selector = _find_element(page, error_selectors, timeout=2000)
    if error_selector:
        error_text = page.locator(error_selector).first.text_content()
        logger.error(f"Login failed with error: {error_text}")
    else:
        logger.error(f"Login may have failed — current URL: {current_url}")

    logger.screenshot(page, "login_failed")
    return False
