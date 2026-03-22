"""Integration-level conftest — real QThreadPool, mock hardware.

Tests here exercise the full service->controller->threading chain
with mocked hardware but real Qt signal marshalling.
"""

import pytest
from PySide6.QtCore import QThreadPool

from tests.conftest_hardware import (
    mock_smu_hardware,
    mock_su_hardware,
    mock_vu_hardware,
)

# Re-export so pytest discovers them
__all__ = ["mock_vu_hardware", "mock_smu_hardware", "mock_su_hardware"]


@pytest.fixture(autouse=True)
def _wait_for_thread_pool():
    """Ensure all tasks complete before test teardown."""
    yield
    QThreadPool.globalInstance().waitForDone(5000)
