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
    monkeypatch.setenv("VENDOR_RETRY_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("VENDOR_RETRY_BASE_DELAY", "0.75")
    monkeypatch.setenv(
        "VENDOR_RETRY_MAX_RETRY_AFTER_SECONDS",
        "120",
    )
    monkeypatch.delenv(
        "VENDOR_RETRY_BUDGET_SECONDS",
        raising=False,
    )
    monkeypatch.delenv(
        "VENDOR_RATE_LIMIT_REQUESTS_PER_SECOND",
        raising=False,
    )
    monkeypatch.delenv(
        "VENDOR_RATE_LIMIT_CAPACITY",
        raising=False,
    )


def test_loads_valid_settings(valid_env: None) -> None:
    settings = load_settings_from_env()

    assert str(settings.vendor_base_url) == "https://api.example.com/"
    assert settings.vendor_access_token.get_secret_value() == "test-token"
    assert settings.vendor_timeout == 15.0
    assert settings.vendor_retry_max_attempts == 4
    assert settings.vendor_retry_base_delay == 0.75
    assert settings.vendor_retry_max_retry_after_seconds == 120.0


def test_uses_default_timeout_when_env_variable_is_missing(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VENDOR_TIMEOUT", raising=False)

    settings = load_settings_from_env()

    assert settings.vendor_timeout == 30.0


def test_uses_default_retry_settings(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "VENDOR_RETRY_MAX_ATTEMPTS",
        raising=False,
    )
    monkeypatch.delenv(
        "VENDOR_RETRY_BASE_DELAY",
        raising=False,
    )
    monkeypatch.delenv(
        "VENDOR_RETRY_MAX_RETRY_AFTER_SECONDS",
        raising=False,
    )

    settings = load_settings_from_env()

    assert settings.vendor_retry_max_attempts == 3
    assert settings.vendor_retry_base_delay == 0.5
    assert settings.vendor_retry_max_retry_after_seconds == 60.0


def test_retry_budget_is_disabled_by_default(
    valid_env: None,
) -> None:
    settings = load_settings_from_env()

    assert settings.vendor_retry_budget_seconds is None


def test_loads_retry_budget_configuration(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "VENDOR_RETRY_BUDGET_SECONDS",
        "12.5",
    )

    settings = load_settings_from_env()

    assert settings.vendor_retry_budget_seconds == 12.5


@pytest.mark.parametrize(
    "retry_budget_seconds",
    [
        pytest.param("0", id="zero"),
        pytest.param("-1", id="negative"),
    ],
)
def test_rejects_non_positive_retry_budget(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
    retry_budget_seconds: str,
) -> None:
    monkeypatch.setenv(
        "VENDOR_RETRY_BUDGET_SECONDS",
        retry_budget_seconds,
    )

    with pytest.raises(ValidationError):
        load_settings_from_env()


def test_rate_limiting_is_disabled_by_default(
    valid_env: None,
) -> None:
    settings = load_settings_from_env()

    assert settings.vendor_rate_limit_requests_per_second is None
    assert settings.vendor_rate_limit_capacity is None


def test_loads_rate_limit_configuration(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "VENDOR_RATE_LIMIT_REQUESTS_PER_SECOND",
        "2.5",
    )
    monkeypatch.setenv(
        "VENDOR_RATE_LIMIT_CAPACITY",
        "10",
    )

    settings = load_settings_from_env()

    assert settings.vendor_rate_limit_requests_per_second == 2.5
    assert settings.vendor_rate_limit_capacity == 10


@pytest.mark.parametrize(
    ("variable_name", "value"),
    [
        pytest.param(
            "VENDOR_RATE_LIMIT_REQUESTS_PER_SECOND",
            "2.5",
            id="missing-capacity",
        ),
        pytest.param(
            "VENDOR_RATE_LIMIT_CAPACITY",
            "10",
            id="missing-rate",
        ),
    ],
)
def test_rejects_partial_rate_limit_configuration(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
    variable_name: str,
    value: str,
) -> None:
    monkeypatch.setenv(variable_name, value)

    with pytest.raises(
        ValidationError,
        match="must be configured together",
    ):
        load_settings_from_env()


@pytest.mark.parametrize(
    "rate",
    [
        pytest.param("0", id="zero"),
        pytest.param("-1", id="negative"),
    ],
)
def test_rejects_non_positive_rate_limit_rate(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
    rate: str,
) -> None:
    monkeypatch.setenv(
        "VENDOR_RATE_LIMIT_REQUESTS_PER_SECOND",
        rate,
    )
    monkeypatch.setenv(
        "VENDOR_RATE_LIMIT_CAPACITY",
        "1",
    )

    with pytest.raises(ValidationError):
        load_settings_from_env()


@pytest.mark.parametrize(
    "capacity",
    [
        pytest.param("0", id="zero"),
        pytest.param("-1", id="negative"),
    ],
)
def test_rejects_non_positive_rate_limit_capacity(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
    capacity: str,
) -> None:
    monkeypatch.setenv(
        "VENDOR_RATE_LIMIT_REQUESTS_PER_SECOND",
        "1.0",
    )
    monkeypatch.setenv(
        "VENDOR_RATE_LIMIT_CAPACITY",
        capacity,
    )

    with pytest.raises(ValidationError):
        load_settings_from_env()


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


@pytest.mark.parametrize(
    "max_attempts",
    [
        "0",
        "-1",
    ],
)
def test_invalid_retry_max_attempts_raises_validation_error(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
    max_attempts: str,
) -> None:
    monkeypatch.setenv(
        "VENDOR_RETRY_MAX_ATTEMPTS",
        max_attempts,
    )

    with pytest.raises(ValidationError):
        load_settings_from_env()


def test_negative_retry_base_delay_raises_validation_error(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "VENDOR_RETRY_BASE_DELAY",
        "-0.5",
    )

    with pytest.raises(ValidationError):
        load_settings_from_env()


@pytest.mark.parametrize(
    "max_retry_after_seconds",
    [
        "0",
        "-1",
    ],
)
def test_invalid_retry_max_retry_after_raises_validation_error(
    valid_env: None,
    monkeypatch: pytest.MonkeyPatch,
    max_retry_after_seconds: str,
) -> None:
    monkeypatch.setenv(
        "VENDOR_RETRY_MAX_RETRY_AFTER_SECONDS",
        max_retry_after_seconds,
    )

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
