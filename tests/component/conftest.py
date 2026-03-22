"""Component-level conftest — provides mock services with real Qt signals.

The key challenge is that MagicMock services don't have real Signal objects,
so qtbot.waitSignal() fails. This module provides QObject-based mock services
that have real signals but mock methods.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from src.logic.qt_workers import FunctionTask, TaskResult, TaskSignals


# ---------------------------------------------------------------------------
# Mock service base with real Qt signals
# ---------------------------------------------------------------------------


class MockServiceSignals(QObject):
    """Real Qt signals for mock services — enables qtbot.waitSignal()."""

    connectedChanged = Signal(bool)
    instrumentVerified = Signal(bool)
    coeffsChanged = Signal(object)


class MockVUService(QObject):
    """Mock VoltageUnitService with real Qt signals and mock methods."""

    connectedChanged = Signal(bool)
    instrumentVerified = Signal(bool)
    coeffsChanged = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._instrument_verified = False

        # Mock all public methods
        self.set_instrument_ip = MagicMock()
        self.set_targets = MagicMock()
        self.ping_instrument = MagicMock()
        self.disconnect_hardware = MagicMock()
        self.search_instruments = MagicMock()
        self.connect_only = MagicMock()
        self.connect_and_read = MagicMock()
        self.read_coefficients = MagicMock()
        self.reset_coefficients_ram = MagicMock()
        self.write_coefficients_eeprom = MagicMock()
        self.set_guard_signal = MagicMock()
        self.set_guard_ground = MagicMock()
        self.test_outputs = MagicMock()
        self.test_ramp = MagicMock()
        self.test_transient = MagicMock()
        self.test_all = MagicMock()
        self.autocal_python = MagicMock()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def is_instrument_verified(self) -> bool:
        return self._instrument_verified

    @property
    def artifact_dir(self) -> str:
        return "/tmp/test_artifacts"

    @property
    def coeffs(self) -> dict:
        return {"CH1": [1.0, 0.0], "CH2": [1.0, 0.0], "CH3": [1.0, 0.0]}

    def set_connected(self, value: bool) -> None:
        """Helper to change connected state and emit signal."""
        self._connected = value
        self.connectedChanged.emit(value)

    def set_verified(self, value: bool) -> None:
        """Helper to change verification state and emit signal."""
        self._instrument_verified = value
        self.instrumentVerified.emit(value)


class MockSMUService(QObject):
    """Mock SourceMeasureUnitService with real Qt signals."""

    connectedChanged = Signal(bool)
    instrumentVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._instrument_verified = False
        self.set_instrument_ip = MagicMock()
        self.set_targets = MagicMock()
        self.ping_instrument = MagicMock()
        self.disconnect_hardware = MagicMock()
        self.connect_only = MagicMock()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def is_instrument_verified(self) -> bool:
        return self._instrument_verified

    def set_connected(self, value: bool) -> None:
        self._connected = value
        self.connectedChanged.emit(value)


class MockSUService(QObject):
    """Mock SamplingUnitService with real Qt signals."""

    connectedChanged = Signal(bool)
    instrumentVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._instrument_verified = False
        self.set_instrument_ip = MagicMock()
        self.set_targets = MagicMock()
        self.ping_instrument = MagicMock()
        self.disconnect_hardware = MagicMock()
        self.connect_only = MagicMock()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def is_instrument_verified(self) -> bool:
        return self._instrument_verified

    def set_connected(self, value: bool) -> None:
        self._connected = value
        self.connectedChanged.emit(value)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_vu_service() -> MockVUService:
    """Create a MockVUService with real signals."""
    return MockVUService()


@pytest.fixture
def mock_smu_service() -> MockSMUService:
    """Create a MockSMUService with real signals."""
    return MockSMUService()


@pytest.fixture
def mock_su_service() -> MockSUService:
    """Create a MockSUService with real signals."""
    return MockSUService()


@pytest.fixture
def mock_shared_panels(qtbot):
    """Create a real SharedPanelsWidget for testing."""
    from src.gui.widgets.shared_panels_widget import SharedPanelsWidget

    panels = SharedPanelsWidget()
    qtbot.addWidget(panels)
    return panels


@pytest.fixture
def make_dummy_task():
    """Factory fixture to create FunctionTask with controllable behavior."""

    def _make(name: str = "test_task", return_value=None, side_effect=None):
        if side_effect:
            fn = side_effect
        else:
            fn = lambda: return_value  # noqa: E731
        task = FunctionTask(name, fn)
        return task

    return _make


@pytest.fixture
def make_finished_result():
    """Factory to create TaskResult objects for testing."""

    def _make(name: str = "test", ok: bool = True, data: dict | None = None):
        return TaskResult(name=name, ok=ok, data=data)

    return _make
