# Auto Skedway

Automated desk booking on [Skedway](https://console.skedway.com/) with multi-account support, built-in scheduler, and web dashboard.

Uses **Playwright + Microsoft Edge** with stealth anti-detection to simulate human-like browser interactions.

## Features

- **Multi-account management** — manage multiple Skedway accounts via web UI
- **Built-in scheduler** — cron-based automatic booking (no external cron needed)
- **Web dashboard** — manage accounts, schedules, trigger runs, view execution history
- **Anti-detection** — stealth mode, human-like typing, random mouse movements
- **Priority-based desk selection** — tries desks in order with retry logic
- **Smart booking results** — detects duplicate bookings and unavailable desks automatically
- **Headless by default** — runs headless unless `--debug` is passed
- **Full logging** — text logs, screenshots at every step, JSON summaries

## Prerequisites

- Python 3.10+
- Microsoft Edge (installed via Playwright)

## Setup

```bash
cd auto-skedway
pip install -r requirements.txt
playwright install --with-deps msedge
```

> **Corporate proxy?** If `playwright install` fails with `SELF_SIGNED_CERT_IN_CHAIN`, run:
> ```bash
> # PowerShell
> $env:NODE_TLS_REJECT_UNAUTHORIZED = "0"
> playwright install --with-deps msedge
> ```

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
- `--debug` — enable debug mode (browser visible, non-headless)
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

## Booking Result Handling

The system detects specific Skedway responses after each booking attempt:

| Response | Action |
|----------|--------|
| **"já possui um agendamento coincidente"** | Stops immediately — user already has a booking for that period |
| **"Colisão de agenda" / "não está disponível"** | Skips to next desk — current desk is taken |
| Success confirmation | Returns success |
| Any other failure | Retries the same desk (up to `RETRY_PER_DESK` times) |

## Deployment (nginx subpath)

To serve the app at a subpath like `example.com/skedway/`, use the provided `nginx-config.conf`:

1. Copy the `location /skedway/ { ... }` block from `nginx-config.conf` into your nginx server block.
2. Test and reload nginx:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

ProxyFix is already configured in `frontend/api.py` to handle forwarded headers correctly.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Edge not found | Run `playwright install --with-deps msedge` |
| SSL cert error on install | Set `NODE_TLS_REJECT_UNAUTHORIZED=0` before `playwright install` |
| Login fails | Check credentials in `.env` or via account settings |
| Bot detected | Increase delays in `config.py` (SLOW_MO) |
| Button not found | Check screenshots in logs — DOM may have changed |
| Timeout | Increase `PAGE_LOAD_TIMEOUT` / `CLICK_TIMEOUT` in `config.py` |
