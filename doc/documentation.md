# Auto Skedway — Complete Documentation

**Auto Skedway** is an automated desk booking system for the [Skedway](https://console.skedway.com/) platform. It manages multiple employee accounts, books desks according to configurable preferences and schedules, and provides a web dashboard for management and monitoring.

---

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Directory Structure](#directory-structure)
4. [Configuration](#configuration)
5. [Architecture](#architecture)
6. [API Reference](#api-reference)
7. [Frontend](#frontend)
8. [CLI & Commands](#cli--commands)
9. [Data Models](#data-models)
10. [Deployment](#deployment)
11. [Testing](#testing)
12. [Booking Result Messages](#booking-result-messages)

---

## Overview

Auto Skedway automates the process of reserving a desk on the Skedway platform (Volvo instance). It supports:

- **Multiple accounts** managed through a single service
- **Priority desk lists** — it tries desks in order until one succeeds
- **Cron-based scheduling** — each account has independent schedules
- **Anti-detection** — Playwright with stealth mode (Edge browser, human-like interactions)
- **Full execution logging** — screenshots at every step, JSON summary, text log
- **Web dashboard** — view history, trigger manual runs, manage accounts and schedules

---

## Tech Stack

| Component     | Technology                                |
|---------------|-------------------------------------------|
| Backend       | Python 3.10+, Flask 2.3+                  |
| Automation    | Playwright 1.58+, playwright-stealth 2.0+ |
| Scheduling    | APScheduler 3.10                          |
| Frontend      | HTML5, Vanilla JavaScript, CSS3           |
| Server        | Flask with CORS, ProxyFix (nginx support) |
| Browser       | Microsoft Edge (via Playwright)           |
| Persistence   | JSON file (`accounts.json`) + `.env`      |

### Python Dependencies (`requirements.txt`)

```
playwright>=1.58.0
playwright-stealth>=2.0.0
python-dotenv>=1.0.0
colorama>=0.4.6
flask>=2.3.0
flask-cors>=4.0.0
apscheduler>=3.10.0,<4.0.0
filelock>=3.12.0
```

---

## Directory Structure

```
/srv/auto-skedway/
├── main.py                    # Entry point (CLI + server)
├── config.py                  # Configuration constants
├── accounts.json              # Account definitions (non-sensitive)
├── .env                       # Credentials (ACCOUNT_*_USER/PASSWD)
├── requirements.txt           # Python dependencies
├── README.md                  # Quick-start guide
├── start.sh                   # Background startup script
├── stop.sh                    # Process termination script
├── deploy.sh                  # Full deploy with git pull
├── nginx-config.conf          # Nginx reverse proxy config
│
├── core/                      # Core booking logic
│   ├── __init__.py
│   ├── auth.py                # Login flow (Skedway authentication)
│   ├── booking.py             # Desk booking with retry/fallback logic
│   ├── browser.py             # Browser setup with stealth + anti-detection
│   ├── runner.py              # Orchestrator (login → booking)
│   ├── url_builder.py         # Dynamic booking URL construction
│   ├── account_manager.py     # Account/credential/schedule persistence
│   └── scheduler.py           # APScheduler wrapper, cron job management
│
├── frontend/                  # Web UI
│   ├── api.py                 # Flask API server + static file serving
│   ├── index.html             # Single-page app shell
│   ├── app.js                 # Frontend state, UI rendering, API calls
│   ├── styles.css             # Design (amber + deep navy theme)
│   └── start-server.sh        # Local dev server starter
│
├── utils/                     # Utility modules
│   ├── __init__.py
│   ├── humanize.py            # Human-like interactions (typing, clicks, delays)
│   ├── logger.py              # ExecutionLogger (screenshots + logs)
│   └── date_utils.py          # Date calculations (booking date, weekday checks)
│
├── tests/                     # Unit tests (pytest)
│   ├── test_config.py
│   ├── test_url_builder.py
│   └── test_date_utils.py
│
└── logs/                      # Execution history (created at runtime)
    └── 2026-04-06_160104_1a662a44/
        ├── execution.log      # Text log of run
        ├── summary.json       # Machine-readable summary
        ├── 01_login_page.png
        ├── 02_email_filled.png
        └── ...
```

---

## Configuration

### `config.py` — Application Constants

#### URLs

```python
LOGIN_URL         = "https://console.skedway.com/"
BOOKING_BASE_URL  = "https://volvo.skedway.com/booking-form.php"
BOOKING_SUCCESS_URL = "https://volvo.skedway.com/index.php"
```

#### Default Booking Preferences

```python
DEFAULT_DAYS_AHEAD = 7        # How many days ahead to book
DEFAULT_START_TIME = "08:30"
DEFAULT_END_TIME   = "17:00"
```

#### Site Parameters (Volvo Skedway instance)

```python
DEFAULT_SITE_PARAMS = {
    "base_type":       "1",
    "timezone":        "America/Sao_Paulo",
    "from":            "/booking.php?baseType=1",
    "action":          "step1",
    "company_site_id": "2210",
    "building_id":     "3933",
    "floor_id":        "5847",
    "space_type":      "0",
    "order":           "availabilityDesc",
    "page":            "1",
}
```

#### Timeouts & Retries

| Constant         | Value   | Description                         |
|------------------|---------|-------------------------------------|
| `PAGE_LOAD_TIMEOUT` | 30,000 ms | Playwright page load timeout      |
| `CLICK_TIMEOUT`  | 10,000 ms | Playwright element click timeout    |
| `LOGIN_TIMEOUT`  | 15,000 ms | Max time for login flow             |
| `TOTAL_TIMEOUT`  | 300 s   | Max total execution time per account |
| `RETRY_PER_DESK` | 2       | Retries per desk on generic failure  |
| `RETRY_DELAY_MIN` | 3.0 s  | Minimum delay between retries       |
| `RETRY_DELAY_MAX` | 5.0 s  | Maximum delay between retries       |

#### Browser Settings

```python
BROWSER_CHANNEL  = "msedge"
VIEWPORT_WIDTH   = 1920
VIEWPORT_HEIGHT  = 1080
SLOW_MO_DEFAULT  = 50    # ms delay per action (normal mode)
SLOW_MO_DEBUG    = 200   # ms delay per action (debug mode)
```

---

### `.env` — Credentials

Credentials are stored per-account using the account ID:

```
ACCOUNT_{account_id}_USER=email@company.com
ACCOUNT_{account_id}_PASSWD=password
```

These are loaded at runtime by `account_manager.py` and never stored in `accounts.json`.

---

### `accounts.json` — Account Definitions

```json
{
  "accounts": [
    {
      "id": "1a662a44",
      "label": "Cassio",
      "enabled": true,
      "preferences": {
        "desks": ["81502", "81500", "81498"],
        "days_ahead": 7,
        "start_time": "08:30",
        "end_time": "17:00",
        "site_params": {
          "base_type": "1",
          "timezone": "America/Sao_Paulo",
          "from": "/booking.php?baseType=1",
          "action": "step1",
          "company_site_id": "2210",
          "building_id": "3933",
          "floor_id": "5847",
          "space_type": "0",
          "order": "availabilityDesc",
          "page": "1"
        }
      },
      "schedules": [
        {
          "id": "e4cb4c9a",
          "cron": "0 0 * * 4,5",
          "description": "Quintas e Sextas",
          "enabled": true
        }
      ]
    }
  ]
}
```

#### Current Accounts

| ID         | Label    | Desk Priority                            |
|------------|----------|------------------------------------------|
| `1a662a44` | Cassio   | 81502, 81500, 81498                      |
| `78723bad` | Egon     | 81498, 81500, 81502, 81503, 81501        |
| `3f0cf530` | Leonardo | 81502, 81500, 81498                      |
| `39c21ae3` | Amarildo | 81498, 81499, 81502                      |

---

## Architecture

### Entry Point: `main.py`

The application has two modes:

| Mode | Command | Description |
|------|---------|-------------|
| Server (default) | `python main.py` | Starts Flask API + APScheduler background jobs |
| Single-run | `python main.py --run-once <account_id>` | Runs one account and exits (no server) |

#### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--port N` | `5000` | HTTP server port |
| `--host ADDR` | `0.0.0.0` | Bind address |
| `--debug` | off | Visible browser, verbose output, slower interactions |
| `--dry-run` | off | Navigate but skip final booking submit |
| `--run-once ID` | — | Run single account ID, then exit |

---

### Core Modules

#### `core/auth.py` — Authentication

**Function:** `login(page, logger, credentials) → bool`

**Steps:**
1. Navigate to `LOGIN_URL`
2. Dismiss mobile warning if present ("Continue anyway")
3. Locate and fill the email field (multiple selector fallbacks)
4. Click "Próximo" (Next) button
5. Locate and fill the password field
6. Click login/submit button
7. Validate: check URL changed and login form is gone

**Features:**
- Human-like typing with random per-keystroke delays (40–180 ms)
- Random mouse movements to simulate human reading
- Multiple CSS selector fallbacks for robustness against UI changes
- Screenshot captured at each step

---

#### `core/booking.py` — Booking Logic

**Function:** `book_desk(page, desk_ids, days_ahead, start_time, end_time, logger, dry_run, site_params) → dict`

**Workflow:**
1. Iterate through `desk_ids` in priority order
2. For each desk, attempt up to `RETRY_PER_DESK` times on generic failure
3. Navigate to booking URL (built by `url_builder.py`)
4. Click booking/submit button
5. Parse page response to determine outcome

**Result Decision Tree:**

```
Response contains "já possui um agendamento coincidente"
  → result = already_booked  (STOP — user is already booked)

Response contains "Colisão de agenda" or "não está disponível no período"
  → result = desk_unavailable  (SKIP — try next desk)

Success indicators found (redirect or success text)
  → result = success  (STOP — done)

Otherwise
  → result = failure  (RETRY same desk up to RETRY_PER_DESK times)
```

---

#### `core/runner.py` — Orchestration

**Function:** `run_booking(account, debug=False, dry_run=False) → dict`

**Steps:**
1. Setup browser with stealth (via `browser.py`)
2. Login (via `auth.py`)
3. Book desk using account preferences (via `booking.py`)
4. Teardown browser
5. Save execution summary to `logs/{timestamp}_{account_id}/summary.json`

**Execution Summary (`summary.json`):**

```json
{
  "execution_time": "2026-04-14T00:00:00",
  "account_id": "1a662a44",
  "status": "completed",
  "target_date": "2026-04-21",
  "desks_attempted": ["81502", "81500"],
  "result": "success",
  "booked_desk": "81502",
  "duration_seconds": 42.5,
  "screenshots": 9,
  "screenshot_files": ["01_login_page.png", "02_email_filled.png", "..."]
}
```

---

#### `core/browser.py` — Anti-Detection Setup

Uses `playwright-stealth` with:
- Custom User-Agent (Windows 10, Edge 146)
- Navigator overrides: `language=pt-BR`, `platform=Win32`
- Removes WebDriver property and automation indicators via JS injection
- Viewport: 1920×1080
- Locale: `pt-BR`
- Timezone: `America/Sao_Paulo`

---

#### `core/url_builder.py` — URL Construction

**Function:** `build_booking_url(desk_id, days_ahead, start_time, end_time, site_params) → str`

Constructs the full booking URL. Key parameters:

| Parameter      | Example value               | Description              |
|----------------|-----------------------------|--------------------------|
| `startDate`    | `2026-04-21 08:30`          | Start datetime           |
| `endDate`      | `2026-04-21 17:00`          | End datetime             |
| `day`          | `21/04/2026`                | Date in DD/MM/YYYY       |
| `startTime`    | `08:30`                     | Start time               |
| `endTime`      | `17:00`                     | End time                 |
| `companySiteId`| `2210`                      | Skedway site ID          |
| `buildingId`   | `3933`                      | Building identifier      |
| `floorId`      | `5847`                      | Floor identifier         |
| `spaceId[]`    | `81502`                     | Desk/space ID            |
| `timezone`     | `America/Sao_Paulo`         | Timezone                 |

---

#### `core/account_manager.py` — Persistence Layer

Manages reading and writing `accounts.json` and `.env`.

**Account Functions:**

| Function | Returns | Description |
|----------|---------|-------------|
| `load_accounts()` | `list[dict]` | All accounts with credentials merged |
| `get_account(id)` | `dict \| None` | Single account by ID |
| `add_account(label, desks, ...)` | `dict` | Create and persist new account |
| `update_account(id, updates)` | `dict \| None` | Partial update of account fields |
| `delete_account(id)` | `bool` | Remove account and credentials |
| `set_credentials(id, user, passwd)` | — | Write credentials to `.env` |
| `remove_credentials(id)` | — | Delete credentials from `.env` |
| `verify_credentials(user, passwd)` | `list[str]` | Find matching account IDs |

**Schedule Functions:**

| Function | Returns | Description |
|----------|---------|-------------|
| `add_schedule(account_id, cron, description, enabled)` | `dict` | Add schedule to account |
| `update_schedule(account_id, sched_id, updates)` | `dict \| None` | Update schedule fields |
| `delete_schedule(account_id, sched_id)` | `bool` | Remove schedule |

**Concurrency Safety:** Uses `filelock.FileLock` (10 s timeout) on `accounts.json` writes to prevent race conditions between concurrent executions.

---

#### `core/scheduler.py` — Job Scheduling

Uses **APScheduler** (`BackgroundScheduler`) with `CronTrigger`.

**Functions:**

| Function | Returns | Description |
|----------|---------|-------------|
| `init_scheduler()` | `BackgroundScheduler` | Load all accounts, register cron jobs, start |
| `trigger_run(account_id)` | `dict` | Manually start a booking run immediately |
| `get_active_runs()` | `dict` | Status of in-progress executions |
| `reload_jobs()` | — | Re-read `accounts.json` and refresh all jobs |
| `get_scheduled_jobs()` | `list[dict]` | All jobs with next run times |
| `get_next_run_by_account(account_id)` | `str \| None` | ISO datetime of next scheduled run |

**Cron Conversion:**
Standard 5-field cron is converted to APScheduler format (where `0 = Monday` instead of Sunday):
- Example: `0 0 * * 4,5` (Thursday–Friday) → APScheduler `day_of_week=3,4`

**Concurrency:** Executions run in a `ThreadPoolExecutor` with max 2 concurrent workers.

---

### Utilities

#### `utils/humanize.py`

| Function | Description |
|----------|-------------|
| `human_type(page, selector, text)` | Type with random per-keystroke delays (40–180 ms) |
| `human_delay(min_s, max_s)` | Random sleep, default 0.5–2.0 s |
| `human_click(page, selector)` | Click with slight offset and preceding mouse movement |
| `human_scroll(page, direction, amount)` | Scroll with random variation |
| `random_mouse_movement(page)` | Move mouse to random positions |

#### `utils/logger.py` — ExecutionLogger

- Sequentially numbered screenshot captures (`01_`, `02_`, ...)
- Color-coded console output (via Colorama)
- File logging to `logs/{timestamp}_{account_id}/execution.log`
- Live-updated `summary.json` during execution
- Duration tracking from start to finish

#### `utils/date_utils.py`

| Function | Returns | Description |
|----------|---------|-------------|
| `get_booking_date(days_ahead)` | `str` (YYYY-MM-DD) | Target booking date |
| `get_day_of_week(date_str)` | `int` (0=Mon, 6=Sun) | Day of week for a date |
| `is_weekday(date_str)` | `bool` | Whether the date is Mon–Fri |
| `format_date_display(date_str)` | `str` | Human-readable date string |

---

## API Reference

### Base URL

- **Local dev:** `http://localhost:5000`
- **Via nginx subpath:** `http://<host>/skedway/`

### Authentication

All endpoints (except `/api/health`) require **HTTP Basic Auth**.

- **Credentials:** account email + password
- **Admin user:** `cassio.rodrigues@volvo.com` (defined in `config.ADMIN_EMAIL`)
- **Access control:** Admin can see/manage all accounts; non-admin users can only access their own account

---

### Account Management

#### `GET /api/accounts`
List all accounts the authenticated user can access.

**Response:**
```json
[
  {
    "id": "1a662a44",
    "label": "Cassio",
    "enabled": true,
    "user": "cassio.rodrigues@volvo.com",
    "has_credentials": true,
    "next_run": "2026-04-24T00:00:00",
    "preferences": { "desks": ["81502", "81500", "81498"], "..." },
    "schedules": [{ "id": "e4cb4c9a", "cron": "0 0 * * 4,5", "..." }]
  }
]
```

#### `GET /api/accounts/<id>`
Get a single account by ID.

#### `POST /api/accounts`
Create a new account.

**Body:**
```json
{
  "label": "Name",
  "desks": ["81502", "81500"],
  "days_ahead": 7,
  "start_time": "08:30",
  "end_time": "17:00",
  "user": "email@company.com",
  "passwd": "password"
}
```

#### `PUT /api/accounts/<id>`
Update an existing account (partial update).

**Body:** Any subset of `{label, enabled, desks, days_ahead, start_time, end_time, user, passwd}`

#### `DELETE /api/accounts/<id>`
Delete account and its credentials.

**Response:** `{ "status": "deleted" }`

---

### Schedule Management

#### `GET /api/accounts/<id>/schedules`
List all schedules for an account.

**Response:**
```json
[
  {
    "id": "e4cb4c9a",
    "cron": "0 0 * * 4,5",
    "description": "Quintas e Sextas",
    "enabled": true
  }
]
```

#### `POST /api/accounts/<id>/schedules`
Add a new schedule.

**Body:**
```json
{
  "cron": "0 0 * * 1,2,3",
  "description": "Mon-Wed",
  "enabled": true
}
```

#### `PUT /api/accounts/<id>/schedules/<sched_id>`
Update a schedule.

#### `DELETE /api/accounts/<id>/schedules/<sched_id>`
Remove a schedule.

**Response:** `{ "status": "deleted" }`

---

### Execution Control

#### `POST /api/accounts/<id>/run`
Trigger an immediate booking run for an account.

**Response:**
```json
{ "status": "started", "account_id": "1a662a44" }
```

#### `GET /api/status`
Get active runs and scheduled jobs.

**Response:**
```json
{
  "active_runs": {
    "1a662a44": { "status": "running", "account_id": "1a662a44" }
  },
  "scheduled_jobs": [
    {
      "id": "1a662a44_e4cb4c9a",
      "name": "Cassio - Quintas e Sextas",
      "next_run": "2026-04-24T00:00:00"
    }
  ]
}
```

#### `GET /api/executions`
List all execution history (newest first).

**Response:** Array of execution summary objects (see [Data Models](#data-models)).

#### `GET /api/executions/<timestamp>`
Get full details of a single execution (includes log content).

#### `DELETE /api/executions/<timestamp>`
Delete an execution log folder.

**Response:** `{ "message": "Execution deleted" }`

#### `GET /api/executions/<timestamp>/screenshots/<filename>`
Retrieve a screenshot from an execution. Returns binary PNG.

---

### Health Check

#### `GET /api/health`
No authentication required.

**Response:**
```json
{ "status": "ok", "logs_dir": "/srv/auto-skedway/logs", "logs_dir_exists": true }
```

---

### Static Files

| Path | Serves |
|------|--------|
| `/` | `frontend/index.html` |
| `/app.js` | `frontend/app.js` |
| `/styles.css` | `frontend/styles.css` |

---

## Frontend

### Layout

The single-page app has three areas:

1. **Sidebar (300 px, fixed)**
   - Brand header + refresh button
   - Account status cards
   - Scheduled jobs list

2. **Main content (fluid)**
   - Top bar: title, account filter, sort order
   - Execution history feed (newest first)

3. **Detail panel (520 px, slide-in)**
   - Execution summary grid
   - Screenshots gallery
   - Execution log (collapsible)
   - Raw JSON (collapsible)

### Account Status Cards

Each card shows:
- Avatar with initials
- Account name and email
- Edit / delete buttons
- Next scheduled run time
- "Run Now" button (disabled when account is running or disabled)

### Execution History Items

Each item shows:
- Status badge: `running`, `success`, `failed`, `already_booked`, etc.
- Target booking date
- Desks attempted
- Duration

Click any item to open the detail panel.

### Modals

- **Account form:** label, email, password, desk list, booking times, enabled toggle
- **Schedule form:** account selector, cron expression, description, enabled toggle

### State Management (`app.js`)

```javascript
const state = {
  executions:      [],
  accounts:        [],
  sortOrder:       'newest',
  accountFilter:   '',
  selectedExecution: null,
  activeRuns:      {},
};
```

**Key Functions:**

| Function | Description |
|----------|-------------|
| `loadAll()` | Fetch executions + accounts, render all views |
| `renderExecutions(list)` | Render history feed |
| `renderAccountStatusCards(accounts)` | Render sidebar account cards |
| `renderSchedulesList(accounts)` | Render scheduled jobs in sidebar |
| `pollStatus()` | Poll `/api/status` every 2 s while runs are active |
| `triggerRun(id)` | POST to `/api/accounts/<id>/run` |

---

## CLI & Commands

### Start the Server

```bash
python main.py
# or with options:
python main.py --port 8080 --debug
```

### Single Account Run

```bash
python main.py --run-once 1a662a44
python main.py --run-once 1a662a44 --dry-run   # navigate, skip submit
python main.py --run-once 1a662a44 --debug      # visible browser
```

### Background Execution (Shell Scripts)

```bash
./start.sh    # Start server in background (nohup)
./stop.sh     # Stop background server process
./deploy.sh   # git pull + pip install + restart
```

### Run Tests

```bash
python -m pytest tests/ -v
python -m pytest tests/test_url_builder.py -v
```

---

## Data Models

### Account Object

```python
{
  "id": str,           # 8-char hex UUID
  "label": str,        # Display name
  "enabled": bool,
  "credentials": {
    "user":   str,     # Email address
    "passwd": str      # Password (from .env)
  },
  "preferences": {
    "desks":      list[str],   # Desk IDs in priority order
    "days_ahead": int,         # How many days ahead to book (default 7)
    "start_time": str,         # "HH:MM"
    "end_time":   str,         # "HH:MM"
    "site_params": {
      "base_type":       str,
      "timezone":        str,
      "from":            str,
      "action":          str,
      "company_site_id": str,
      "building_id":     str,
      "floor_id":        str,
      "space_type":      str,
      "order":           str,
      "page":            str
    }
  },
  "schedules": list[Schedule]
}
```

### Schedule Object

```python
{
  "id":          str,   # 8-char hex UUID
  "cron":        str,   # Standard 5-field cron expression
  "description": str,   # Human-readable label (optional)
  "enabled":     bool
}
```

### Execution Result Object

```python
{
  "result": str,              # success | failure | already_booked | login_failed
                               # | timeout | error | no_desks_configured | missing_credentials
  "booked_desk":     str | None,
  "target_date":     str,     # YYYY-MM-DD
  "desks_attempted": list[str],
  "attempts":        int,
  "account_id":      str,
  "log_dir":         str      # Absolute path to logs/{timestamp}_{account_id}/
}
```

### Execution Summary (`summary.json`)

```json
{
  "execution_time":    "2026-04-14T00:00:00",
  "account_id":        "1a662a44",
  "status":            "completed",
  "target_date":       "2026-04-21",
  "desks_attempted":   ["81502", "81500"],
  "result":            "success",
  "booked_desk":       "81502",
  "duration_seconds":  42.5,
  "screenshots":       9,
  "screenshot_files":  ["01_login_page.png", "02_email_filled.png", "..."],
  "timestamp":         "2026-04-14_000000_1a662a44",
  "parsed_time":       "2026-04-14T00:00:00"
}
```

---

## Deployment

### Environment Setup

```bash
cd /srv/auto-skedway
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps msedge
```

Create `.env` with credentials:
```
ACCOUNT_1a662a44_USER=email@company.com
ACCOUNT_1a662a44_PASSWD=password
```

Edit `accounts.json` to define accounts and schedules, then start:
```bash
python main.py
```

### Nginx Reverse Proxy

The app supports running under a subpath (e.g., `/skedway/`).

**`nginx-config.conf`:**
```nginx
location /skedway/ {
    rewrite ^/skedway/(.*)$ /$1 break;
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host  $server_name;
    proxy_set_header X-Script-Name     /skedway;
    proxy_http_version 1.1;
    proxy_set_header Connection        "";
}
```

- Flask uses `ProxyFix` to trust `X-Forwarded-*` headers
- Frontend auto-detects the `X-Script-Name` header and sets the API prefix accordingly

---

## Testing

### Test Files

| File | What it tests |
|------|---------------|
| `tests/test_config.py` | Configuration constants and validation |
| `tests/test_url_builder.py` | URL construction with various parameters |
| `tests/test_date_utils.py` | Date calculations and formatting |

### Run Tests

```bash
python -m pytest tests/ -v
```

---

## Booking Result Messages

The booking flow detects results by matching Portuguese text from the Skedway response page:

| Detected text | Meaning | Action |
|---------------|---------|--------|
| `já possui um agendamento coincidente` | User already has a booking for this period | Stop — return `already_booked` |
| `Colisão de agenda` | Schedule collision — desk taken | Skip — try next desk |
| `não está disponível no período` | Desk unavailable during requested time | Skip — try next desk |
| `sucesso` / `confirmado` / success URL redirect | Booking confirmed | Stop — return `success` |
| *(anything else)* | Unrecognized failure | Retry same desk up to `RETRY_PER_DESK` times, then move on |

---

*Documentation generated from source code at `/srv/auto-skedway/` — April 2026.*
