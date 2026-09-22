from python_integration_service.integrations.pagination import iter_items


def test_iter_items_multiple_pages() -> None:
    pages = [
        [{"id": 1}, {"id": 2}],
        [{"id": 3}],
        [{"id": 4}, {"id": 5}],
    ]

    result = list(iter_items(pages))

    assert result == [
        {"id": 1},
        {"id": 2},
        {"id": 3},
        {"id": 4},
        {"id": 5},
    ]


def test_iter_items_skips_empty_pages() -> None:
    pages = [
        [{"id": 1}],
        [],
        [{"id": 2}, {"id": 3}],
        [],
    ]

    result = list(iter_items(pages))

    assert result == [
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ]


def test_iter_items_with_empty_pages_list() -> None:
    pages: list[list[dict]] = []

    result = list(iter_items(pages))

    assert result == []
