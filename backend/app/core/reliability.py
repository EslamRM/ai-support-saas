"""Small, explicit retry primitives for transient infrastructure failures.

We retry only errors that are plausibly transient: timeouts, connection
errors, HTTP 429, and upstream 5xx responses. Validation errors, 4xx errors
and programming errors are not retried. Backoff is bounded and injectable
for deterministic tests.
"""
import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class RetryExhaustedError(RuntimeError):
    def __init__(self, operation: str, last_error: Exception):
        super().__init__(f"{operation} failed after retries: {last_error}")
        self.operation = operation
        self.last_error = last_error


def is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    if status == 429 or (isinstance(status, int) and 500 <= status <= 599):
        return True
    name = exc.__class__.__name__.lower()
    return any(token in name for token in ("timeout", "connection", "temporarilyunavailable", "ratelimit"))


def retry_call(
    operation: str,
    fn: Callable[[], T],
    *,
    max_attempts: int,
    base_delay: float,
    max_delay: float,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - policy is centralized below
            last_error = exc
            if attempt >= max_attempts or not is_retryable_error(exc):
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay *= 0.75 + 0.5 * jitter()
            sleep(delay)
    assert last_error is not None
    raise RetryExhaustedError(operation, last_error)
