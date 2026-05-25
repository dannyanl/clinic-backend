from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from app.config.settings import settings


def loc_tz(tz_name: str | None) -> ZoneInfo:
    return ZoneInfo(tz_name or settings.DEFAULT_TIMEZONE)


def localize(dt: datetime, tz_name: str | None) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(loc_tz(tz_name))


def combine_local(date_, time_: time, tz_name: str | None) -> datetime:
    return datetime.combine(date_, time_, tzinfo=loc_tz(tz_name)).astimezone(timezone.utc)
