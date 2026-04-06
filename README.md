# Auto Skedway

Automated desk booking on [Skedway](https://console.skedway.com/) with multi-account support, built-in scheduler, and web dashboard.

Uses **Playwright + Chromium** with stealth anti-detection to simulate human-like browser interactions.

## Features

- **Multi-account management** — manage multiple Skedway accounts via web UI
- **Built-in scheduler** — cron-based automatic booking (no external cron needed)
- **Web dashboard** — manage accounts, schedules, trigger runs, view execution history
- **Anti-detection** — stealth mode, human-like typing, random mouse movements
- **Priority-based desk selection** — tries desks in order with retry logic
- **Full logging** — text logs, screenshots at every step, JSON summaries

## Prerequisites

- Python 3.10+
- Chromium (installed via Playwright)

### Ubuntu 24 LTS

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv
```

## Setup

```bash
cd auto-skedway
pip install -r requirements.txt
playwright install --with-deps chromium
```

## Configuration

### Accounts

Accounts are managed via the web UI or directly in `accounts.json`:

```json
{
  "accounts": [
    {
      "id": "abc12345",
      "label": "João - Sede",
      "enabled": true,
      "preferences": {
        "desks": ["1234", "5678"],
        "days_ahead": 7,
        "start_time": "08:30",
        "end_time": "17:00"
      },
      "schedules": [
        {
          "id": "sch001",
          "cron": "0 7 * * 1-5",
          "description": "Weekdays 7am",
          "enabled": true
        }
      ]
    }
  ]
}
```

### Credentials

Credentials are stored in `.env` (never in `accounts.json`):

```env
ACCOUNT_abc12345_USER=email@company.com
ACCOUNT_abc12345_PASSWD=your_password
```

Credentials can also be set via the web UI when creating/editing accounts.

## Running Locally

```bash
python main.py
```

Open http://localhost:5000 in your browser.

Options:
- `--port 8080` — custom port
- `--host 127.0.0.1` — bind to localhost only
- `--debug` — enable debug mode
- `--run-once <account_id>` — run a single account and exit (no server)
- `--dry-run` — navigate but don't click submit

## Frontend Usage

The web dashboard has 3 tabs:

1. **Dashboard** — execution statistics, account status cards with "Run Now" buttons, execution history with account filter
2. **Accounts** — create, edit, and delete accounts with preferences and credentials
3. **Schedules** — create and manage cron schedules per account, enable/disable toggle

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Chromium not found | Run `playwright install --with-deps chromium` |
| Login fails | Check credentials in `.env` or via account settings |
| Bot detected | Increase delays in `config.py` (SLOW_MO) |
| Button not found | Check screenshots in logs — DOM may have changed |
| Timeout | Increase timeout in account preferences |
