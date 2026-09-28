from unittest.mock import (
    MagicMock,
    NonCallableMagicMock,
    call,
    create_autospec,
)

import pytest
from pydantic import ValidationError

from python_integration_service.integrations.exceptions import (
    InvalidUpstreamResponseError,
    RetryBudgetExceededError,
    UpstreamTimeoutError,
)
from python_integration_service.integrations.rate_limit import RateLimiter
from python_integration_service.integrations.retry import RetryPolicy
from python_integration_service.integrations.transport import Transport
from python_integration_service.integrations.vendor_client import VendorClient
from python_integration_service.integrations.vendor_schemas import (
    VendorCategory,
    VendorItem,
    VendorItemAttributes,
    VendorStatus,
)
from tests.factories.vendor import (
    make_items_page_payload,
    make_vendor_item_payload,
)


def make_transport() -> NonCallableMagicMock:
    return create_autospec(
        Transport,
        instance=True,
        spec_set=True,
    )


def make_retry_policy() -> NonCallableMagicMock:
    retry_policy = create_autospec(
        RetryPolicy,
        instance=True,
        spec_set=True,
    )
    retry_policy.execute.side_effect = lambda operation: operation()

    return retry_policy


def make_rate_limiter() -> NonCallableMagicMock:
    return create_autospec(
        RateLimiter,
        instance=True,
        spec_set=True,
    )


def test_get_executes_transport_through_retry_policy() -> None:
    transport = make_transport()
    transport.get.return_value = {
        "id": 1,
    }

    retry_policy = make_retry_policy()
    rate_limiter = make_rate_limiter()

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=retry_policy,
        rate_limiter=rate_limiter,
    )

    result = client.get("/items")

    assert result == {
        "id": 1,
    }

    retry_policy.execute.assert_called_once()
    rate_limiter.acquire.assert_called_once_with()
    transport.get.assert_called_once_with("https://api.vendor.test/items")


def test_get_retries_transient_failure_and_then_succeeds() -> None:
    transport = make_transport()
    transport.get.side_effect = [
        UpstreamTimeoutError("temporary timeout"),
        make_items_page_payload(),
    ]

    sleep = MagicMock()
    jitter = MagicMock(return_value=0.25)

    retry_policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
    )

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=retry_policy,
        rate_limiter=make_rate_limiter(),
    )

    page = client.get_items_page(page=1)

    assert page.items == []
    assert page.next_page is None

    assert transport.get.call_count == 2

    jitter.assert_called_once_with(
        0.0,
        1.0,
    )
    sleep.assert_called_once_with(0.25)


def test_retry_attempts_acquire_rate_limit_capacity_independently() -> None:
    transport = make_transport()
    transport.get.side_effect = [
        UpstreamTimeoutError("temporary timeout"),
        make_items_page_payload(),
    ]

    rate_limiter = make_rate_limiter()

    retry_policy = RetryPolicy(
        max_attempts=2,
        base_delay=0.0,
        max_retry_after_seconds=60.0,
        sleep=MagicMock(),
        jitter=MagicMock(return_value=0.0),
    )

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=retry_policy,
        rate_limiter=rate_limiter,
    )

    client.get_items_page(page=1)

    assert rate_limiter.acquire.call_count == 2
    assert transport.get.call_count == 2


def test_vendor_client_does_not_start_retry_after_budget_is_exhausted() -> None:
    transport = make_transport()
    transport.get.side_effect = UpstreamTimeoutError("temporary timeout")

    rate_limiter = make_rate_limiter()

    clock = MagicMock(
        side_effect=[
            100.0,
            101.5,
        ]
    )

    retry_policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        retry_budget_seconds=2.0,
        sleep=MagicMock(),
        jitter=MagicMock(return_value=1.0),
        clock=clock,
    )

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=retry_policy,
        rate_limiter=rate_limiter,
    )

    with pytest.raises(RetryBudgetExceededError) as exc_info:
        client.get("/items")

    assert isinstance(
        exc_info.value.__cause__,
        UpstreamTimeoutError,
    )

    rate_limiter.acquire.assert_called_once_with()
    transport.get.assert_called_once_with("https://api.vendor.test/items")


def test_invalid_upstream_payload_is_not_retried() -> None:
    transport = make_transport()
    transport.get.return_value = make_items_page_payload(
        items=[
            make_vendor_item_payload(
                item_id="not-an-integer",
                display_name="Broken item",
            )
        ]
    )

    sleep = MagicMock()
    jitter = MagicMock()

    retry_policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
    )

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=retry_policy,
        rate_limiter=make_rate_limiter(),
    )

    with pytest.raises(InvalidUpstreamResponseError):
        client.get_items_page(page=1)

    transport.get.assert_called_once_with("https://api.vendor.test/items?page=1")

    sleep.assert_not_called()
    jitter.assert_not_called()


def test_get_items_page_validates_vendor_response() -> None:
    transport = make_transport()

    item_payload = make_vendor_item_payload()

    item_payload["created_at"] = "2026-09-26T12:00:00Z"

    payload = make_items_page_payload(
        items=[item_payload],
        next_page=2,
    )
    payload["request_id"] = "abc123"

    transport.get.return_value = payload

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    page = client.get_items_page(page=1)

    assert page.items == [
        VendorItem(
            id=1,
            attributes=VendorItemAttributes(
                display_name="Item 1",
                category=VendorCategory.HARDWARE,
            ),
            status=VendorStatus.ENABLED,
        )
    ]
    assert page.next_page == 2

    transport.get.assert_called_once_with("https://api.vendor.test/items?page=1")


@pytest.mark.parametrize(
    "payload",
    [
        make_items_page_payload(
            items=[
                make_vendor_item_payload(
                    item_id="1",
                )
            ]
        ),
        make_items_page_payload(
            items=[make_vendor_item_payload()],
            next_page="2",
        ),
    ],
)
def test_get_items_page_rejects_invalid_field_types(
    payload: dict[str, object],
) -> None:
    transport = make_transport()
    transport.get.return_value = payload

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    with pytest.raises(InvalidUpstreamResponseError) as exc_info:
        client.get_items_page(page=1)

    assert isinstance(
        exc_info.value.__cause__,
        ValidationError,
    )


@pytest.mark.parametrize(
    "item_payload",
    [
        make_vendor_item_payload(
            status="archived",
        ),
        make_vendor_item_payload(
            category="unknown",
        ),
        {
            "id": 1,
            "status": "enabled",
        },
    ],
)
def test_get_items_page_rejects_invalid_upstream_item_contract(
    item_payload: dict[str, object],
) -> None:
    transport = make_transport()
    transport.get.return_value = make_items_page_payload(
        items=[item_payload],
    )

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    with pytest.raises(InvalidUpstreamResponseError) as exc_info:
        client.get_items_page(page=1)

    assert isinstance(
        exc_info.value.__cause__,
        ValidationError,
    )


@pytest.mark.parametrize(
    "next_page",
    [
        0,
        -1,
        -10,
    ],
)
def test_get_items_page_rejects_non_positive_next_page(
    next_page: int,
) -> None:
    transport = make_transport()
    transport.get.return_value = make_items_page_payload(
        next_page=next_page,
    )

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    with pytest.raises(InvalidUpstreamResponseError) as exc_info:
        client.get_items_page(page=1)

    assert isinstance(
        exc_info.value.__cause__,
        ValidationError,
    )


@pytest.mark.parametrize(
    "page",
    [
        0,
        -1,
    ],
)
def test_get_items_page_rejects_invalid_page_argument(
    page: int,
) -> None:
    transport = make_transport()

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    with pytest.raises(
        ValueError,
        match="page must be greater than 0",
    ):
        client.get_items_page(page=page)

    transport.get.assert_not_called()


@pytest.mark.parametrize(
    "start_page",
    [
        0,
        -1,
    ],
)
def test_iter_items_rejects_invalid_start_page(
    start_page: int,
) -> None:
    transport = make_transport()

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    items = client.iter_items(start_page=start_page)

    with pytest.raises(
        ValueError,
        match="start_page must be greater than 0",
    ):
        next(items)

    transport.get.assert_not_called()


def test_iter_items_fetches_pages_lazily() -> None:
    transport = make_transport()
    transport.get.side_effect = [
        make_items_page_payload(
            items=[
                make_vendor_item_payload(
                    item_id=1,
                    display_name="Item 1",
                    category="hardware",
                )
            ],
            next_page=2,
        ),
        make_items_page_payload(
            items=[
                make_vendor_item_payload(
                    item_id=2,
                    display_name="Item 2",
                    category="software",
                    status="disabled",
                )
            ],
        ),
    ]

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    items = client.iter_items()

    first_item = next(items)

    assert first_item == VendorItem(
        id=1,
        attributes=VendorItemAttributes(
            display_name="Item 1",
            category=VendorCategory.HARDWARE,
        ),
        status=VendorStatus.ENABLED,
    )

    transport.get.assert_called_once_with("https://api.vendor.test/items?page=1")

    second_item = next(items)

    assert second_item == VendorItem(
        id=2,
        attributes=VendorItemAttributes(
            display_name="Item 2",
            category=VendorCategory.SOFTWARE,
        ),
        status=VendorStatus.DISABLED,
    )

    assert transport.get.call_args_list == [
        call("https://api.vendor.test/items?page=1"),
        call("https://api.vendor.test/items?page=2"),
    ]

    with pytest.raises(StopIteration):
        next(items)


def test_iter_items_rejects_cyclic_pagination() -> None:
    transport = make_transport()
    transport.get.side_effect = [
        make_items_page_payload(
            items=[
                make_vendor_item_payload(
                    item_id=1,
                    display_name="Item 1",
                )
            ],
            next_page=2,
        ),
        make_items_page_payload(
            items=[
                make_vendor_item_payload(
                    item_id=2,
                    display_name="Item 2",
                )
            ],
            next_page=1,
        ),
    ]

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    items = client.iter_items()

    assert next(items) == VendorItem(
        id=1,
        attributes=VendorItemAttributes(
            display_name="Item 1",
            category=VendorCategory.HARDWARE,
        ),
        status=VendorStatus.ENABLED,
    )

    with pytest.raises(InvalidUpstreamResponseError):
        next(items)

    assert transport.get.call_args_list == [
        call("https://api.vendor.test/items?page=1"),
        call("https://api.vendor.test/items?page=2"),
    ]


def test_iter_items_skips_empty_pages_and_continues() -> None:
    transport = make_transport()
    transport.get.side_effect = [
        make_items_page_payload(
            next_page=2,
        ),
        make_items_page_payload(
            items=[
                make_vendor_item_payload(
                    item_id=2,
                    display_name="Item 2",
                    category="accessory",
                )
            ],
        ),
    ]

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    items = list(client.iter_items())

    assert items == [
        VendorItem(
            id=2,
            attributes=VendorItemAttributes(
                display_name="Item 2",
                category=VendorCategory.ACCESSORY,
            ),
            status=VendorStatus.ENABLED,
        )
    ]

    assert transport.get.call_args_list == [
        call("https://api.vendor.test/items?page=1"),
        call("https://api.vendor.test/items?page=2"),
    ]


def test_iter_items_stops_on_empty_final_page() -> None:
    transport = make_transport()
    transport.get.return_value = make_items_page_payload()

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    items = list(client.iter_items())

    assert items == []

    transport.get.assert_called_once_with("https://api.vendor.test/items?page=1")


def test_iter_items_allows_non_monotonic_unvisited_pages() -> None:
    transport = make_transport()
    transport.get.side_effect = [
        make_items_page_payload(
            items=[
                make_vendor_item_payload(
                    item_id=1,
                    display_name="Item 1",
                    category="hardware",
                )
            ],
            next_page=3,
        ),
        make_items_page_payload(
            items=[
                make_vendor_item_payload(
                    item_id=2,
                    display_name="Item 2",
                    category="software",
                )
            ],
            next_page=2,
        ),
        make_items_page_payload(
            items=[
                make_vendor_item_payload(
                    item_id=3,
                    display_name="Item 3",
                    category="accessory",
                    status="disabled",
                )
            ],
        ),
    ]

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
        retry_policy=make_retry_policy(),
        rate_limiter=make_rate_limiter(),
    )

    items = list(client.iter_items(start_page=1))

    assert items == [
        VendorItem(
            id=1,
            attributes=VendorItemAttributes(
                display_name="Item 1",
                category=VendorCategory.HARDWARE,
            ),
            status=VendorStatus.ENABLED,
        ),
        VendorItem(
            id=2,
            attributes=VendorItemAttributes(
                display_name="Item 2",
                category=VendorCategory.SOFTWARE,
            ),
            status=VendorStatus.ENABLED,
        ),
        VendorItem(
            id=3,
            attributes=VendorItemAttributes(
                display_name="Item 3",
                category=VendorCategory.ACCESSORY,
            ),
            status=VendorStatus.DISABLED,
        ),
    ]

    assert transport.get.call_args_list == [
        call("https://api.vendor.test/items?page=1"),
        call("https://api.vendor.test/items?page=3"),
        call("https://api.vendor.test/items?page=2"),
    ]
