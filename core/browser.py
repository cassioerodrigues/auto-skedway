"""Browser setup with Edge, stealth, and anti-detection."""

from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth

import config

# Stealth instance (reusable)
_stealth = Stealth(
    navigator_languages_override=("pt-BR", "pt", "en-US", "en"),
    navigator_platform_override="Win32",
    navigator_user_agent_override=config.EDGE_USER_AGENT,
    navigator_vendor_override="Google Inc.",
)


def launch_browser(playwright: Playwright, debug: bool = False) -> Browser:
    """Launch Edge browser with anti-detection settings."""
    slow_mo = config.SLOW_MO_DEBUG if debug else config.SLOW_MO_DEFAULT

    browser = playwright.chromium.launch(
        channel=config.BROWSER_CHANNEL,
        headless=False,
        slow_mo=slow_mo,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
        ],
    )
    return browser


def create_context(browser: Browser) -> BrowserContext:
    """Create browser context with realistic settings and stealth applied."""
    context = browser.new_context(
        viewport={"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
        user_agent=config.EDGE_USER_AGENT,
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        permissions=["geolocation"],
        java_script_enabled=True,
        ignore_https_errors=True,
    )

    # Apply stealth to context (patches all pages created from it)
    _stealth.use_sync(context)

    return context


def create_stealth_page(context: BrowserContext) -> Page:
    """Create a new page (stealth already applied via context)."""
    page = context.new_page()

    # Additional anti-detection: override navigator.webdriver
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        // Remove Playwright/automation indicators
        delete window.__playwright;
        delete window.__pw_manual;
    """)

    page.set_default_timeout(config.PAGE_LOAD_TIMEOUT)
    return page


def setup_browser(debug: bool = False):
    """Full browser setup: launch, context, stealth page.

    Returns:
        tuple: (playwright, browser, context, page)
    """
    pw = sync_playwright().start()
    browser = launch_browser(pw, debug=debug)
    context = create_context(browser)
    page = create_stealth_page(context)
    return pw, browser, context, page


def teardown_browser(pw, browser, context):
    """Clean up browser resources."""
    try:
        context.close()
    except Exception:
        pass
    try:
        browser.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass
