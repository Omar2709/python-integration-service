import pytest
from pydantic import ValidationError

from python_integration_service.config import Settings


def load_settings_from_env() -> Settings:
    return Settings(_env_file=None)  # pyright: ignore[reportCallIssue]


@pytest.fixture
def valid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VENDOR_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("VENDOR_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("VENDOR_TIMEOUT", "15")


def test_loads_valid_settings(valid_env: None) -> None:
    settings = load_settings_from_env()

    assert str(settings.vendor_base_url) == "https://api.example.com/"
    assert settings.vendor_access_token.get_secret_value() == "test-token"
    assert settings.vendor_timeout == 15.0


def test_uses_default_timeout_when_env_variable_is_missing(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VENDOR_TIMEOUT", raising=False)

    settings = load_settings_from_env()

    assert settings.vendor_timeout == 30.0


def test_invalid_base_url_raises_validation_error(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VENDOR_BASE_URL", "not-a-url")

    with pytest.raises(ValidationError):
        load_settings_from_env()


@pytest.mark.parametrize("timeout", ["0", "-1"])
def test_non_positive_timeout_raises_validation_error(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
    timeout: str,
) -> None:
    monkeypatch.setenv("VENDOR_TIMEOUT", timeout)

    with pytest.raises(ValidationError):
        load_settings_from_env()


@pytest.mark.parametrize("access_token", ["", "   "])
def test_blank_access_token_raises_validation_error(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
    access_token: str,
) -> None:
    monkeypatch.setenv("VENDOR_ACCESS_TOKEN", access_token)

    with pytest.raises(ValidationError):
        load_settings_from_env()


def test_secret_value_is_preserved(valid_env: None) -> None:
    settings = load_settings_from_env()

    assert settings.vendor_access_token.get_secret_value() == "test-token"
