"""Date utilities for booking date calculation."""

from datetime import datetime, timedelta


def get_booking_date(days_ahead: int = 7) -> str:
    """Calculate the booking date (today + days_ahead).

    Args:
        days_ahead: Number of days in the future. Default is 7.

    Returns:
        Date string in YYYY-MM-DD format.
    """
    target = datetime.now() + timedelta(days=days_ahead)
    return target.strftime("%Y-%m-%d")


def get_day_of_week(date_str: str) -> int:
    """Get the day of week (0=Monday, 6=Sunday) for a given date string.

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        Integer day of week.
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.weekday()


def is_weekday(date_str: str) -> bool:
    """Check if a date is a weekday (Mon-Fri).

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        True if weekday, False if weekend.
    """
    return get_day_of_week(date_str) < 5


def format_date_display(date_str: str) -> str:
    """Format date for display (e.g., 'Monday, April 12, 2026').

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        Human-readable date string.
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%A, %B %d, %Y")
