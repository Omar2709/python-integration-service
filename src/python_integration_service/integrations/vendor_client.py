import os
from urllib.parse import urlparse

from python_integration_service.integrations.exceptions import ConfigurationError


class VendorClient:
    def __init__(self, base_url: str, access_token: str, timeout: float = 30.0) -> None:
        if not base_url:
            raise ConfigurationError("base_url is required and cannot be empty")
        if not access_token:
            raise ConfigurationError("access_token is required and cannot be empty")
        if timeout <= 0:
            raise ConfigurationError(f"timeout must be greater than 0, got {timeout}")

        self.base_url: str = base_url
        self.access_token: str = access_token
        self.timeout: float = timeout

    def build_url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        endpoint = path.lstrip("/")
        return f"{base}/{endpoint}"

    @classmethod
    def from_env(cls) -> "VendorClient":
        base_url = os.getenv("VENDOR_BASE_URL")
        if not base_url:
            raise ConfigurationError("Missing environment variable: VENDOR_BASE_URL")

        access_token = os.getenv("VENDOR_ACCESS_TOKEN")
        if not access_token:
            raise ConfigurationError(
                "Missing environment variable: VENDOR_ACCESS_TOKEN"
            )

        raw_timeout = os.getenv("VENDOR_TIMEOUT", "30")
        try:
            timeout = float(raw_timeout)
        except ValueError as err:
            raise ConfigurationError(
                f"Invalid VENDOR_TIMEOUT value '{raw_timeout}'. Must be a valid number."
            ) from err

        return cls(base_url=base_url, access_token=access_token, timeout=timeout)

    @staticmethod
    def is_valid_url(value: object) -> bool:
        if not isinstance(value, str):
            return False
        parsed_url = urlparse(value)
        return parsed_url.scheme in ("http", "https") and bool(parsed_url.netloc)
