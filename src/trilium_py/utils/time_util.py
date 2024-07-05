import dateutil
from datetime import timedelta, datetime
from typing import Optional


def get_today():
    return datetime.now().strftime("%Y-%m-%d")


def get_yesterday():
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def get_local_timezone():
    print("Getting local_timezone...")

    # this is short and sweet
    local_timezone = datetime.now().astimezone().tzinfo

    # So why the heck did I think we need all this? Delete if this reason doesn't
    # reappear soon
    # # Get the local timezone offset in minutes and create a timezone object
    # offset_min = -1 * time.timezone if (time.localtime().tm_isdst == 0) else -1 * time.altzone
    # offset = timedelta(seconds=offset_min)
    # local_timezone = timezone(offset)

    print(f"timezone: {local_timezone}")
    return local_timezone


def synchronize_dates(
    local_date: Optional[datetime], utc_date: Optional[datetime]
) -> tuple[Optional[datetime], Optional[datetime]]:
    """Synchronize local and UTC dates. We expect only one of local or utc date to
    be passed, use that to define the other, and return both as datetime objects."""
    if local_date and utc_date:
        msg = "Both local and UTC dates were provided, cannot determine which to use.\n"
        msg = msg + "Please pass only one of local or UTC date."
        raise ValueError(msg)

    local_timezone = get_local_timezone()

    if local_date and not utc_date:
        utc_date = local_date.astimezone(dateutil.tz.tzutc())
        # utc_date = local_date.astimezone(dateutil.tz.tzstr('Z'))
    elif utc_date and not local_date:
        local_date = utc_date.astimezone(local_timezone)
    elif local_date and utc_date != utc_date.astimezone(dateutil.tz.tzlocal()):
        raise ValueError("local_date and utc_date are inconsistent.")

    print("Synchronized dates:")
    print(f"\tlocal_date: {local_date}")
    print(f"\tutc_date  : {utc_date}")
    return local_date, utc_date


def format_date_to_etapi(date: datetime, kind: str) -> str:
    """From a datetime object, return a date string formatted to ETAPI requirements:
            local: '2023-08-21 23:38:51.110-0200'
            UTC  : '2023-08-22 01:38:51.110Z'
    and exactly 3 decimal places for seconds."""
    if kind == "local":
        date = date.strftime("%Y-%m-%d %H:%M:%S.%d3%z")
    if kind == "utc":
        date = date.astimezone(dateutil.tz.tzstr("Z"))  # use Zulu time
        date = date.strftime("%Y-%m-%d %H:%M:%S.%d3%Z")
    print(f"ETAPI Formatted date kind: {kind}")
    print(f"\t{date}")
    # print(f'\t{type (date)}')
    return date
