from types import TracebackType
from typing import Literal, Self

import httpx

from python_integration_service.integrations.exceptions import (
    AuthenticationError,
    IntegrationError,
    RateLimitError,
    UpstreamConnectionError,
    UpstreamServerError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from python_integration_service.integrations.transport import Transport


class HttpxTransport(Transport):
    def __init__(
        self,
        access_token: str,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        self.close()
        return False

    def close(self) -> None:
        self._client.close()

    def get(self, url: str) -> dict:
        try:
            response = self._client.get(url)
            response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"Request timed out while calling {url}"
            ) from exc

        except httpx.NetworkError as exc:
            raise UpstreamConnectionError(
                f"Network error while calling external service: {url}"
            ) from exc

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code

            if status_code == 401:
                raise AuthenticationError(
                    "Authentication with the external service failed"
                ) from exc

            if status_code == 429:
                retry_after = exc.response.headers.get("Retry-After")

                raise RateLimitError(
                    "External service rate limit exceeded",
                    retry_after=retry_after,
                ) from exc

            if status_code in (500, 502):
                raise UpstreamServerError(
                    f"External service returned HTTP {status_code}"
                ) from exc

            if status_code == 503:
                raise UpstreamUnavailableError(
                    "External service is temporarily unavailable"
                ) from exc

            if status_code == 504:
                raise UpstreamTimeoutError(
                    "External service reported a gateway timeout"
                ) from exc

            raise IntegrationError(
                f"External service returned HTTP {status_code}"
            ) from exc

        return response.json()
