from app.core.reliability import is_retryable_error, retry_call


def test_retry_call_retries_transient_error_then_succeeds():
    calls = {"n": 0}
    sleeps = []

    def operation():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("upstream timeout")
        return "ok"

    assert retry_call(
        "test",
        operation,
        max_attempts=3,
        base_delay=0,
        max_delay=0,
        sleep=sleeps.append,
        jitter=lambda: 0.5,
    ) == "ok"
    assert calls["n"] == 3
    assert len(sleeps) == 2


def test_retry_call_does_not_retry_non_transient_error():
    calls = {"n": 0}

    def operation():
        calls["n"] += 1
        raise ValueError("bad input")

    try:
        retry_call(
            "test",
            operation,
            max_attempts=3,
            base_delay=0,
            max_delay=0,
            sleep=lambda _: None,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")

    assert calls["n"] == 1


def test_rate_limit_status_is_retryable():
    class RateLimitedError(Exception):
        status_code = 429

    assert is_retryable_error(RateLimitedError())
