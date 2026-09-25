from python_integration_service.integrations.exceptions import ConfigurationError
from python_integration_service.integrations.transport import Transport


class VendorClient:
    def __init__(
        self,
        base_url: str,
        transport: Transport,
    ) -> None:
        if not base_url:
            raise ConfigurationError("base_url is required and cannot be empty")

        self.base_url = base_url
        self.transport = transport

    def build_url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        endpoint = path.lstrip("/")
        return f"{base}/{endpoint}"

    def get(self, path: str) -> dict:
        url = self.build_url(path)
        return self.transport.get(url)
