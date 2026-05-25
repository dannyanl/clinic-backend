from datetime import date, datetime, time, timedelta, timezone


def combine_date_time(d: date, t: time) -> datetime:
    return datetime.combine(d, t, tzinfo=timezone.utc)


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)
