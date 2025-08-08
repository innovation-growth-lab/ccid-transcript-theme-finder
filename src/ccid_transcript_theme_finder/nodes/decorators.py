"""Decorators for the theme-finder package."""

import asyncio
import functools
import logging
from typing import Any, Callable, Coroutine, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def async_retry(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """Decorator for async functions to add retry logic with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff (seconds)
        max_delay: Maximum delay between retries (seconds)

    """

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            retries = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if retries >= max_retries:
                        logger.error(f"Failed after {retries + 1} attempts: {e}")
                        raise

                    delay = min(base_delay * (2**retries), max_delay)
                    retries += 1
                    logger.warning(f"Attempt {retries}/{max_retries + 1} failed: {e}")
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)

        return wrapper

    return decorator
