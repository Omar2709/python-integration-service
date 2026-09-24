import pytest

from python_integration_service.integrations.resource_context import managed_resource


def test_resource_is_open_inside_with() -> None:
    with managed_resource("vendor-session") as resource:
        assert resource.is_open is True
        assert resource.name == "vendor-session"


def test_resource_is_closed_after_normal_exit() -> None:
    with managed_resource("vendor-session") as resource:
        assert resource.is_open is True

    assert resource.is_open is False


def test_resource_is_closed_when_exception_occurs() -> None:
    resource = None

    with pytest.raises(RuntimeError), managed_resource("vendor-session") as managed:
        resource = managed
        assert resource.is_open is True
        raise RuntimeError("Something went wrong")

    assert resource is not None
    assert resource.is_open is False


def test_exception_is_not_suppressed() -> None:
    with pytest.raises(ValueError, match="boom"), managed_resource("vendor-session"):
        raise ValueError("boom")
