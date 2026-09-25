from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    vendor_base_url: AnyHttpUrl
    vendor_access_token: SecretStr
    vendor_timeout: float = Field(default=30.0, gt=0)

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
