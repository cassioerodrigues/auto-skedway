"""Auto Skedway — Configuration constants and settings."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


# --- Credentials ---
SKEDWAY_USER = os.getenv("SKEDWAY_USER")
SKEDWAY_PASSWD = os.getenv("SKEDWAY_PASSWD")

# --- URLs ---
LOGIN_URL = "https://console.skedway.com/"
BOOKING_BASE_URL = "https://volvo.skedway.com/booking-form.php"

# --- Booking Defaults ---
DEFAULT_DAYS_AHEAD = 7
DEFAULT_START_TIME = "08:30"
DEFAULT_END_TIME = "17:00"

# --- Skedway Site Parameters ---
BOOKING_BASE_TYPE = "1"
BOOKING_TIMEZONE = "America/Sao_Paulo"
BOOKING_FROM = "/booking.php?baseType=1"
BOOKING_ACTION = "step1"
BOOKING_COMPANY_SITE_ID = "2210"
BOOKING_BUILDING_ID = "3933"
BOOKING_FLOOR_ID = "5847"
BOOKING_SPACE_TYPE = "0"
BOOKING_ORDER = "availabilityDesc"
BOOKING_PAGE = "1"

# --- Timeouts (seconds) ---
PAGE_LOAD_TIMEOUT = 30_000      # 30s in ms (Playwright uses ms)
CLICK_TIMEOUT = 10_000          # 10s in ms
LOGIN_TIMEOUT = 15_000          # 15s in ms
TOTAL_TIMEOUT = 300             # 5 min in seconds
RETRY_PER_DESK = 2
RETRY_DELAY_MIN = 3.0
RETRY_DELAY_MAX = 5.0

# --- Browser ---
BROWSER_CHANNEL = "msedge"
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
SLOW_MO_DEFAULT = 50
SLOW_MO_DEBUG = 200

# --- Selectors ---
CONTINUE_BUTTON_SELECTOR = "text=Continue anyway"
LOGIN_EMAIL_SELECTORS = [
    "input[type='email']",
    "input[name='email']",
    "input[name='login']",
    "#email",
    "#login",
    "input[placeholder*='email' i]",
    "input[placeholder*='login' i]",
]
LOGIN_PASSWORD_SELECTORS = [
    "input[type='password']",
    "input[name='password']",
    "#password",
]
LOGIN_NEXT_SELECTORS = [
    "button:has-text('Próximo')",
    "button:has-text('Next')",
    "button[type='submit']",
    "input[type='submit']",
]
LOGIN_SUBMIT_SELECTORS = [
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('Login')",
    "button:has-text('Entrar')",
    "button:has-text('Sign in')",
    ".btn-primary[type='submit']",
]
BOOKING_SUBMIT_SELECTORS = [
    "button:has-text('Agendar')",
    "button:has-text('Reservar')",
    "button:has-text('Book')",
    "button:has-text('Confirmar')",
    "input[type='submit']",
    "button[type='submit']",
    ".btn-primary:has-text('Agendar')",
    ".btn-primary:has-text('Reservar')",
]

# --- User-Agent ---
EDGE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36 "
    "Edg/146.0.0.0"
)


def validate_credentials():
    """Validate that required environment variables are set."""
    missing = []
    if not SKEDWAY_USER:
        missing.append("SKEDWAY_USER")
    if not SKEDWAY_PASSWD:
        missing.append("SKEDWAY_PASSWD")
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("Set them in your environment or create a .env file.")
        print("See .env.example for reference.")
        sys.exit(1)
