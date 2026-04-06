"""Logging and screenshot management."""

import logging
import os
import json
import sys
from datetime import datetime

from colorama import init as colorama_init, Fore, Style

colorama_init()


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output."""

    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


class ExecutionLogger:
    """Manages text logging and screenshot capture for a single execution."""

    def __init__(self, base_dir: str = "logs", debug: bool = False, account_id: str | None = None):
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        folder_name = f"{self.timestamp}_{account_id}" if account_id else self.timestamp
        self.log_dir = os.path.join(base_dir, folder_name)
        self.account_id = account_id
        os.makedirs(self.log_dir, exist_ok=True)

        self.screenshot_counter = 0
        self.screenshots = []
        self.start_time = datetime.now()

        # Setup logger
        self.logger = logging.getLogger("auto-skedway")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.logger.handlers.clear()

        # File handler
        log_file = os.path.join(self.log_dir, "execution.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "[%(asctime)s] [%(levelname)-8s] [%(module)-12s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        console_fmt = ColoredFormatter(
            "[%(asctime)s] [%(levelname)-8s] %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(console_fmt)
        self.logger.addHandler(console_handler)

        self.info(f"Execution started — logs at: {self.log_dir}")

        # Create initial summary with in_progress status
        self._create_initial_summary()

    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def screenshot(self, page, label: str) -> str:
        """Capture a screenshot with sequential numbering.

        Args:
            page: Playwright page object.
            label: Descriptive label for the screenshot.

        Returns:
            Path to the saved screenshot.
        """
        self.screenshot_counter += 1
        filename = f"{self.screenshot_counter:02d}_{label}.png"
        filepath = os.path.join(self.log_dir, filename)

        try:
            page.screenshot(path=filepath, full_page=True)
            self.screenshots.append(filename)
            self.debug(f"Screenshot saved: {filename}")
        except Exception as e:
            self.warning(f"Failed to capture screenshot '{label}': {e}")

        return filepath

    def _create_initial_summary(self):
        """Create initial summary.json with in_progress status."""
        summary = {
            "execution_time": self.start_time.isoformat(),
            "account_id": self.account_id,
            "status": "in_progress",
            "target_date": None,
            "desks_attempted": [],
            "result": None,
            "booked_desk": None,
            "duration_seconds": 0,
            "screenshots": 0,
            "screenshot_files": [],
        }
        filepath = os.path.join(self.log_dir, "summary.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    def update_summary(
        self,
        target_date: str | None = None,
        desks_attempted: list | None = None,
        result: str | None = None,
        booked_desk: str | None = None,
    ):
        """Update summary.json with current execution progress."""
        duration = (datetime.now() - self.start_time).total_seconds()
        summary = {
            "execution_time": self.start_time.isoformat(),
            "account_id": self.account_id,
            "status": "in_progress",
            "target_date": target_date,
            "desks_attempted": desks_attempted or [],
            "result": result,
            "booked_desk": booked_desk,
            "duration_seconds": round(duration, 2),
            "screenshots": len(self.screenshots),
            "screenshot_files": self.screenshots,
        }
        filepath = os.path.join(self.log_dir, "summary.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    def save_summary(
        self,
        target_date: str,
        desks_attempted: list,
        result: str,
        booked_desk: str | None = None,
    ):
        """Save a machine-readable execution summary."""
        duration = (datetime.now() - self.start_time).total_seconds()
        summary = {
            "execution_time": self.start_time.isoformat(),
            "account_id": self.account_id,
            "status": "completed",
            "target_date": target_date,
            "desks_attempted": desks_attempted,
            "result": result,
            "booked_desk": booked_desk,
            "duration_seconds": round(duration, 2),
            "screenshots": len(self.screenshots),
            "screenshot_files": self.screenshots,
        }
        filepath = os.path.join(self.log_dir, "summary.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self.info(f"Summary saved: {filepath}")
        return summary

    def finalize(self, result: str = "completed"):
        """Log final execution status."""
        duration = (datetime.now() - self.start_time).total_seconds()
        self.info(f"Execution {result} in {duration:.1f}s — {len(self.screenshots)} screenshots captured")
