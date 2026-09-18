class IntegrationError(Exception):
    """Base exception for all integration errors."""


class ConfigurationError(IntegrationError):
    """Raised when integration configuration is invalid."""


class AuthenticationError(IntegrationError):
    """Raised when authentication with the provider fails."""


class RateLimitError(IntegrationError):
    """Raised when the provider rate limit is exceeded."""


class TransientIntegrationError(IntegrationError):
    """Raised for temporary integration failures."""
