from collections.abc import Callable
from functools import wraps


def retry(
    max_attempts: int,
    retry_on: tuple[type[Exception], ...],
) -> Callable:
    if max_attempts <= 0:
        raise ValueError(f"max_attempts must be greater than 0, got {max_attempts}")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on:
                    if attempt == max_attempts:
                        raise

        return wrapper

    return decorator
