from collections.abc import Iterator

from pydantic import ValidationError

from python_integration_service.integrations.exceptions import (
    ConfigurationError,
    InvalidUpstreamResponseError,
)
from python_integration_service.integrations.rate_limit import RateLimiter
from python_integration_service.integrations.retry import RetryPolicy
from python_integration_service.integrations.transport import Transport
from python_integration_service.integrations.vendor_schemas import (
    ItemsPage,
    VendorItem,
)


class VendorClient:
    def __init__(
        self,
        base_url: str,
        transport: Transport,
        retry_policy: RetryPolicy,
        rate_limiter: RateLimiter,
    ) -> None:
        if not base_url:
            raise ConfigurationError("base_url is required and cannot be empty")

        self.base_url = base_url
        self.transport = transport
        self.retry_policy = retry_policy
        self.rate_limiter = rate_limiter

    def build_url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        endpoint = path.lstrip("/")
        return f"{base}/{endpoint}"

    def get(self, path: str) -> dict:
        url = self.build_url(path)

        def operation() -> dict:
            self.rate_limiter.acquire()
            return self.transport.get(url)

        return self.retry_policy.execute(operation)

    def get_items_page(self, page: int) -> ItemsPage:
        if page < 1:
            raise ValueError("page must be greater than 0")

        payload = self.get(f"/items?page={page}")

        try:
            return ItemsPage.model_validate(payload)
        except ValidationError as exc:
            raise InvalidUpstreamResponseError(
                "Vendor returned an invalid items page"
            ) from exc

    def iter_items(
        self,
        start_page: int = 1,
    ) -> Iterator[VendorItem]:
        if start_page < 1:
            raise ValueError("start_page must be greater than 0")

        page: int | None = start_page
        visited_pages: set[int] = set()

        while page is not None:
            if page in visited_pages:
                raise InvalidUpstreamResponseError("Vendor pagination contains a cycle")

            visited_pages.add(page)

            items_page = self.get_items_page(page=page)
            next_page = items_page.next_page

            if next_page is not None and next_page in visited_pages:
                raise InvalidUpstreamResponseError("Vendor pagination contains a cycle")

            yield from items_page.items

            page = next_page
