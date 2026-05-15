"""Global fixtures for custom integration."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    """Enable custom integrations defined in the test dir."""
    return


@pytest.fixture(autouse=True)
def mock_reachability():
    """Mock TCP reachability to succeed by default."""
    with patch(
        "custom_components.grubstation.coordinator.async_check_tcp_reachability",
        return_value=True,
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_agent_status():
    """Mock agent status to succeed by default."""
    with patch(
        "custom_components.grubstation.coordinator.async_get_agent_status",
        new_callable=AsyncMock,
        return_value={
            "status": "ok",
            "os": "linux",
            "service_manager": "systemd",
            "version": "1.0.0",
        },
    ) as mock:
        yield mock
