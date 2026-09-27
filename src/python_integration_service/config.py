from typing import Self

from pydantic import (
    AnyHttpUrl,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    vendor_base_url: AnyHttpUrl
    vendor_access_token: SecretStr
    vendor_timeout: float = Field(default=30.0, gt=0)
    vendor_retry_max_attempts: int = Field(default=3, ge=1)
    vendor_retry_base_delay: float = Field(default=0.5, ge=0)
    vendor_retry_max_retry_after_seconds: float = Field(
        default=60.0,
        gt=0,
    )
    vendor_rate_limit_requests_per_second: float | None = Field(
        default=None,
        gt=0,
    )
    vendor_rate_limit_capacity: int | None = Field(
        default=None,
        ge=1,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("vendor_access_token")
    @classmethod
    def validate_vendor_access_token(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("vendor_access_token cannot be empty")

        return value

    @model_validator(mode="after")
    def validate_rate_limit_configuration(self) -> Self:
        rate_configured = self.vendor_rate_limit_requests_per_second is not None
        capacity_configured = self.vendor_rate_limit_capacity is not None

        if rate_configured != capacity_configured:
            raise ValueError(
                "vendor rate limit requests per second and capacity "
                "must be configured together"
            )

        return self


def load_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
