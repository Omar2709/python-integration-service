class IntegrationError(Exception):
    """Base exception for all integration errors."""


class ConfigurationError(IntegrationError):
    """Raised when integration configuration is invalid."""


class AuthenticationError(IntegrationError):
    """Raised when authentication with the provider fails."""


class RateLimitError(IntegrationError):
    """Raised when the provider rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class TransientIntegrationError(IntegrationError):
    """Raised for temporary integration failures."""
