import pytest

from python_integration_service.integrations.page_iterator import PageIterator


def test_iterates_over_multiple_pages() -> None:
    pages = [
        [{"id": 1}, {"id": 2}],
        [{"id": 3}],
        [{"id": 4}, {"id": 5}],
    ]

    iterator = PageIterator(pages)

    result = list(iterator)

    assert result == [
        {"id": 1},
        {"id": 2},
        {"id": 3},
        {"id": 4},
        {"id": 5},
    ]


def test_skips_empty_pages() -> None:
    pages = [
        [],
        [{"id": 1}],
        [],
        [{"id": 2}, {"id": 3}],
        [],
    ]

    iterator = PageIterator(pages)

    result = list(iterator)

    assert result == [
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ]


def test_next_raises_stop_iteration_when_exhausted() -> None:
    pages = [
        [{"id": 1}],
    ]

    iterator = PageIterator(pages)

    assert next(iterator) == {"id": 1}

    with pytest.raises(StopIteration):
        next(iterator)


def test_iter_returns_same_iterator() -> None:
    pages = [
        [{"id": 1}],
    ]

    iterator = PageIterator(pages)

    assert iter(iterator) is iterator
