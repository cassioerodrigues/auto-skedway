"""Job scheduler using APScheduler for automated booking execution."""

import logging
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

from core.account_manager import load_accounts, get_account
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
    """Parse a 5-field cron expression into APScheduler kwargs."""
    parts = cron_str.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (need 5 fields): {cron_str}")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def init_scheduler() -> BackgroundScheduler:
    """Initialize and start the scheduler with jobs from accounts.json."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(
        job_defaults={"coalesce": True, "max_instances": 1}
    )
    _scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)

    _load_all_jobs()
    _scheduler.start()

    # Log next run times for debugging
    for job in _scheduler.get_jobs():
        logger.info(f"  → {job.name} | next run: {job.next_run_time}")

    logger.info("Scheduler started")
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
                logger.info(f"Scheduled job {job_id}: {schedule['cron']}")
            except Exception as e:
                logger.error(f"Failed to schedule job for {account['id']}/{schedule['id']}: {e}")

    logger.info(f"Loaded {job_count} scheduled jobs")


def reload_jobs():
    """Reload all jobs from accounts.json (call after schedule changes)."""
    if not _scheduler:
        return
    _scheduler.remove_all_jobs()
    _load_all_jobs()
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


def shutdown_scheduler():
    """Shut down the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
    _scheduler = None
