"""
Retry decorator utility for handling transient failures with Rich visualization.
"""

import time
from functools import wraps
from typing import Type, List


def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff_factor: float = 3.0,
    exceptions: List[Type[Exception]] = None,
):
    """
    Retry decorator for handling transient failures with Rich visualization.
    Uses techniques that don't conflict with other Live displays.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff_factor: Multiplier for delay between retries (default: 2.0)
        exceptions: List of exceptions to catch (default: all exceptions)

    Returns:
        A decorator function that will retry the decorated function on failure.
    """
    exceptions = exceptions or [Exception]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)

                except tuple(exceptions) as e:
                    if attempt < max_attempts:
                        print(
                            "Warning: "
                            f"Attempt {attempt}/{max_attempts}. "
                            f"Retrying in {current_delay:.2f}s"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                        attempt += 1
                    else:
                        print(
                            "Warning: "
                            f"Attempt {attempt}/{max_attempts}. "
                            "Max retries exceeded. Exiting."
                        )
                        raise

        return wrapper

    return decorator
