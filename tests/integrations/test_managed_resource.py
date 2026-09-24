import pytest

from python_integration_service.integrations.managed_resource import ManagedResource


def test_resource_is_open_inside_with() -> None:
    resource = ManagedResource("vendor-session")

    with resource as managed_resource:
        assert managed_resource.is_open is True
        assert managed_resource.name == "vendor-session"


def test_resource_is_closed_after_normal_exit() -> None:
    resource = ManagedResource("vendor-session")

    with resource:
        assert resource.is_open is True

    assert resource.is_open is False


def test_resource_is_closed_when_exception_occurs() -> None:
    resource = ManagedResource("vendor-session")

    with pytest.raises(RuntimeError), resource:
        assert resource.is_open is True
        raise RuntimeError("Something went wrong")

    assert resource.is_open is False


def test_exception_is_not_suppressed() -> None:
    resource = ManagedResource("vendor-session")

    with pytest.raises(ValueError, match="boom"), resource:
        raise ValueError("boom")
