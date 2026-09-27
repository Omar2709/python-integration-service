class IntegrationError(Exception):
    """Base exception for all integration errors."""


class ConfigurationError(IntegrationError):
    """Raised when integration configuration is invalid."""


class AuthenticationError(IntegrationError):
    """Raised when authentication with the provider fails."""


class InvalidUpstreamResponseError(IntegrationError):
    """Raised when the upstream service returns an invalid response payload."""


class InvalidVendorDataError(InvalidUpstreamResponseError):
    """Raised when structurally valid vendor data violates application semantics."""


class MappingError(IntegrationError):
    """Base exception for failures adapting upstream data."""


class UnsupportedVendorCategoryError(MappingError):
    """Raised when a vendor category cannot be mapped to the public contract."""


class TransientIntegrationError(IntegrationError):
    """Base exception for temporary integration failures."""


class RateLimitError(TransientIntegrationError):
    """Raised when the provider rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class UpstreamTimeoutError(TransientIntegrationError):
    """Raised when an upstream operation times out."""


class UpstreamConnectionError(TransientIntegrationError):
    """Raised when the upstream service cannot be reached reliably."""


class UpstreamServerError(TransientIntegrationError):
    """Raised when the upstream service reports an internal server failure."""


class UpstreamUnavailableError(TransientIntegrationError):
    """Raised when the upstream service is temporarily unavailable."""
