import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
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


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_retry_after_seconds(
    value: str | None,
    now: Callable[[], datetime],
) -> float | None:
    if value is None:
        return None

    candidate = value.strip()

    if not candidate:
        return None

    if candidate.isascii() and candidate.isdigit():
        return float(candidate)

    try:
        retry_at = parsedate_to_datetime(candidate)
    except (TypeError, ValueError, OverflowError):
        return None

    if retry_at.tzinfo is None:
        return None

    current_time = now()

    if current_time.tzinfo is None:
        raise ValueError("now must return a timezone-aware datetime")

    return max(
        0.0,
        (retry_at - current_time).total_seconds(),
    )


class HttpxTransport(Transport):
    def __init__(
        self,
        access_token: str,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._now = now
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
        return self._request(
            method="GET",
            url=url,
        )

    def post(
        self,
        url: str,
        payload: Mapping[str, object],
        headers: Mapping[str, str] | None = None,
    ) -> dict:
        try:
            json.dumps(payload)
        except TypeError as exc:
            raise ValueError("Request payload must be JSON serializable") from exc

        return self._request(
            method="POST",
            url=url,
            json_payload=payload,
            headers=headers,
        )

    def _request(
        self,
        method: Literal["GET", "POST"],
        url: str,
        *,
        json_payload: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict:
        try:
            response = self._client.request(
                method,
                url,
                json=json_payload,
                headers=headers,
            )
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
                retry_after_seconds = _parse_retry_after_seconds(
                    exc.response.headers.get("Retry-After"),
                    self._now,
                )

                raise RateLimitError(
                    "External service rate limit exceeded",
                    retry_after_seconds=retry_after_seconds,
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
