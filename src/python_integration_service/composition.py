from collections.abc import Iterator
from contextlib import contextmanager

from python_integration_service.config import Settings
from python_integration_service.integrations.httpx_transport import HttpxTransport
from python_integration_service.integrations.rate_limit import (
    NoOpRateLimiter,
    RateLimiter,
    TokenBucketRateLimiter,
)
from python_integration_service.integrations.retry import RetryPolicy
from python_integration_service.integrations.vendor_client import VendorClient


def create_rate_limiter(settings: Settings) -> RateLimiter:
    if (
        settings.vendor_rate_limit_requests_per_second is None
        or settings.vendor_rate_limit_capacity is None
    ):
        return NoOpRateLimiter()

    return TokenBucketRateLimiter(
        requests_per_second=settings.vendor_rate_limit_requests_per_second,
        capacity=settings.vendor_rate_limit_capacity,
    )


@contextmanager
def create_vendor_client(settings: Settings) -> Iterator[VendorClient]:
    retry_policy = RetryPolicy(
        max_attempts=settings.vendor_retry_max_attempts,
        base_delay=settings.vendor_retry_base_delay,
        max_retry_after_seconds=settings.vendor_retry_max_retry_after_seconds,
    )

    rate_limiter = create_rate_limiter(settings)

    with HttpxTransport(
        access_token=settings.vendor_access_token.get_secret_value(),
        timeout=settings.vendor_timeout,
    ) as transport:
        yield VendorClient(
            base_url=str(settings.vendor_base_url),
            transport=transport,
            retry_policy=retry_policy,
            rate_limiter=rate_limiter,
        )
