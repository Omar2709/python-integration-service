from unittest.mock import MagicMock, patch

import pytest
from pydantic import AnyHttpUrl, SecretStr

from python_integration_service.composition import create_vendor_client
from python_integration_service.config import Settings


def make_settings() -> Settings:
    return Settings(
        vendor_base_url=AnyHttpUrl("https://api.example.com"),
        vendor_access_token=SecretStr("test-token"),
        vendor_timeout=15.0,
    )


def test_create_vendor_client_wires_dependencies() -> None:
    settings = make_settings()
    transport = MagicMock()

    with patch(
        "python_integration_service.composition.HttpxTransport"
    ) as transport_class:
        transport_class.return_value.__enter__.return_value = transport

        with create_vendor_client(settings) as client:
            transport_class.assert_called_once_with(
                access_token="test-token",
                timeout=15.0,
            )

            assert client.base_url == "https://api.example.com/"
            assert client.transport is transport


def test_create_vendor_client_exits_transport_context() -> None:
    settings = make_settings()

    with patch(
        "python_integration_service.composition.HttpxTransport"
    ) as transport_class:
        with create_vendor_client(settings):
            pass

        transport_class.return_value.__exit__.assert_called_once()


def test_create_vendor_client_exits_transport_context_on_exception() -> None:
    settings = make_settings()

    with patch(
        "python_integration_service.composition.HttpxTransport"
    ) as transport_class:
        with (
            pytest.raises(RuntimeError, match="boom"),
            create_vendor_client(settings),
        ):
            raise RuntimeError("boom")

        transport_class.return_value.__exit__.assert_called_once()
