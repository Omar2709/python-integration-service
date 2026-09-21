from abc import ABC, abstractmethod


class Transport(ABC):
    @abstractmethod
    def get(self, url: str) -> dict:
        pass


class FakeTransport(Transport):
    def get(self, url: str) -> dict:
        return {
            "url": url,
            "status": "ok",
        }
