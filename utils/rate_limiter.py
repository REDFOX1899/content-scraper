"""
Rate limiting utilities for API and web scraping requests.
"""
import time
import threading
from functools import wraps
from collections import deque
from typing import Callable, Optional
from loguru import logger


class RateLimiter:
    """Token bucket rate limiter implementation."""

    def __init__(self, calls: int, period: int):
        """
        Initialize rate limiter.

        Args:
            calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.timestamps = deque()
        self.lock = threading.Lock()

    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply rate limiting to a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                now = time.time()

                # Remove timestamps outside the current window
                while self.timestamps and self.timestamps[0] <= now - self.period:
                    self.timestamps.popleft()

                # If we've hit the limit, wait
                if len(self.timestamps) >= self.calls:
                    sleep_time = self.period - (now - self.timestamps[0])
                    if sleep_time > 0:
                        logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                        time.sleep(sleep_time)
                        # Clean up old timestamps after waking
                        now = time.time()
                        while self.timestamps and self.timestamps[0] <= now - self.period:
                            self.timestamps.popleft()

                # Add current timestamp
                self.timestamps.append(now)

            return func(*args, **kwargs)

        return wrapper

    def wait_if_needed(self):
        """Manually check and wait if rate limit is exceeded."""
        with self.lock:
            now = time.time()

            # Remove old timestamps
            while self.timestamps and self.timestamps[0] <= now - self.period:
                self.timestamps.popleft()

            # If we've hit the limit, wait
            if len(self.timestamps) >= self.calls:
                sleep_time = self.period - (now - self.timestamps[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    now = time.time()
                    while self.timestamps and self.timestamps[0] <= now - self.period:
                        self.timestamps.popleft()

            self.timestamps.append(now)


class AdaptiveRateLimiter:
    """Rate limiter that adapts based on API responses."""

    def __init__(self, initial_calls: int, period: int, min_calls: int = 1):
        """
        Initialize adaptive rate limiter.

        Args:
            initial_calls: Initial number of calls allowed
            period: Time period in seconds
            min_calls: Minimum calls to throttle down to
        """
        self.calls = initial_calls
        self.initial_calls = initial_calls
        self.period = period
        self.min_calls = min_calls
        self.timestamps = deque()
        self.lock = threading.Lock()
        self.consecutive_rate_limits = 0

    def throttle_down(self):
        """Reduce the rate limit after hitting API limits."""
        with self.lock:
            self.consecutive_rate_limits += 1
            if self.calls > self.min_calls:
                old_calls = self.calls
                self.calls = max(self.min_calls, self.calls // 2)
                logger.warning(
                    f"Rate limit hit, throttling down from {old_calls} to {self.calls} calls per {self.period}s"
                )

    def throttle_up(self):
        """Increase the rate limit after successful requests."""
        with self.lock:
            if self.consecutive_rate_limits > 0:
                self.consecutive_rate_limits -= 1
            elif self.calls < self.initial_calls:
                old_calls = self.calls
                self.calls = min(self.initial_calls, int(self.calls * 1.5))
                logger.info(
                    f"Throttling up from {old_calls} to {self.calls} calls per {self.period}s"
                )

    def wait_if_needed(self):
        """Check and wait if rate limit is exceeded."""
        with self.lock:
            now = time.time()

            # Remove old timestamps
            while self.timestamps and self.timestamps[0] <= now - self.period:
                self.timestamps.popleft()

            # If we've hit the limit, wait
            if len(self.timestamps) >= self.calls:
                sleep_time = self.period - (now - self.timestamps[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    now = time.time()
                    while self.timestamps and self.timestamps[0] <= now - self.period:
                        self.timestamps.popleft()

            self.timestamps.append(now)


def rate_limit(calls: int = 10, period: int = 60):
    """
    Decorator factory for rate limiting.

    Args:
        calls: Maximum number of calls
        period: Time period in seconds

    Returns:
        Decorated function with rate limiting
    """
    limiter = RateLimiter(calls, period)
    return limiter


def delay(seconds: float):
    """
    Add a fixed delay between function calls.

    Args:
        seconds: Delay in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            time.sleep(seconds)
            return result
        return wrapper
    return decorator
