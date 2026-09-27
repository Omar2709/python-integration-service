import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

import pytest

from python_integration_service.integrations.rate_limit import (
    NoOpRateLimiter,
    TokenBucketRateLimiter,
)


class FakeTime:
    def __init__(self) -> None:
        self.current = 0.0
        self.sleep_calls: list[float] = []

    def monotonic(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self.current += seconds

    def advance(self, seconds: float) -> None:
        self.current += seconds


class ThreadSafeFakeClock:
    def __init__(self) -> None:
        self._current = 0.0
        self._lock = threading.Lock()

    def monotonic(self) -> float:
        with self._lock:
            return self._current

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._current += seconds


def test_token_bucket_starts_at_full_capacity() -> None:
    fake_time = FakeTime()
    limiter = TokenBucketRateLimiter(
        requests_per_second=2.0,
        capacity=2,
        clock=fake_time.monotonic,
        sleep=fake_time.sleep,
    )

    limiter.acquire()
    limiter.acquire()

    assert fake_time.sleep_calls == []


def test_token_bucket_waits_when_capacity_is_exhausted() -> None:
    fake_time = FakeTime()
    limiter = TokenBucketRateLimiter(
        requests_per_second=2.0,
        capacity=2,
        clock=fake_time.monotonic,
        sleep=fake_time.sleep,
    )

    limiter.acquire()
    limiter.acquire()
    limiter.acquire()

    assert fake_time.sleep_calls == pytest.approx([0.5])


def test_token_bucket_preserves_fractional_refill() -> None:
    fake_time = FakeTime()
    limiter = TokenBucketRateLimiter(
        requests_per_second=2.0,
        capacity=1,
        clock=fake_time.monotonic,
        sleep=fake_time.sleep,
    )

    limiter.acquire()
    fake_time.advance(0.25)
    limiter.acquire()

    assert fake_time.sleep_calls == pytest.approx([0.25])
    assert fake_time.current == pytest.approx(0.5)


def test_token_bucket_caps_refill_at_capacity() -> None:
    fake_time = FakeTime()
    limiter = TokenBucketRateLimiter(
        requests_per_second=10.0,
        capacity=2,
        clock=fake_time.monotonic,
        sleep=fake_time.sleep,
    )

    limiter.acquire()
    limiter.acquire()

    fake_time.advance(10.0)

    limiter.acquire()
    limiter.acquire()

    assert fake_time.sleep_calls == []

    limiter.acquire()

    assert fake_time.sleep_calls == pytest.approx([0.1])


def test_token_bucket_recomputes_after_sleep() -> None:
    fake_time = FakeTime()
    sleep_calls: list[float] = []

    def partial_first_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

        if len(sleep_calls) == 1:
            fake_time.advance(seconds / 2)
        else:
            fake_time.advance(seconds)

    limiter = TokenBucketRateLimiter(
        requests_per_second=2.0,
        capacity=1,
        clock=fake_time.monotonic,
        sleep=partial_first_sleep,
    )

    limiter.acquire()
    limiter.acquire()

    assert sleep_calls == pytest.approx(
        [
            0.5,
            0.25,
        ]
    )


def test_token_bucket_allows_only_one_thread_per_available_token() -> None:
    clock = ThreadSafeFakeClock()

    start_barrier = threading.Barrier(3)
    waiting_event = threading.Event()
    first_completed_event = threading.Event()
    release_waiter = threading.Event()

    completed: Queue[str] = Queue()
    sleep_requests: Queue[float] = Queue()

    def controlled_sleep(seconds: float) -> None:
        sleep_requests.put(seconds)
        waiting_event.set()

        released = release_waiter.wait(timeout=1.0)

        if not released:
            raise RuntimeError("rate limiter test waiter was not released")

        clock.advance(seconds)

    limiter = TokenBucketRateLimiter(
        requests_per_second=1.0,
        capacity=1,
        clock=clock.monotonic,
        sleep=controlled_sleep,
    )

    def worker(name: str) -> None:
        start_barrier.wait(timeout=1.0)

        limiter.acquire()

        completed.put(name)
        first_completed_event.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(worker, "a")
        future_b = executor.submit(worker, "b")

        try:
            start_barrier.wait(timeout=1.0)

            assert waiting_event.wait(timeout=1.0)
            assert first_completed_event.wait(timeout=1.0)

            assert completed.qsize() == 1

            wait_seconds = sleep_requests.get(timeout=1.0)

            assert wait_seconds == pytest.approx(1.0)
        finally:
            release_waiter.set()

        future_a.result(timeout=1.0)
        future_b.result(timeout=1.0)

    assert completed.qsize() == 2


@pytest.mark.parametrize(
    "requests_per_second",
    [
        0.0,
        -1.0,
    ],
)
def test_token_bucket_rejects_non_positive_rate(
    requests_per_second: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="requests_per_second must be greater than 0",
    ):
        TokenBucketRateLimiter(
            requests_per_second=requests_per_second,
            capacity=1,
        )


@pytest.mark.parametrize(
    "capacity",
    [
        0,
        -1,
    ],
)
def test_token_bucket_rejects_non_positive_capacity(
    capacity: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="capacity must be greater than 0",
    ):
        TokenBucketRateLimiter(
            requests_per_second=1.0,
            capacity=capacity,
        )


def test_no_op_rate_limiter_acquires_immediately() -> None:
    limiter = NoOpRateLimiter()

    assert limiter.acquire() is None
