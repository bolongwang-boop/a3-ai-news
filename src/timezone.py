from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SYDNEY_TZ = ZoneInfo("Australia/Sydney")
UTC_TZ = ZoneInfo("UTC")


def get_week_range_sydney(days_back: int = 7) -> tuple[datetime, datetime]:
    """Calculate the 'last N days' range in Sydney time, returned as UTC datetimes.

    The start boundary is midnight Sydney time N days ago.
    The end boundary is the current moment in Sydney time.
    Both are converted to UTC for use with news APIs.
    """
    now_sydney = datetime.now(SYDNEY_TZ)

    to_utc = now_sydney.astimezone(UTC_TZ)

    start_sydney = (now_sydney - timedelta(days=days_back)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    from_utc = start_sydney.astimezone(UTC_TZ)

    return from_utc, to_utc


def utc_to_sydney_str(utc_dt: datetime) -> str:
    """Convert a UTC datetime to a human-readable Sydney time string."""
    sydney_dt = utc_dt.astimezone(SYDNEY_TZ)
    # Include the timezone abbreviation (AEDT or AEST depending on DST)
    return sydney_dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def is_within_sydney_range(
    published_at: datetime, from_utc: datetime, to_utc: datetime
) -> bool:
    """Check if a publication datetime falls within the Sydney-based range."""
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC_TZ)
    return from_utc <= published_at <= to_utc
