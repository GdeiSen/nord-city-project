from datetime import datetime, timezone, timedelta
from typing import Optional
import ntplib
import time
import threading
from functools import wraps

# Конфигурация часового пояса - изменяйте здесь для смены часового пояса всей системы
# Московский часовой пояс (UTC+3)
SYSTEM_TIMEZONE = timezone(timedelta(hours=3))

# NTP server configuration
DEFAULT_NTP_SERVERS = [
    'pool.ntp.org',
    'time.google.com',
    'time.cloudflare.com',
    'time.windows.com'
]

class TimeUtils:
    """
    Centralized utility for working with time in system timezone with NTP synchronization support.
    
    This class provides methods for time operations, NTP synchronization, and maintains
    an offset correction value for accurate time calculations when the system clock
    is not perfectly synchronized.
    """
    
    # Class variables for NTP synchronization
    _ntp_offset: Optional[float] = None
    _last_sync_time: Optional[float] = None
    _sync_lock = threading.Lock()
    _sync_interval = 3600  # Sync every hour by default
    
    @staticmethod
    def now() -> datetime:
        """
        Returns current time in system timezone with NTP offset correction if available.
        
        Returns:
            datetime: Current time in system timezone, corrected with NTP offset if synced.
            
        Example:
            >>> current_time = TimeUtils.now()
            >>> print(current_time)
            2024-01-15 14:30:25.123456+03:00
        """
        base_time = datetime.now(SYSTEM_TIMEZONE)
        if TimeUtils._ntp_offset is not None:
            base_time = base_time + timedelta(seconds=TimeUtils._ntp_offset)
        return base_time
    
    @staticmethod
    def utcnow() -> datetime:
        """
        Returns current time in UTC with NTP offset correction if available.
        
        Returns:
            datetime: Current time in UTC, corrected with NTP offset if synced.
            
        Example:
            >>> utc_time = TimeUtils.utcnow()
            >>> print(utc_time)
            2024-01-15 11:30:25.123456+00:00
        """
        base_time = datetime.now(timezone.utc)
        if TimeUtils._ntp_offset is not None:
            base_time = base_time + timedelta(seconds=TimeUtils._ntp_offset)
        return base_time
    
    @staticmethod
    def sync_with_ntp(servers: Optional[list] = None, timeout: float = 10.0) -> bool:
        """
        Synchronizes time with NTP servers and calculates offset correction.
        
        This method attempts to connect to NTP servers in order and calculates
        the time difference between system time and NTP time. The offset is
        stored and used in subsequent time calculations.
        
        Args:
            servers (list, optional): List of NTP server addresses to try.
                                    Defaults to DEFAULT_NTP_SERVERS.
            timeout (float): Connection timeout in seconds. Defaults to 10.0.
            
        Returns:
            bool: True if synchronization was successful, False otherwise.
            
        Example:
            >>> success = TimeUtils.sync_with_ntp()
            >>> if success:
            ...     print("NTP synchronization successful")
            ... else:
            ...     print("NTP synchronization failed")
        """
        if servers is None:
            servers = DEFAULT_NTP_SERVERS
            
        with TimeUtils._sync_lock:
            ntp_client = ntplib.NTPClient()
            
            for server in servers:
                try:
                    # Get NTP response from server
                    response = ntp_client.request(server, timeout=timeout)
                    
                    # Calculate offset between system time and NTP time
                    # offset = NTP time - system time
                    ntp_time = response.tx_time
                    system_time = time.time()
                    TimeUtils._ntp_offset = ntp_time - system_time
                    TimeUtils._last_sync_time = system_time
                    
                    return True
                    
                except (ntplib.NTPException, OSError) as e:
                    # Log error and try next server
                    continue
                    
            # All servers failed
            return False
    
    @staticmethod
    def get_ntp_offset() -> Optional[float]:
        """
        Returns the current NTP offset in seconds.
        
        Returns:
            float or None: Time offset in seconds, or None if not synchronized.
            
        Example:
            >>> offset = TimeUtils.get_ntp_offset()
            >>> if offset is not None:
            ...     print(f"System clock is {offset:.3f} seconds behind NTP")
        """
        return TimeUtils._ntp_offset
    
    @staticmethod
    def get_last_sync_time() -> Optional[datetime]:
        """
        Returns the timestamp of the last successful NTP synchronization.
        
        Returns:
            datetime or None: Timestamp of last sync in system timezone, 
                            or None if never synchronized.
            
        Example:
            >>> last_sync = TimeUtils.get_last_sync_time()
            >>> if last_sync:
            ...     print(f"Last sync: {last_sync}")
        """
        if TimeUtils._last_sync_time is None:
            return None
        return datetime.fromtimestamp(TimeUtils._last_sync_time, SYSTEM_TIMEZONE)
    
    @staticmethod
    def is_sync_needed() -> bool:
        """
        Checks if NTP synchronization is needed based on sync interval.
        
        Returns:
            bool: True if sync is needed (never synced or interval exceeded), 
                  False otherwise.
                  
        Example:
            >>> if TimeUtils.is_sync_needed():
            ...     TimeUtils.sync_with_ntp()
        """
        if TimeUtils._last_sync_time is None:
            return True
            
        return (time.time() - TimeUtils._last_sync_time) > TimeUtils._sync_interval
    
    @staticmethod
    def auto_sync_if_needed() -> bool:
        """
        Automatically performs NTP synchronization if needed.
        
        This method checks if synchronization is needed based on the sync interval
        and performs it if necessary. Safe to call repeatedly.
        
        Returns:
            bool: True if sync was performed and successful, False if not needed 
                  or failed.
                  
        Example:
            >>> TimeUtils.auto_sync_if_needed()  # Call periodically
        """
        if TimeUtils.is_sync_needed():
            return TimeUtils.sync_with_ntp()
        return False
    
    @staticmethod
    def set_sync_interval(seconds: int) -> None:
        """
        Sets the automatic synchronization interval.
        
        Args:
            seconds (int): Interval between automatic syncs in seconds.
                          Must be positive.
                          
        Raises:
            ValueError: If seconds is not positive.
            
        Example:
            >>> TimeUtils.set_sync_interval(1800)  # Sync every 30 minutes
        """
        if seconds <= 0:
            raise ValueError("Sync interval must be positive")
        TimeUtils._sync_interval = seconds
    
    @staticmethod
    def get_system_timezone() -> timezone:
        """
        Returns the system timezone object.
        
        Returns:
            timezone: The configured system timezone object.
            
        Example:
            >>> tz = TimeUtils.get_system_timezone()
            >>> print(tz)
            datetime.timezone(datetime.timedelta(seconds=10800))
        """
        return SYSTEM_TIMEZONE
    
    @staticmethod
    def to_system_time(dt: datetime) -> datetime:
        """
        Converts datetime to system time with NTP offset correction.
        
        Args:
            dt (datetime): Datetime object to convert. If timezone-naive,
                          assumed to be UTC.
                          
        Returns:
            datetime: Datetime converted to system timezone with NTP correction.
            
        Example:
            >>> utc_time = datetime.now(timezone.utc)
            >>> system_time = TimeUtils.to_system_time(utc_time)
        """
        if dt.tzinfo is None:
            # If time without timezone, assume it's UTC
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to system timezone
        system_dt = dt.astimezone(SYSTEM_TIMEZONE)
        
        # Apply NTP offset correction if available
        if TimeUtils._ntp_offset is not None:
            system_dt = system_dt + timedelta(seconds=TimeUtils._ntp_offset)
            
        return system_dt
    
    @staticmethod
    def format_time(dt: Optional[datetime] = None, format_str: str = "%d.%m.%Y %H:%M") -> str:
        """
        Formats time in system timezone with NTP correction.
        
        Args:
            dt (datetime, optional): Datetime to format. If None, uses current time.
                                   If timezone-naive, assumed to be UTC.
            format_str (str): Format string for strftime. Defaults to "%d.%m.%Y %H:%M".
            
        Returns:
            str: Formatted time string in system timezone.
            
        Example:
            >>> formatted = TimeUtils.format_time()
            >>> print(formatted)
            15.01.2024 14:30
        """
        if dt is None:
            dt = TimeUtils.now()
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        system_time = dt.astimezone(SYSTEM_TIMEZONE)
        
        # Apply NTP offset correction if available
        if TimeUtils._ntp_offset is not None:
            system_time = system_time + timedelta(seconds=TimeUtils._ntp_offset)
            
        return system_time.strftime(format_str)

# Decorator for automatic NTP sync
def with_ntp_sync(func):
    """
    Decorator that automatically performs NTP synchronization if needed before function execution.
    
    Args:
        func: Function to decorate.
        
    Returns:
        function: Decorated function that performs auto-sync before execution.
        
    Example:
        @with_ntp_sync
        def get_current_time():
            return TimeUtils.now()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        TimeUtils.auto_sync_if_needed()
        return func(*args, **kwargs)
    return wrapper

# Глобальные функции для удобства использования
def now() -> datetime:
    """
    Returns current time in system timezone with NTP correction.
    
    Returns:
        datetime: Current time in system timezone, NTP-corrected if available.
        
    Example:
        >>> current_time = now()
        >>> print(current_time)
    """
    return TimeUtils.now()

def utcnow() -> datetime:
    """
    Returns current time in UTC with NTP correction.
    
    Returns:
        datetime: Current time in UTC, NTP-corrected if available.
        
    Example:
        >>> utc_time = utcnow()
        >>> print(utc_time)
    """
    return TimeUtils.utcnow()

# Для использования в моделях SQLAlchemy
def now_for_db():
    """
    Function for use in SQLAlchemy model default parameters.
    
    Returns:
        datetime: Current time in system timezone for database storage.
        
    Example:
        class MyModel(Base):
            created_at = Column(DateTime, default=now_for_db)
    """
    return TimeUtils.now()

def utc_now_for_db():
    """
    Function for use in SQLAlchemy model default parameters (UTC).
    
    Returns:
        datetime: Current time in UTC for database storage.
        
    Example:
        class MyModel(Base):
            created_at = Column(DateTime, default=utc_now_for_db)
    """
    return TimeUtils.utcnow() 