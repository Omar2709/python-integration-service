from email.utils import parsedate_to_datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from python_integration_service.api.schemas import ErrorResponse
from python_integration_service.integrations.exceptions import (
    AuthenticationError,
    IntegrationError,
    RateLimitError,
    UpstreamConnectionError,
    UpstreamServerError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)


def _get_valid_retry_after(value: str | None) -> str | None:
    if value is None:
        return None

    candidate = value.strip()

    if not candidate:
        return None

    if candidate.isascii() and candidate.isdigit():
        return candidate

    try:
        parsed_date = parsedate_to_datetime(candidate)
    except (TypeError, ValueError, OverflowError):
        return None

    if parsed_date.tzinfo is None:
        return None

    return candidate


async def authentication_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            code="upstream_authentication_error",
            detail="The upstream service could not authenticate the request.",
        ).model_dump(mode="json"),
    )


async def rate_limit_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    retry_after: str | None = None

    if isinstance(exc, RateLimitError):
        retry_after = _get_valid_retry_after(exc.retry_after)

    headers: dict[str, str] = {}

    if retry_after is not None:
        headers["Retry-After"] = retry_after

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse(
            code="upstream_rate_limited",
            detail="The upstream service is temporarily rate limited.",
        ).model_dump(mode="json"),
        headers=headers,
    )


async def upstream_timeout_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content=ErrorResponse(
            code="upstream_timeout",
            detail="The upstream service did not respond in time.",
        ).model_dump(mode="json"),
    )


async def upstream_connection_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            code="upstream_connection_error",
            detail="The upstream service could not be reached.",
        ).model_dump(mode="json"),
    )


async def upstream_server_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            code="upstream_server_error",
            detail="The upstream service failed to process the request.",
        ).model_dump(mode="json"),
    )


async def upstream_unavailable_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse(
            code="upstream_unavailable",
            detail="The upstream service is temporarily unavailable.",
        ).model_dump(mode="json"),
    )


async def integration_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            code="upstream_integration_error",
            detail="The upstream service could not complete the request.",
        ).model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        AuthenticationError,
        authentication_error_handler,
    )
    app.add_exception_handler(
        RateLimitError,
        rate_limit_error_handler,
    )
    app.add_exception_handler(
        UpstreamTimeoutError,
        upstream_timeout_error_handler,
    )
    app.add_exception_handler(
        UpstreamConnectionError,
        upstream_connection_error_handler,
    )
    app.add_exception_handler(
        UpstreamServerError,
        upstream_server_error_handler,
    )
    app.add_exception_handler(
        UpstreamUnavailableError,
        upstream_unavailable_error_handler,
    )
    app.add_exception_handler(
        IntegrationError,
        integration_error_handler,
    )
