"""Auto Skedway — Unified entrypoint.

Starts the Flask API server + APScheduler for automated booking execution.

Usage:
    python main.py                          # Start server (default port 5000)
    python main.py --port 8080              # Custom port
    python main.py --run-once <account_id>  # Run single account and exit
"""

import argparse
import logging
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger("auto-skedway.main")


def parse_args():
    parser = argparse.ArgumentParser(description="Auto Skedway — Automated desk booking")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", default=False, help="Enable debug mode")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Navigate but don't click submit")
    parser.add_argument(
        "--run-once",
        type=str,
        metavar="ACCOUNT_ID",
        default=None,
        help="Run booking for a single account and exit (no server)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Configure logging early
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)-8s] [%(name)-12s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Single-run mode: execute one account and exit
    if args.run_once:
        from core.account_manager import get_account
        from core.runner import run_booking

        account = get_account(args.run_once)
        if not account:
            print(f"ERROR: Account '{args.run_once}' not found in accounts.json")
            return 1

        result = run_booking(account, debug=args.debug, dry_run=args.dry_run)
        print(f"Result: {result.get('result', 'unknown')}")
        return 0 if result.get("result") in ("success", "dry_run_success") else 1

    # Server mode: start Flask + Scheduler
    from frontend.api import create_app
    from core.scheduler import init_scheduler, shutdown_scheduler

    app = create_app()

    # Ensure logs directory exists
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Start scheduler
    logger.info("Initializing scheduler...")
    init_scheduler()
    logger.info("Scheduler initialized")

    try:
        logger.info(f"Starting Auto Skedway on http://{args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)
    finally:
        shutdown_scheduler()


if __name__ == "__main__":
    sys.exit(main() or 0)
