"""Tests for URL builder module."""

import sys
import os
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs, unquote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.url_builder import build_booking_url


class TestBuildBookingUrl:
    """Tests for build_booking_url function."""

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_url_contains_base(self, mock_date):
        url = build_booking_url("1234")
        assert url.startswith("https://volvo.skedway.com/booking-form.php?")

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_start_date_includes_time(self, mock_date):
        url = unquote(build_booking_url("1234"))
        # Space is encoded as + in URL
        assert "startDate=2026-04-12+08:30" in url or "startDate=2026-04-12 08:30" in url

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_end_date_includes_time(self, mock_date):
        url = unquote(build_booking_url("1234"))
        assert "endDate=2026-04-12+17:00" in url or "endDate=2026-04-12 17:00" in url

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_day_param_dd_mm_yyyy(self, mock_date):
        url = unquote(build_booking_url("1234"))
        assert "day=12/04/2026" in url

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_url_has_default_times(self, mock_date):
        url = unquote(build_booking_url("1234"))
        assert "startTime=08:30" in url
        assert "endTime=17:00" in url

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_url_has_custom_times(self, mock_date):
        url = unquote(build_booking_url("1234", start_time="09:00", end_time="18:00"))
        assert "startTime=09:00" in url
        assert "endTime=18:00" in url

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_url_has_two_space_ids(self, mock_date):
        url = build_booking_url("1234")
        count = url.count("spaceId")
        assert count == 2, f"Expected 2 spaceId params, found {count}"

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_first_space_id_is_empty(self, mock_date):
        url = build_booking_url("1234")
        assert "spaceId%5B%5D=&" in url

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_second_space_id_has_desk(self, mock_date):
        url = build_booking_url("81506")
        assert url.endswith("spaceId%5B%5D=81506")

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_has_base_type(self, mock_date):
        url = unquote(build_booking_url("1234"))
        assert "baseType=1" in url

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_has_timezone(self, mock_date):
        url = unquote(build_booking_url("1234"))
        assert "timezone=America/Sao_Paulo" in url

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_has_site_params(self, mock_date):
        url = unquote(build_booking_url("1234"))
        assert "companySiteId=2210" in url
        assert "buildingId=3933" in url
        assert "floorId=5847" in url

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_has_action_step1(self, mock_date):
        url = unquote(build_booking_url("1234"))
        assert "action=step1" in url

    @patch("core.url_builder.get_booking_date", return_value="2026-04-12")
    def test_different_desk_ids(self, mock_date):
        url1 = build_booking_url("111")
        url2 = build_booking_url("222")
        assert "111" in url1
        assert "222" in url2
        assert "111" not in url2
