# Auto Skedway

Automated desk booking on [Skedway](https://console.skedway.com/) (Volvo instance) with multi-account support, cron-based scheduling, holiday calendar, and a web dashboard. Uses **Playwright + Microsoft Edge** with stealth anti-detection.

A separate nightly job at 02:00 BRT auto-resolves the oldest open GitHub issues using Claude — see [`scripts/README.md`](scripts/README.md).

---

## Table of contents

1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [Directory layout](#directory-layout)
4. [Setup](#setup)
5. [Configuration](#configuration)
6. [Running](#running)
7. [Web dashboard](#web-dashboard)
8. [Architecture](#architecture)
9. [API reference](#api-reference)
10. [Data models](#data-models)
11. [Booking result messages](#booking-result-messages)
12. [Deployment](#deployment)
13. [Testing](#testing)
14. [Troubleshooting](#troubleshooting)

---

## Features

- **Multi-account management** — all accounts and per-account schedules managed via web UI (admin sees all; non-admin users see only their own)
- **Built-in scheduler** — APScheduler with cron triggers, no external cron needed for booking
- **Holiday calendar** — global list of dates that suppress all scheduled runs (admin-only writes; visible to all users)
- **Anti-detection** — stealth mode, human-like typing, random mouse movements
- **Priority-based desk selection** — tries desks in order with retry on generic failure
- **Smart booking outcomes** — detects already-booked / desk-unavailable from Skedway responses
- **Headless by default** — visible browser only with `--debug`
- **Full logging** — text logs, screenshots at every step, JSON summaries
- **Web dashboard** — execution history, manual trigger, account/schedule/holiday management

## Tech stack

| Component | Technology |
|---|---|
| Backend | Python 3.10+, Flask 2.3+ |
| Automation | Playwright 1.58+, playwright-stealth 2.0+ |
| Scheduling | APScheduler 3.10 |
| Frontend | HTML5, vanilla JavaScript, CSS3 |
| Server | Flask + CORS + ProxyFix (for nginx subpath) |
| Browser | Microsoft Edge via Playwright |
| Persistence | `accounts.json`, `holidays.json`, `.env` (filelock-protected) |

### Python dependencies (`requirements.txt`)

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

## Directory layout

```
/srv/auto-skedway/
├── main.py                    # Entry point (CLI + server)
├── config.py                  # Configuration constants
├── accounts.json              # Account definitions (non-sensitive)
├── holidays.json              # Global holiday calendar
├── .env                       # Credentials (ACCOUNT_*_USER/PASSWD)
├── requirements.txt
├── README.md                  # This file
├── nginx-config.conf          # Nginx reverse proxy config
│
├── core/
│   ├── auth.py                # Login flow (Skedway authentication)
│   ├── booking.py             # Desk booking with retry/fallback
│   ├── browser.py             # Browser setup with stealth
│   ├── runner.py              # Orchestrator (login → booking)
│   ├── url_builder.py         # Booking URL construction
│   ├── account_manager.py     # Account/credential/schedule persistence
│   ├── holiday_manager.py     # Holiday calendar CRUD
│   └── scheduler.py           # APScheduler wrapper, cron job management
│
├── frontend/
│   ├── api.py                 # Flask API + static file serving
│   ├── index.html             # Single-page app shell
│   ├── app.js                 # Frontend state + UI rendering
│   └── styles.css             # Theme
│
├── utils/
│   ├── humanize.py            # Human-like typing/clicks/delays
│   ├── logger.py              # ExecutionLogger (screenshots + logs)
│   └── date_utils.py          # Date helpers
│
├── tests/                     # Pytest suites
│   ├── test_url_builder.py
│   └── test_date_utils.py
│
├── scripts/                   # Auto issue resolver (see scripts/README.md)
│   ├── auto-resolve-issues.sh
│   └── issue-resolver-prompt.md
│
└── logs/                      # Created at runtime
    ├── 2026-04-06_160104_1a662a44/
    │   ├── execution.log
    │   ├── summary.json
    │   └── 01_login_page.png … 09_done.png
    └── cron-issues-YYYY-MM-DD.log    # auto-resolver per-day log
```

---

## Setup

```bash
cd /srv/auto-skedway
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps msedge
```

> **Corporate proxy?** If `playwright install` fails with `SELF_SIGNED_CERT_IN_CHAIN`:
> ```bash
> NODE_TLS_REJECT_UNAUTHORIZED=0 playwright install --with-deps msedge
> ```

---

## Configuration

### `config.py` — application constants

| Constant | Default | Description |
|---|---|---|
| `LOGIN_URL` | `https://console.skedway.com/` | Skedway login page |
| `BOOKING_BASE_URL` | `https://volvo.skedway.com/booking-form.php` | Booking endpoint |
| `DEFAULT_DAYS_AHEAD` | `7` | How many days ahead to book by default |
| `DEFAULT_START_TIME` / `DEFAULT_END_TIME` | `08:30` / `17:00` | Default reservation window |
| `PAGE_LOAD_TIMEOUT` | `30000 ms` | Playwright navigation timeout |
| `CLICK_TIMEOUT` | `10000 ms` | Element click timeout |
| `LOGIN_TIMEOUT` | `15000 ms` | Max time for login flow |
| `TOTAL_TIMEOUT` | `300 s` | Max total time per account |
| `RETRY_PER_DESK` | `2` | Retries per desk on generic failure |
| `RETRY_DELAY_MIN` / `RETRY_DELAY_MAX` | `1.5 / 2.5 s` | Delay between retries |
| `BROWSER_CHANNEL` | `msedge` | Edge channel via Playwright |
| `SLOW_MO_DEFAULT` / `SLOW_MO_DEBUG` | `50 / 200 ms` | Per-action delay (normal/debug) |
| `ADMIN_EMAIL` | `cassio.rodrigues@volvo.com` | Admin user identifier |

### `.env` — credentials

Per-account, indexed by account ID:

```
ACCOUNT_1a662a44_USER=email@company.com
ACCOUNT_1a662a44_PASSWD=password
```

Loaded at runtime by `account_manager.py`. Never written to `accounts.json`.

### `accounts.json` — account definitions

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
        { "id": "e4cb4c9a", "cron": "0 0 * * 4,5", "description": "Quintas e Sextas", "enabled": true }
      ]
    }
  ]
}
```

### `holidays.json` — global holiday calendar

Dates listed here suppress **all** scheduled booking runs whose target date (today + `days_ahead`) lands on the holiday. Manual `/api/accounts/<id>/run` calls are not affected.

```json
{
  "holidays": [
    { "id": "63bd4ed5", "date": "2026-06-04", "description": "Corpus Christi" }
  ]
}
```

Admin-only writes via `/api/holidays`. All authenticated users can read.

---

## Running

### Server (default)

```bash
python main.py
```

Open `http://localhost:5000`.

| Flag | Default | Description |
|---|---|---|
| `--port N` | `5000` | HTTP port |
| `--host ADDR` | `0.0.0.0` | Bind address |
| `--debug` | off | Visible browser, verbose, slower interactions |
| `--dry-run` | off | Navigate but skip final submit |
| `--run-once ID` | — | Run a single account and exit (no server) |

### Single-account run (no server)

```bash
python main.py --run-once 1a662a44
python main.py --run-once 1a662a44 --dry-run
python main.py --run-once 1a662a44 --debug
```

---

## Web dashboard

Single-page app served by Flask. Three areas:

1. **Sidebar (left, ~300 px):**
   - Account status cards — avatar, name, edit/delete, next scheduled run, "Run Now"
   - **Feriados** section (admin-only) — date picker (dd/mm/yyyy), description, list with delete

2. **Main content:**
   - Top bar: title, account filter, sort order
   - Execution history feed (newest first)

3. **Detail panel (right, slide-in):**
   - Execution summary, screenshots, log, raw JSON

### Account modal

Holds account fields (label, email, password, desks, times, enabled toggle) **and** the per-account schedules sub-section (cron, description, enabled, edit/delete inline). Schedules are not a separate sidebar tab — they live with the account they belong to.

### Permissions

- **Admin** (`config.ADMIN_EMAIL`): all accounts, all schedules, holidays read/write.
- **Non-admin**: only their own account; holidays read-only.

---

## Architecture

### Entry point — `main.py`

```
python main.py                          # server mode (Flask + APScheduler)
python main.py --run-once <id>          # single-shot, no server
```

### Booking flow (per execution)

```
core/runner.run_booking()
  ├─ core/browser.create_browser()         # stealth setup
  ├─ core/auth.login()                     # email → "Próximo" → password → submit
  └─ core/booking.book_desk()              # iterate desks in priority order
       ├─ url_builder.build_booking_url()  # construct URL with query params
       ├─ navigate + click submit
       └─ parse_response()                 # success | already_booked | desk_unavailable | failure
```

Each step writes a screenshot and log line to `logs/{timestamp}_{account_id}/`.

### Scheduler — `core/scheduler.py`

APScheduler `BackgroundScheduler` with `CronTrigger`. Standard 5-field cron is converted (APScheduler uses `0 = Monday`).

Before invoking `run_booking()`, the scheduler checks `holiday_manager.is_holiday(target_date)` and skips the run if true.

Concurrency: `ThreadPoolExecutor(max_workers=2)`. A per-account lock prevents the same account from running twice in parallel.

### Persistence

- `accounts.json` and `holidays.json` are guarded by `filelock.FileLock` (10 s timeout) on writes.
- `.env` is rewritten in place when credentials change.

### Anti-detection (`core/browser.py`)

- `playwright-stealth` plus custom JS injection that removes `navigator.webdriver` and other automation flags
- Custom User-Agent (Windows 10 + Edge)
- Locale `pt-BR`, timezone `America/Sao_Paulo`, viewport `1920×1080`
- Human-like typing in `auth.py` is preserved (anti-detection critical zone)

---

## API reference

Base URL: `http://localhost:5000` (or `<host>/skedway/` behind nginx).

All endpoints except `/api/health` require **HTTP Basic Auth** (account email + password). Admin sees everything; users see only their own resources.

### Account management

| Method | Path | Description |
|---|---|---|
| GET | `/api/accounts` | List accounts the caller can see |
| GET | `/api/accounts/<id>` | Single account |
| POST | `/api/accounts` | Create account (label, desks, days_ahead, start/end times, user, passwd) |
| PUT | `/api/accounts/<id>` | Partial update |
| DELETE | `/api/accounts/<id>` | Delete account + credentials |

### Schedules (nested under account)

| Method | Path | Description |
|---|---|---|
| GET | `/api/accounts/<id>/schedules` | List schedules |
| POST | `/api/accounts/<id>/schedules` | Add schedule (cron, description, enabled) |
| PUT | `/api/accounts/<id>/schedules/<sched_id>` | Update schedule |
| DELETE | `/api/accounts/<id>/schedules/<sched_id>` | Remove schedule |

### Holidays (global)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/holidays` | any user | List holidays |
| POST | `/api/holidays` | admin only | Add (date, description) — 400 if past, 409 if duplicate |
| PUT | `/api/holidays/<id>` | admin only | Update |
| DELETE | `/api/holidays/<id>` | admin only | Remove |

### Execution control

| Method | Path | Description |
|---|---|---|
| POST | `/api/accounts/<id>/run` | Trigger an immediate booking run |
| GET | `/api/status` | Active runs + scheduled jobs + `is_admin` flag |
| GET | `/api/executions` | Execution history (newest first) |
| GET | `/api/executions/<timestamp>` | Single execution with log content |
| DELETE | `/api/executions/<timestamp>` | Delete an execution log folder |
| GET | `/api/executions/<timestamp>/screenshots/<filename>` | Binary PNG |

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | No auth. `{ "status": "ok", ... }` |

---

## Data models

### Account

```python
{
  "id": str,                  # 8-char hex
  "label": str,
  "enabled": bool,
  "credentials": { "user": str, "passwd": str },   # merged from .env
  "preferences": {
    "desks": list[str],       # priority order
    "days_ahead": int,
    "start_time": str,        # "HH:MM"
    "end_time":   str,
    "site_params": { ... }    # 10 fixed keys, see config.DEFAULT_SITE_PARAMS
  },
  "schedules": list[Schedule]
}
```

### Schedule

```python
{
  "id": str,                  # 8-char hex
  "cron": str,                # standard 5-field cron
  "description": str,
  "enabled": bool
}
```

### Holiday

```python
{
  "id": str,                  # 8-char hex
  "date": str,                # YYYY-MM-DD
  "description": str
}
```

### Execution summary (`logs/{ts}_{account_id}/summary.json`)

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
  "screenshot_files": ["01_login_page.png", "..."],
  "timestamp": "2026-04-14_000000_1a662a44"
}
```

`result` is one of: `success`, `failure`, `already_booked`, `login_failed`, `timeout`, `error`, `no_desks_configured`, `missing_credentials`.

---

## Booking result messages

The booking flow detects results by matching Portuguese text from the Skedway response page:

| Detected text | Meaning | Action |
|---|---|---|
| `já possui um agendamento coincidente` | User already has a booking | Stop — return `already_booked` |
| `Colisão de agenda` / `não está disponível no período` | Desk taken | Skip — try next desk |
| Success URL redirect or success text | Booking confirmed | Stop — return `success` |
| (anything else) | Unknown failure | Retry same desk up to `RETRY_PER_DESK` times |

---

## Deployment

### Initial deploy

```bash
cd /srv/auto-skedway
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps msedge
```

Create `.env` with credentials, edit `accounts.json` to define accounts and schedules, then start with `python main.py` (or use the convenience scripts below).

### Background scripts

`start.sh`, `stop.sh`, and `deploy.sh` are local convenience scripts (kept out of git) for running the server under `nohup` and for `git pull && pip install && restart` workflows. Use them or call `python main.py` directly — they are not load-bearing.

### Nginx subpath (`/skedway/`)

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

Flask uses `ProxyFix` to trust `X-Forwarded-*`; the frontend reads `X-Script-Name` and prefixes API calls accordingly.

---

## Testing

```bash
python -m pytest tests/ -v
```

| File | Coverage |
|---|---|
| `tests/test_url_builder.py` | URL construction with various parameters |
| `tests/test_date_utils.py` | Date calculations and formatting |

---

## Troubleshooting

| Issue | Solution |
|---|---|
| Edge not found | `playwright install --with-deps msedge` |
| SSL cert error on install | `NODE_TLS_REJECT_UNAUTHORIZED=0 playwright install --with-deps msedge` |
| Login fails | Check credentials in `.env` or via account modal |
| Bot detected | Increase `SLOW_MO_DEFAULT` in `config.py`; verify stealth is loading |
| Button not found | Check screenshots in `logs/{ts}_{id}/` — DOM may have changed |
| Timeout | Increase `PAGE_LOAD_TIMEOUT` / `CLICK_TIMEOUT` in `config.py` |
| Holiday not skipping | Check `holidays.json` date matches `target_date` (today + `days_ahead`), not the run date |
| Schedule not firing | Verify cron expression and `enabled: true`; check server log on startup for job registration |
