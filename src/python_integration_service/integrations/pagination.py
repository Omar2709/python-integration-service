from collections.abc import Iterator


def iter_items(pages: list[list[dict]]) -> Iterator[dict]:
    for page in pages:
        yield from page
