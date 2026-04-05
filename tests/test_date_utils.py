"""Tests for date utilities module."""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.date_utils import get_booking_date, get_day_of_week, is_weekday, format_date_display


class TestGetBookingDate:
    """Tests for get_booking_date function."""

    def test_default_7_days_ahead(self):
        expected = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        assert get_booking_date() == expected

    def test_custom_days_ahead(self):
        expected = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        assert get_booking_date(14) == expected

    def test_zero_days_ahead(self):
        expected = datetime.now().strftime("%Y-%m-%d")
        assert get_booking_date(0) == expected

    def test_format_yyyy_mm_dd(self):
        result = get_booking_date()
        parts = result.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # year
        assert len(parts[1]) == 2  # month
        assert len(parts[2]) == 2  # day


class TestGetDayOfWeek:
    """Tests for get_day_of_week function."""

    def test_known_monday(self):
        # 2026-04-06 is a Monday
        assert get_day_of_week("2026-04-06") == 0

    def test_known_friday(self):
        # 2026-04-10 is a Friday
        assert get_day_of_week("2026-04-10") == 4

    def test_known_sunday(self):
        # 2026-04-05 is a Sunday
        assert get_day_of_week("2026-04-05") == 6


class TestIsWeekday:
    """Tests for is_weekday function."""

    def test_weekday(self):
        assert is_weekday("2026-04-06") is True  # Monday

    def test_weekend_saturday(self):
        assert is_weekday("2026-04-04") is False  # Saturday

    def test_weekend_sunday(self):
        assert is_weekday("2026-04-05") is False  # Sunday


class TestFormatDateDisplay:
    """Tests for format_date_display function."""

    def test_format_output(self):
        result = format_date_display("2026-04-12")
        assert "April" in result
        assert "12" in result
        assert "2026" in result
