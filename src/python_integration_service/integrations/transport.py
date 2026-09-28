from abc import ABC, abstractmethod
from collections.abc import Mapping


class Transport(ABC):
    @abstractmethod
    def get(self, url: str) -> dict:
        pass

    @abstractmethod
    def post(
        self,
        url: str,
        payload: Mapping[str, object],
        headers: Mapping[str, str] | None = None,
    ) -> dict:
        pass


class FakeTransport(Transport):
    def get(self, url: str) -> dict:
        return {
            "url": url,
            "status": "ok",
        }

    def post(
        self,
        url: str,
        payload: Mapping[str, object],
        headers: Mapping[str, str] | None = None,
    ) -> dict:
        return {
            "url": url,
            "payload": dict(payload),
            "headers": dict(headers or {}),
        }
