from collections.abc import Callable, Iterator, Mapping
from copy import deepcopy
from unicodedata import category
from uuid import uuid4

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


def _generate_idempotency_key() -> str:
    return str(uuid4())


class VendorClient:
    def __init__(
        self,
        base_url: str,
        transport: Transport,
        retry_policy: RetryPolicy,
        rate_limiter: RateLimiter,
        idempotency_key_factory: Callable[[], str] = _generate_idempotency_key,
    ) -> None:
        if not base_url:
            raise ConfigurationError("base_url is required and cannot be empty")

        self.base_url = base_url
        self.transport = transport
        self.retry_policy = retry_policy
        self.rate_limiter = rate_limiter
        self._idempotency_key_factory = idempotency_key_factory

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

    def post(
        self,
        path: str,
        payload: Mapping[str, object],
        idempotency_key: str | None = None,
    ) -> dict:
        resolved_key = self._resolve_idempotency_key(idempotency_key)
        payload_snapshot = self._snapshot_payload(payload)
        url = self.build_url(path)

        self.rate_limiter.acquire()

        return self.transport.post(
            url,
            payload_snapshot,
            headers={
                "Idempotency-Key": resolved_key,
            },
        )

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

    def _resolve_idempotency_key(
        self,
        idempotency_key: str | None,
    ) -> str:
        candidate: object

        if idempotency_key is None:
            candidate = self._idempotency_key_factory()
        else:
            candidate = idempotency_key

        return self._validate_idempotency_key(candidate)

    @staticmethod
    def _validate_idempotency_key(value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("idempotency_key must be a string")

        if not value.strip():
            raise ValueError(
                "idempotency_key must be a non-empty string without control characters"
            )

        if any(category(character) == "Cc" for character in value):
            raise ValueError(
                "idempotency_key must be a non-empty string without control characters"
            )

        return value

    @staticmethod
    def _snapshot_payload(
        payload: Mapping[str, object],
    ) -> dict[str, object]:
        try:
            return deepcopy(dict(payload))
        except Exception as exc:
            raise ValueError("Request payload could not be safely copied") from exc
