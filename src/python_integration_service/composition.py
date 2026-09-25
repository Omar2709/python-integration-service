from collections.abc import Iterator
from contextlib import contextmanager

from python_integration_service.config import Settings
from python_integration_service.integrations.httpx_transport import HttpxTransport
from python_integration_service.integrations.vendor_client import VendorClient


@contextmanager
def create_vendor_client(settings: Settings) -> Iterator[VendorClient]:
    with HttpxTransport(
        access_token=settings.vendor_access_token.get_secret_value(),
        timeout=settings.vendor_timeout,
    ) as transport:
        yield VendorClient(
            base_url=str(settings.vendor_base_url),
            transport=transport,
        )
