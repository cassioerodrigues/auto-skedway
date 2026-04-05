"""Dynamic booking URL construction with spaceId handling."""

from urllib.parse import urlencode

import config
from utils.date_utils import get_booking_date


def build_booking_url(
    desk_id: str,
    days_ahead: int = config.DEFAULT_DAYS_AHEAD,
    start_time: str = config.DEFAULT_START_TIME,
    end_time: str = config.DEFAULT_END_TIME,
) -> str:
    """Build the booking URL matching the actual Skedway format.

    Actual URL format (decoded):
      booking-form.php?baseType=1
        &spaceId[]=
        &startDate=YYYY-MM-DD HH:MM
        &endDate=YYYY-MM-DD HH:MM
        &timezone=America/Sao_Paulo
        &from=/booking.php?baseType=1
        &action=step1
        &day=DD/MM/YYYY
        &startTime=HH:MM
        &endTime=HH:MM
        &companySiteId=2210
        &buildingId=3933
        &floorId=5847
        &spaceType=0
        &order=availabilityDesc
        &page=1
        &spaceId[]=DESK_ID

    Args:
        desk_id: The desk/space ID to book.
        days_ahead: Days ahead for booking date.
        start_time: Booking start time (HH:MM).
        end_time: Booking end time (HH:MM).

    Returns:
        Complete booking URL string.
    """
    target_date = get_booking_date(days_ahead)  # YYYY-MM-DD

    # day param uses DD/MM/YYYY format
    parts = target_date.split("-")
    day_param = f"{parts[2]}/{parts[1]}/{parts[0]}"

    # startDate/endDate include time: "YYYY-MM-DD HH:MM"
    start_date_time = f"{target_date} {start_time}"
    end_date_time = f"{target_date} {end_time}"

    params = [
        ("baseType", config.BOOKING_BASE_TYPE),
        ("spaceId[]", ""),                          # First spaceId[] — empty
        ("startDate", start_date_time),
        ("endDate", end_date_time),
        ("timezone", config.BOOKING_TIMEZONE),
        ("from", config.BOOKING_FROM),
        ("action", config.BOOKING_ACTION),
        ("day", day_param),
        ("startTime", start_time),
        ("endTime", end_time),
        ("companySiteId", config.BOOKING_COMPANY_SITE_ID),
        ("buildingId", config.BOOKING_BUILDING_ID),
        ("floorId", config.BOOKING_FLOOR_ID),
        ("spaceType", config.BOOKING_SPACE_TYPE),
        ("order", config.BOOKING_ORDER),
        ("page", config.BOOKING_PAGE),
        ("spaceId[]", desk_id),                     # Second spaceId[] — target desk
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
