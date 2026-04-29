"""Auto Skedway — Configuration constants and settings."""

from dotenv import load_dotenv

load_dotenv()


# --- URLs ---
LOGIN_URL = "https://console.skedway.com/"
BOOKING_BASE_URL = "https://volvo.skedway.com/booking-form.php"
BOOKING_SUCCESS_URL = "https://volvo.skedway.com/index.php"

# --- Admin ---
ADMIN_EMAIL = "cassio.rodrigues@volvo.com"

# --- Booking Defaults ---
DEFAULT_DAYS_AHEAD = 7
DEFAULT_START_TIME = "08:30"
DEFAULT_END_TIME = "17:00"

# --- Default Skedway Site Parameters (used if account doesn't specify) ---
DEFAULT_SITE_PARAMS = {
    "base_type": "1",
    "timezone": "America/Sao_Paulo",
    "from": "/booking.php?baseType=1",
    "action": "step1",
    "company_site_id": "2210",
    "building_id": "3933",
    "floor_id": "5847",
    "space_type": "0",
    "order": "availabilityDesc",
    "page": "1",
}

# Legacy flat constants (kept for backward compatibility with tests)
BOOKING_BASE_TYPE = DEFAULT_SITE_PARAMS["base_type"]
BOOKING_TIMEZONE = DEFAULT_SITE_PARAMS["timezone"]
BOOKING_FROM = DEFAULT_SITE_PARAMS["from"]
BOOKING_ACTION = DEFAULT_SITE_PARAMS["action"]
BOOKING_COMPANY_SITE_ID = DEFAULT_SITE_PARAMS["company_site_id"]
BOOKING_BUILDING_ID = DEFAULT_SITE_PARAMS["building_id"]
BOOKING_FLOOR_ID = DEFAULT_SITE_PARAMS["floor_id"]
BOOKING_SPACE_TYPE = DEFAULT_SITE_PARAMS["space_type"]
BOOKING_ORDER = DEFAULT_SITE_PARAMS["order"]
BOOKING_PAGE = DEFAULT_SITE_PARAMS["page"]

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
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36 "
    "Edg/146.0.0.0"
)
