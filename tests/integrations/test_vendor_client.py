from unittest.mock import MagicMock, call

import pytest
from pydantic import ValidationError

from python_integration_service.integrations.exceptions import (
    InvalidUpstreamResponseError,
)
from python_integration_service.integrations.transport import Transport
from python_integration_service.integrations.vendor_client import VendorClient
from python_integration_service.integrations.vendor_schemas import VendorItem


def test_get_items_page_validates_vendor_response() -> None:
    transport = MagicMock(spec=Transport)
    transport.get.return_value = {
        "items": [
            {
                "id": 1,
                "name": "Item 1",
                "created_at": "2026-09-26T12:00:00Z",
            }
        ],
        "next_page": 2,
        "request_id": "abc123",
    }

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
    )

    page = client.get_items_page(page=1)

    assert page.items == [
        VendorItem(
            id=1,
            name="Item 1",
        )
    ]
    assert page.next_page == 2

    transport.get.assert_called_once_with("https://api.vendor.test/items?page=1")


@pytest.mark.parametrize(
    "payload",
    [
        {
            "items": [
                {
                    "id": "1",
                    "name": "Item 1",
                }
            ],
            "next_page": None,
        },
        {
            "items": [
                {
                    "id": 1,
                    "name": "Item 1",
                }
            ],
            "next_page": "2",
        },
    ],
)
def test_get_items_page_rejects_invalid_field_types(
    payload: dict,
) -> None:
    transport = MagicMock(spec=Transport)
    transport.get.return_value = payload

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
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
    transport = MagicMock(spec=Transport)
    transport.get.return_value = {
        "items": [],
        "next_page": next_page,
    }

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
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
    transport = MagicMock(spec=Transport)

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
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
    transport = MagicMock(spec=Transport)

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
    )

    items = client.iter_items(start_page=start_page)

    with pytest.raises(
        ValueError,
        match="start_page must be greater than 0",
    ):
        next(items)

    transport.get.assert_not_called()


def test_iter_items_fetches_pages_lazily() -> None:
    transport = MagicMock(spec=Transport)
    transport.get.side_effect = [
        {
            "items": [
                {
                    "id": 1,
                    "name": "Item 1",
                }
            ],
            "next_page": 2,
        },
        {
            "items": [
                {
                    "id": 2,
                    "name": "Item 2",
                }
            ],
            "next_page": None,
        },
    ]

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
    )

    items = client.iter_items()

    first_item = next(items)

    assert first_item == VendorItem(
        id=1,
        name="Item 1",
    )

    transport.get.assert_called_once_with("https://api.vendor.test/items?page=1")

    second_item = next(items)

    assert second_item == VendorItem(
        id=2,
        name="Item 2",
    )

    assert transport.get.call_args_list == [
        call("https://api.vendor.test/items?page=1"),
        call("https://api.vendor.test/items?page=2"),
    ]

    with pytest.raises(StopIteration):
        next(items)


def test_iter_items_rejects_cyclic_pagination() -> None:
    transport = MagicMock(spec=Transport)
    transport.get.side_effect = [
        {
            "items": [
                {
                    "id": 1,
                    "name": "Item 1",
                }
            ],
            "next_page": 2,
        },
        {
            "items": [
                {
                    "id": 2,
                    "name": "Item 2",
                }
            ],
            "next_page": 1,
        },
    ]

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
    )

    items = client.iter_items()

    assert next(items) == VendorItem(
        id=1,
        name="Item 1",
    )

    with pytest.raises(InvalidUpstreamResponseError):
        next(items)

    assert transport.get.call_args_list == [
        call("https://api.vendor.test/items?page=1"),
        call("https://api.vendor.test/items?page=2"),
    ]


def test_iter_items_skips_empty_pages_and_continues() -> None:
    transport = MagicMock(spec=Transport)
    transport.get.side_effect = [
        {
            "items": [],
            "next_page": 2,
        },
        {
            "items": [
                {
                    "id": 2,
                    "name": "Item 2",
                }
            ],
            "next_page": None,
        },
    ]

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
    )

    items = list(client.iter_items())

    assert items == [
        VendorItem(
            id=2,
            name="Item 2",
        )
    ]

    assert transport.get.call_args_list == [
        call("https://api.vendor.test/items?page=1"),
        call("https://api.vendor.test/items?page=2"),
    ]


def test_iter_items_stops_on_empty_final_page() -> None:
    transport = MagicMock(spec=Transport)
    transport.get.return_value = {
        "items": [],
        "next_page": None,
    }

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
    )

    items = list(client.iter_items())

    assert items == []

    transport.get.assert_called_once_with("https://api.vendor.test/items?page=1")


def test_iter_items_allows_non_monotonic_unvisited_pages() -> None:
    transport = MagicMock(spec=Transport)
    transport.get.side_effect = [
        {
            "items": [
                {
                    "id": 1,
                    "name": "Item 1",
                }
            ],
            "next_page": 3,
        },
        {
            "items": [
                {
                    "id": 2,
                    "name": "Item 2",
                }
            ],
            "next_page": 2,
        },
        {
            "items": [
                {
                    "id": 3,
                    "name": "Item 3",
                }
            ],
            "next_page": None,
        },
    ]

    client = VendorClient(
        base_url="https://api.vendor.test",
        transport=transport,
    )

    items = list(client.iter_items(start_page=1))

    assert items == [
        VendorItem(
            id=1,
            name="Item 1",
        ),
        VendorItem(
            id=2,
            name="Item 2",
        ),
        VendorItem(
            id=3,
            name="Item 3",
        ),
    ]

    assert transport.get.call_args_list == [
        call("https://api.vendor.test/items?page=1"),
        call("https://api.vendor.test/items?page=3"),
        call("https://api.vendor.test/items?page=2"),
    ]
