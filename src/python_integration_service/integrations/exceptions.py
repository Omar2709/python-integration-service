class IntegrationError(Exception):
    """Base exception for all integration errors."""


class ConfigurationError(IntegrationError):
    """Raised when integration configuration is invalid."""


class AuthenticationError(IntegrationError):
    """Raised when authentication with the provider fails."""


class InvalidUpstreamResponseError(IntegrationError):
    """Raised when the upstream service returns an invalid response payload."""


class TransientIntegrationError(IntegrationError):
    """Base exception for temporary integration failures."""


class RateLimitError(TransientIntegrationError):
    """Raised when the provider rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class UpstreamTimeoutError(TransientIntegrationError):
    """Raised when an upstream operation times out."""


class UpstreamConnectionError(TransientIntegrationError):
    """Raised when the upstream service cannot be reached reliably."""


class UpstreamServerError(TransientIntegrationError):
    """Raised when the upstream service reports an internal server failure."""


class UpstreamUnavailableError(TransientIntegrationError):
    """Raised when the upstream service is temporarily unavailable."""
