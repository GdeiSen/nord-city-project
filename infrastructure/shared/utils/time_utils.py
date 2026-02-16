from datetime import datetime, timezone

def now() -> datetime:
    """Returns the current time with UTC timezone."""
    return datetime.now(timezone.utc)

def now_for_db() -> datetime:
    """Returns the current time without timezone info for database compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)