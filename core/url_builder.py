"""Dynamic booking URL construction with spaceId handling."""

from urllib.parse import urlencode

import config
from utils.date_utils import get_booking_date


def build_booking_url(
    desk_id: str,
    days_ahead: int = config.DEFAULT_DAYS_AHEAD,
    start_time: str = config.DEFAULT_START_TIME,
    end_time: str = config.DEFAULT_END_TIME,
    site_params: dict | None = None,
) -> str:
    """Build the booking URL matching the actual Skedway format.

    Args:
        desk_id: The desk/space ID to book.
        days_ahead: Days ahead for booking date.
        start_time: Booking start time (HH:MM).
        end_time: Booking end time (HH:MM).
        site_params: Per-account site parameters. Falls back to config defaults.

    Returns:
        Complete booking URL string.
    """
    sp = site_params or config.DEFAULT_SITE_PARAMS
    target_date = get_booking_date(days_ahead)  # YYYY-MM-DD

    # day param uses DD/MM/YYYY format
    parts = target_date.split("-")
    day_param = f"{parts[2]}/{parts[1]}/{parts[0]}"

    # startDate/endDate include time: "YYYY-MM-DD HH:MM"
    start_date_time = f"{target_date} {start_time}"
    end_date_time = f"{target_date} {end_time}"

    params = [
        ("baseType", sp.get("base_type", config.BOOKING_BASE_TYPE)),
        ("spaceId[]", ""),
        ("startDate", start_date_time),
        ("endDate", end_date_time),
        ("timezone", sp.get("timezone", config.BOOKING_TIMEZONE)),
        ("from", sp.get("from", config.BOOKING_FROM)),
        ("action", sp.get("action", config.BOOKING_ACTION)),
        ("day", day_param),
        ("startTime", start_time),
        ("endTime", end_time),
        ("companySiteId", sp.get("company_site_id", config.BOOKING_COMPANY_SITE_ID)),
        ("buildingId", sp.get("building_id", config.BOOKING_BUILDING_ID)),
        ("floorId", sp.get("floor_id", config.BOOKING_FLOOR_ID)),
        ("spaceType", sp.get("space_type", config.BOOKING_SPACE_TYPE)),
        ("order", sp.get("order", config.BOOKING_ORDER)),
        ("page", sp.get("page", config.BOOKING_PAGE)),
        ("spaceId[]", desk_id),
    ]

    query_string = urlencode(params)
    return f"{config.BOOKING_BASE_URL}?{query_string}"


def get_target_date(days_ahead: int = config.DEFAULT_DAYS_AHEAD) -> str:
    """Get the target booking date string.

    Args:
        days_ahead: Days ahead for booking date.

    Returns:
        Date string in YYYY-MM-DD format.
    """
    return get_booking_date(days_ahead)
