from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from python_integration_service.main import app


def test_lifespan_initializes_vendor_client() -> None:
    settings = MagicMock()
    vendor_client = MagicMock()
    vendor_client_context = MagicMock()

    vendor_client_context.__enter__.return_value = vendor_client

    with (
        patch(
            "python_integration_service.main.load_settings",
            return_value=settings,
        ) as load_settings_mock,
        patch(
            "python_integration_service.main.create_vendor_client",
            return_value=vendor_client_context,
        ) as create_vendor_client_mock,
        TestClient(app),
    ):
        assert app.state.vendor_client is vendor_client

    load_settings_mock.assert_called_once_with()
    create_vendor_client_mock.assert_called_once_with(settings)


def test_lifespan_exits_vendor_client_context_on_shutdown() -> None:
    settings = MagicMock()
    vendor_client_context = MagicMock()

    with (
        patch(
            "python_integration_service.main.load_settings",
            return_value=settings,
        ),
        patch(
            "python_integration_service.main.create_vendor_client",
            return_value=vendor_client_context,
        ),
        TestClient(app),
    ):
        pass

    vendor_client_context.__exit__.assert_called_once()


def test_lifespan_fails_when_settings_loading_fails() -> None:
    with (
        patch(
            "python_integration_service.main.load_settings",
            side_effect=RuntimeError("invalid configuration"),
        ),
        patch(
            "python_integration_service.main.create_vendor_client",
        ) as create_vendor_client_mock,
        pytest.raises(
            RuntimeError,
            match="invalid configuration",
        ),
        TestClient(app),
    ):
        pass

    create_vendor_client_mock.assert_not_called()


def test_lifespan_fails_when_vendor_client_creation_fails() -> None:
    settings = MagicMock()

    with (
        patch(
            "python_integration_service.main.load_settings",
            return_value=settings,
        ),
        patch(
            "python_integration_service.main.create_vendor_client",
            side_effect=RuntimeError("vendor client initialization failed"),
        ),
        pytest.raises(
            RuntimeError,
            match="vendor client initialization failed",
        ),
        TestClient(app),
    ):
        pass
