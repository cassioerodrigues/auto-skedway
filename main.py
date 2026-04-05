"""Auto Skedway — Automated desk booking on Skedway.

Usage:
    python main.py --desks 1234 5678 9012
    python main.py --desks 1234 --debug --dry-run
    python main.py --desks 1234 5678 --days-ahead 7 --start-time 08:30 --end-time 17:00
"""

import argparse
import os
import sys
import signal
import time

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from core.browser import setup_browser, teardown_browser
from core.auth import login
from core.booking import book_desk
from utils.logger import ExecutionLogger


def parse_args():
    parser = argparse.ArgumentParser(
        description="Auto Skedway — Automated desk booking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --desks 1234 5678 9012
  python main.py --desks 1234 --debug
  python main.py --desks 1234 --dry-run
  python main.py --desks 1234 5678 --days-ahead 7
        """,
    )
    parser.add_argument(
        "--desks",
        nargs="+",
        required=True,
        help="Space-separated list of desk IDs in priority order",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Debug mode: slower, more verbose, keeps browser open on failure",
    )
    parser.add_argument(
        "--days-ahead",
        type=int,
        default=config.DEFAULT_DAYS_AHEAD,
        help=f"Days ahead for booking date (default: {config.DEFAULT_DAYS_AHEAD})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Navigate to booking page but don't click submit",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        default=config.DEFAULT_START_TIME,
        help=f"Booking start time (default: {config.DEFAULT_START_TIME})",
    )
    parser.add_argument(
        "--end-time",
        type=str,
        default=config.DEFAULT_END_TIME,
        help=f"Booking end time (default: {config.DEFAULT_END_TIME})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=config.TOTAL_TIMEOUT,
        help=f"Max execution time in seconds (default: {config.TOTAL_TIMEOUT})",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Initialize logger
    log_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    logger = ExecutionLogger(base_dir=log_base, debug=args.debug)

    # Validate credentials
    logger.info("Validating credentials...")
    config.validate_credentials()

    logger.info(f"Desks (priority order): {args.desks}")
    logger.info(f"Days ahead: {args.days_ahead}")
    logger.info(f"Time: {args.start_time} - {args.end_time}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Debug: {args.debug}")

    pw = None
    browser = None
    context = None

    # Timeout handler
    start_time = time.time()

    def check_timeout():
        elapsed = time.time() - start_time
        if elapsed > args.timeout:
            raise TimeoutError(f"Execution exceeded {args.timeout}s timeout ({elapsed:.0f}s elapsed)")

    try:
        # Setup browser
        logger.info("Launching Edge browser with stealth mode...")
        pw, browser, context, page = setup_browser(debug=args.debug)
        logger.info("Browser launched successfully")

        check_timeout()

        # Login
        logger.info("Starting login flow...")
        login_success = login(page, logger)
        if not login_success:
            # Retry login once
            logger.warning("Login failed — retrying...")
            page.goto("about:blank")
            time.sleep(2)
            login_success = login(page, logger)

        if not login_success:
            logger.error("Login failed after retry — aborting")
            logger.save_summary(
                target_date="N/A",
                desks_attempted=[],
                result="login_failed",
            )
            logger.finalize("failed")
            return 1

        check_timeout()

        # Attempt booking
        result = book_desk(
            page=page,
            desk_ids=args.desks,
            days_ahead=args.days_ahead,
            start_time=args.start_time,
            end_time=args.end_time,
            logger=logger,
            dry_run=args.dry_run,
        )

        # Save summary
        logger.save_summary(
            target_date=result["target_date"],
            desks_attempted=result["desks_attempted"],
            result=result["result"],
            booked_desk=result["booked_desk"],
        )

        if result["result"] in ("success", "dry_run_success"):
            logger.finalize("success")
            return 0
        else:
            logger.finalize("failed")
            return 1

    except TimeoutError as e:
        logger.error(str(e))
        logger.screenshot(page, "timeout") if "page" in dir() else None
        logger.save_summary(
            target_date="N/A",
            desks_attempted=args.desks,
            result="timeout",
        )
        logger.finalize("timeout")
        return 2

    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user")
        logger.finalize("interrupted")
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        try:
            logger.screenshot(page, "unexpected_error")
        except Exception:
            pass
        logger.save_summary(
            target_date="N/A",
            desks_attempted=args.desks,
            result=f"error: {str(e)[:100]}",
        )
        logger.finalize("error")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

    finally:
        if not args.debug:
            if pw and browser and context:
                logger.info("Closing browser...")
                teardown_browser(pw, browser, context)
        else:
            logger.info("Debug mode — browser remains open. Close it manually.")


if __name__ == "__main__":
    sys.exit(main())
