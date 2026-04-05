# Auto Skedway

Automated desk booking on [Skedway](https://console.skedway.com/) for Volvo.

Uses **Playwright + Microsoft Edge** (non-headless) with anti-detection stealth to simulate human-like browser interactions.

## Features

- **Edge-only automation** — bypasses anti-bot detection that blocks Chrome/headless
- **Human-like behavior** — random typing delays, mouse movements, realistic patterns
- **Priority-based desk selection** — tries desks in order, falls back automatically
- **Retry logic** — retries per desk with configurable delays
- **Full logging** — text logs + screenshots at every step + JSON summary
- **Dry-run mode** — test the flow without actually booking
- **Debug mode** — slow, verbose, keeps browser open for inspection

## Requirements

- Python 3.10+
- Microsoft Edge (installed on system)
- Playwright (Python)

## Setup

1. **Install dependencies:**

```bash
cd auto-skedway
pip install -r requirements.txt
```

2. **Set environment variables:**

```bash
# Windows PowerShell
$env:SKEDWAY_USER = "your_email@volvo.com"
$env:SKEDWAY_PASSWD = "your_password"
```

Or create a `.env` file (see `.env.example`).

3. **Install Playwright browsers** (if not already done):

```bash
python -m playwright install
```

## Usage

### Basic

```bash
python main.py --desks 1234 5678 9012
```

### With options

```bash
# Debug mode (slower, verbose, browser stays open)
python main.py --desks 1234 5678 --debug

# Dry run (navigates but doesn't click submit)
python main.py --desks 1234 --dry-run

# Custom date offset and times
python main.py --desks 1234 --days-ahead 7 --start-time 08:30 --end-time 17:00

# Custom timeout
python main.py --desks 1234 5678 --timeout 600
```

### CLI Arguments

| Argument       | Required | Default | Description                      |
|----------------|----------|---------|----------------------------------|
| `--desks`      | Yes      | —       | Desk IDs in priority order       |
| `--debug`      | No       | False   | Verbose mode, slow browser       |
| `--days-ahead` | No       | 7       | Days ahead for booking date      |
| `--dry-run`    | No       | False   | Navigate but don't submit        |
| `--start-time` | No       | 08:30   | Booking start time               |
| `--end-time`   | No       | 17:00   | Booking end time                 |
| `--timeout`    | No       | 300     | Max execution time (seconds)     |

## Logs

Each execution creates a timestamped folder under `logs/`:

```
logs/
└── 2026-04-12_083000/
    ├── execution.log           # Full text log
    ├── 01_login_page.png       # Screenshot: login page
    ├── 02_continue_warning.png # Screenshot: mobile warning
    ├── 03_login_form_filled.png
    ├── 04_after_login.png
    ├── 05_booking_page_1234.png
    ├── 06_before_submit_1234.png
    ├── 07_result_1234.png
    └── summary.json            # Machine-readable result
```

## Scheduled Execution (Windows Task Scheduler)

```powershell
$action = New-ScheduledTaskAction -Execute "python" `
    -Argument "C:\Users\a374163\auto-skedway\main.py --desks 1234 5678" `
    -WorkingDirectory "C:\Users\a374163\auto-skedway"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
Register-ScheduledTask -TaskName "AutoSkedway" -Action $action -Trigger $trigger
```

## Running Tests

```bash
pip install pytest
cd auto-skedway
python -m pytest tests/ -v
```

## Project Structure

```
auto-skedway/
├── main.py              # CLI entry point
├── config.py            # Configuration and constants
├── core/
│   ├── browser.py       # Edge + stealth browser setup
│   ├── auth.py          # Login flow
│   ├── booking.py       # Booking logic with fallback
│   └── url_builder.py   # Dynamic URL construction
├── utils/
│   ├── logger.py        # Logging + screenshots
│   ├── humanize.py      # Human-like delays and movements
│   └── date_utils.py    # Date calculations
├── tests/               # Unit tests
└── logs/                # Execution logs (auto-created)
```

## Troubleshooting

| Issue                    | Solution                                              |
|--------------------------|-------------------------------------------------------|
| Edge not found           | Ensure Edge is installed and in PATH                  |
| Login fails              | Check SKEDWAY_USER/SKEDWAY_PASSWD env vars            |
| Bot detected             | Try increasing delays in `config.py` (SLOW_MO)        |
| Button not found         | Check screenshots — DOM may have changed              |
| Timeout                  | Increase `--timeout` or check network                 |

## Security

- Credentials are loaded from **environment variables only**
- No secrets are stored in code or logs
- Passwords are never printed in log output
- `.env` file is excluded via `.gitignore`
