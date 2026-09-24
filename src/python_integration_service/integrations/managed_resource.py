from types import TracebackType
from typing import Literal, Self


class ManagedResource:
    def __init__(self, name: str) -> None:
        self.name = name
        self.is_open = False

    def __enter__(self) -> Self:
        self.is_open = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        self.is_open = False
        return False
