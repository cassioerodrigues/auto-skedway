"""Tests for configuration module."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


class TestConfig:
    """Tests for configuration constants."""

    def test_login_url(self):
        assert config.LOGIN_URL == "https://console.skedway.com/"

    def test_booking_base_url(self):
        assert config.BOOKING_BASE_URL == "https://volvo.skedway.com/booking-form.php"

    def test_default_times(self):
        assert config.DEFAULT_START_TIME == "08:30"
        assert config.DEFAULT_END_TIME == "17:00"

    def test_default_days_ahead(self):
        assert config.DEFAULT_DAYS_AHEAD == 7

    def test_timeouts_are_positive(self):
        assert config.PAGE_LOAD_TIMEOUT > 0
        assert config.CLICK_TIMEOUT > 0
        assert config.LOGIN_TIMEOUT > 0
        assert config.TOTAL_TIMEOUT > 0

    def test_selectors_not_empty(self):
        assert len(config.LOGIN_EMAIL_SELECTORS) > 0
        assert len(config.LOGIN_PASSWORD_SELECTORS) > 0
        assert len(config.LOGIN_SUBMIT_SELECTORS) > 0
        assert len(config.BOOKING_SUBMIT_SELECTORS) > 0

    def test_browser_channel(self):
        assert config.BROWSER_CHANNEL == "msedge"

    def test_viewport_dimensions(self):
        assert config.VIEWPORT_WIDTH >= 1024
        assert config.VIEWPORT_HEIGHT >= 768
