import dateutil
from datetime import timedelta, datetime
from typing import Optional, Tuple, Union
from loguru import logger


def get_today() -> str:
    """
    Get today's date in YYYY-MM-DD format.

    Returns:
        str: Today's date as a string in format "%Y-%m-%d"
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_yesterday() -> str:
    """
    Get yesterday's date in YYYY-MM-DD format.

    Returns:
        str: Yesterday's date as a string in format "%Y-%m-%d"
    """
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def get_local_timezone():
    """
    Get the local timezone.

    Returns:
        tzinfo: The local timezone info
    """
    logger.debug("Getting local timezone")
    local_timezone = datetime.now().astimezone().tzinfo
    logger.debug(f"Local timezone: {local_timezone}")
    return local_timezone


def ensure_timezone(dt: datetime, tz=None) -> datetime:
    """
    Ensure a datetime object has timezone information.

    Args:
        dt (datetime): The datetime object to check
        tz: The timezone to use if dt has no timezone. If None, use local timezone.

    Returns:
        datetime: A datetime object with timezone information
    """
    if dt.tzinfo is None:
        if tz is None:
            tz = get_local_timezone()
        dt = dt.replace(tzinfo=tz)
        logger.debug(f"Added timezone to datetime: {dt}")
    return dt


def handle_dates(
    dateCreated: Optional[datetime] = None,
    utcDateCreated: Optional[datetime] = None
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Ensure that both local and UTC times are defined and have the same time
    (adjusted for timezone).

    Args:
        dateCreated (datetime, optional): Local datetime
        utcDateCreated (datetime, optional): UTC datetime

    Returns:
        tuple: (local_datetime, utc_datetime)

    Raises:
        TypeError: If dateCreated or utcDateCreated is not a datetime object
    """
    if not dateCreated and not utcDateCreated:
        return None, None

    if dateCreated and not isinstance(dateCreated, datetime):
        logger.error(f"dateCreated is not datetime object, is {type(dateCreated)}")
        raise TypeError("dateCreated must be a datetime object")

    if utcDateCreated and not isinstance(utcDateCreated, datetime):
        logger.error(f"utcDateCreated is not datetime object, is {type(utcDateCreated)}")
        raise TypeError("utcDateCreated must be a datetime object")

    # Ensure timezone info is set
    if dateCreated:
        dateCreated = ensure_timezone(dateCreated)

    if utcDateCreated:
        utcDateCreated = ensure_timezone(utcDateCreated, dateutil.tz.tzutc())

    # Synchronize dates
    return synchronize_dates(local_date=dateCreated, utc_date=utcDateCreated)


def synchronize_dates(
    local_date: Optional[datetime],
    utc_date: Optional[datetime]
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Synchronize local and UTC dates. We expect only one of local or utc date to
    be passed, use that to define the other, and return both as datetime objects.

    Args:
        local_date (datetime, optional): Local datetime with timezone info
        utc_date (datetime, optional): UTC datetime with timezone info

    Returns:
        tuple: (local_datetime, utc_datetime)

    Raises:
        ValueError: If both local_date and utc_date are provided
    """
    if local_date and utc_date:
        msg = "Both local and UTC dates were provided, cannot determine which to use.\n"
        msg = msg + "Please pass only one of local or UTC date."
        logger.error(msg)
        raise ValueError(msg)

    local_timezone = get_local_timezone()

    if local_date and not utc_date:
        utc_date = local_date.astimezone(dateutil.tz.tzutc())
    elif utc_date and not local_date:
        local_date = utc_date.astimezone(local_timezone)
    elif local_date and utc_date != utc_date.astimezone(dateutil.tz.tzlocal()):
        logger.error("local_date and utc_date are inconsistent")
        raise ValueError("local_date and utc_date are inconsistent.")

    logger.debug(f"Synchronized dates: local={local_date}, utc={utc_date}")
    return local_date, utc_date


def format_date_to_etapi(date: datetime, kind: str) -> str:
    """
    From a datetime object, return a date string formatted to ETAPI requirements.

    Args:
        date (datetime): The datetime object to format
        kind (str): Either 'local' or 'utc'

    Returns:
        str: Formatted date string
            local: '2023-08-21 23:38:51.110-0200'
            UTC  : '2023-08-22 01:38:51.110Z'
    """
    if kind == "local":
        formatted_date = date.strftime("%Y-%m-%d %H:%M:%S.%d3%z")
    elif kind == "utc":
        date = date.astimezone(dateutil.tz.tzstr("Z"))  # use Zulu time
        formatted_date = date.strftime("%Y-%m-%d %H:%M:%S.%d3%Z")
    else:
        raise ValueError(f"Invalid kind: {kind}. Must be 'local' or 'utc'")

    logger.debug(f"ETAPI Formatted date ({kind}): {formatted_date}")
    return formatted_date


def format_dates_for_api(
    local_date: Optional[datetime] = None,
    utc_date: Optional[datetime] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Format dates for API calls. This is a convenience function that combines
    handle_dates and format_date_to_etapi.

    Args:
        local_date (datetime, optional): Local datetime
        utc_date (datetime, optional): UTC datetime

    Returns:
        tuple: (formatted_local_date, formatted_utc_date)
    """
    if not local_date and not utc_date:
        return None, None

    local_dt, utc_dt = handle_dates(dateCreated=local_date, utcDateCreated=utc_date)

    if not local_dt or not utc_dt:
        return None, None

    local_str = format_date_to_etapi(local_dt, kind='local')
    utc_str = format_date_to_etapi(utc_dt, kind='utc')

    return local_str, utc_str
