from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class Resource:
    name: str
    is_open: bool = False


@contextmanager
def managed_resource(name: str) -> Generator[Resource]:
    resource = Resource(
        name=name,
        is_open=True,
    )

    try:
        yield resource
    finally:
        resource.is_open = False
