"""Job scheduler using APScheduler for automated booking execution."""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

from core.account_manager import load_accounts, get_account
from core.holiday_manager import is_holiday
from core.runner import run_booking

logger = logging.getLogger("auto-skedway.scheduler")

# Track active executions
_active_runs: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=2)
_scheduler: BackgroundScheduler | None = None


def _job_listener(event):
    """Log scheduler events for debugging."""
    if event.exception:
        logger.error(f"Scheduled job {event.job_id} FAILED with exception: {event.exception}")
        logger.error(f"Traceback: {event.traceback}")
    elif hasattr(event, 'job_id'):
        if event.code == EVENT_JOB_MISSED:
            logger.warning(f"Scheduled job {event.job_id} MISSED (scheduler was down?)")
        else:
            logger.info(f"Scheduled job {event.job_id} executed successfully")


def _execute_job(account_id: str):
    """Run a booking job for an account (called by scheduler or manually)."""
    logger.info(f"Job triggered for account: {account_id}")
    if account_id in _active_runs:
        logger.warning(f"Account {account_id} is already running — skipping")
        return

    account = get_account(account_id)
    if not account:
        logger.error(f"Account {account_id} not found")
        return

    if not account.get("enabled", True):
        logger.info(f"Account {account_id} is disabled — skipping")
        return

    days_ahead = account.get("preferences", {}).get("days_ahead", 7)
    target_date = date.today() + timedelta(days=days_ahead)
    if is_holiday(target_date):
        logger.info(f"Skipping run for {account_id}: target date {target_date} is a holiday")
        return

    _active_runs[account_id] = {"status": "running", "account_id": account_id}
    logger.info(f"Starting execution for account: {account.get('label', account_id)}")

    try:
        result = run_booking(account)
        _active_runs[account_id] = {
            "status": "completed",
            "result": result.get("result"),
            "account_id": account_id,
        }
        logger.info(f"Execution completed for {account_id}: {result.get('result')}")
    except Exception as e:
        _active_runs[account_id] = {
            "status": "error",
            "error": str(e),
            "account_id": account_id,
        }
        logger.error(f"Execution failed for {account_id}: {e}")
    finally:
        # Clean up after a delay (keep status visible briefly)
        import threading
        def cleanup():
            _active_runs.pop(account_id, None)
        threading.Timer(60, cleanup).start()


def trigger_run(account_id: str) -> dict:
    """Manually trigger an immediate booking run for an account."""
    if account_id in _active_runs and _active_runs[account_id]["status"] == "running":
        return {"error": "Account is already running", "account_id": account_id}

    account = get_account(account_id)
    if not account:
        return {"error": "Account not found", "account_id": account_id}

    _executor.submit(_execute_job, account_id)
    return {"status": "started", "account_id": account_id}


def get_active_runs() -> dict:
    """Get status of all active/recent runs."""
    return dict(_active_runs)


def _parse_cron(cron_str: str) -> dict:
    """Parse a 5-field cron expression into APScheduler kwargs.

    Converts day_of_week from standard cron convention (0=Sunday)
    to APScheduler convention (0=Monday).
    """
    parts = cron_str.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (need 5 fields): {cron_str}")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": _convert_dow(parts[4]),
    }


def _convert_dow(field: str) -> str:
    """Convert day_of_week from cron (0=Sun) to APScheduler (0=Mon).

    Handles: single values (1), ranges (1-5), lists (1,3,5), mixed (1-3,5),
    wildcards (*), and 7 as Sunday alias.
    """
    # Map: cron_value -> apscheduler_value
    # cron: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun
    # aps:  0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    if field == "*":
        return "*"

    def convert_single(v: str) -> str:
        n = int(v)
        return str((n - 1) % 7)

    result_parts = []
    for segment in field.split(","):
        if "-" in segment:
            start, end = segment.split("-", 1)
            result_parts.append(f"{convert_single(start)}-{convert_single(end)}")
        else:
            result_parts.append(convert_single(segment))
    return ",".join(result_parts)


def init_scheduler() -> BackgroundScheduler:
    """Initialize and start the scheduler with jobs from accounts.json."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(
        timezone="America/Sao_Paulo",
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60}
    )
    _scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)

    _load_all_jobs()
    _scheduler.start()

    # Log next run times for debugging
    jobs = _scheduler.get_jobs()
    logger.info(f"Scheduler started with {len(jobs)} jobs:")
    for job in jobs:
        logger.info(f"  \u2192 {job.name} | next run: {job.next_run_time}")

    return _scheduler


def _load_all_jobs():
    """Load all enabled schedules from accounts.json into the scheduler."""
    accounts = load_accounts()
    job_count = 0

    for account in accounts:
        if not account.get("enabled", True):
            continue
        for schedule in account.get("schedules", []):
            if not schedule.get("enabled", True):
                continue
            try:
                cron_kwargs = _parse_cron(schedule["cron"])
                job_id = f"{account['id']}_{schedule['id']}"
                # Use account timezone if available, fallback to America/Sao_Paulo
                tz = account.get("preferences", {}).get("site_params", {}).get(
                    "timezone", "America/Sao_Paulo"
                )
                _scheduler.add_job(
                    _execute_job,
                    trigger=CronTrigger(timezone=tz, **cron_kwargs),
                    args=[account["id"]],
                    id=job_id,
                    replace_existing=True,
                    name=f"{account.get('label', account['id'])} - {schedule.get('description', schedule['cron'])}",
                )
                job_count += 1
                logger.info(f"Loaded job {job_id}: {schedule['cron']} (tz={tz})")
            except Exception as e:
                logger.error(f"Failed to schedule job for {account['id']}/{schedule['id']}: {e}")

    logger.info(f"Loaded {job_count} scheduled jobs")


def reload_jobs():
    """Reload all jobs from accounts.json (call after schedule changes)."""
    if not _scheduler:
        return
    _scheduler.remove_all_jobs()
    _load_all_jobs()
    for job in _scheduler.get_jobs():
        logger.info(f"  \u2192 {job.name} | next run: {job.next_run_time}")
    logger.info("Scheduler jobs reloaded")


def get_scheduled_jobs() -> list[dict]:
    """Get info about all scheduled jobs."""
    if not _scheduler:
        return []
    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run,
        })
    return jobs


def get_next_run_by_account(account_id: str) -> str | None:
    """Get the earliest next_run time for all jobs of an account.
    
    Returns ISO format datetime string or None if no jobs scheduled.
    """
    if not _scheduler:
        return None
    
    earliest = None
    for job in _scheduler.get_jobs():
        # Job ID format: "{account_id}_{schedule_id}"
        if job.id.startswith(f"{account_id}_"):
            if job.next_run_time:
                if earliest is None or job.next_run_time < earliest:
                    earliest = job.next_run_time
    
    return earliest.isoformat() if earliest else None


def shutdown_scheduler():
    """Shut down the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
    _scheduler = None
