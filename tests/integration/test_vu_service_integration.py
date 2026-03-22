"""Integration tests for VoltageUnitService — full async lifecycle.

These tests run FunctionTask through QThreadPool (not synchronous .run())
and verify the full signal chain via qtbot.waitSignal().
"""

import pytest

from src.logic.qt_workers import run_in_thread
from src.logic.services.vu_service import VoltageUnitService

pytestmark = pytest.mark.integration


class TestVUServiceAsyncConnect:
    """Test connect operations through QThreadPool."""

    def test_connect_and_read_async_completes(self, mock_vu_hardware, qtbot):
        """connect_and_read completes through QThreadPool and emits finished."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.connect_and_read()
        assert task is not None

        with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
            run_in_thread(task)

        result = blocker.args[0]
        assert result.ok is True
        assert "coeffs" in result.data

    def test_connect_and_read_emits_started(self, mock_vu_hardware, qtbot):
        """connect_and_read emits started signal before finished."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.connect_and_read()
        started = []
        task.signals.started.connect(lambda: started.append(True))

        with qtbot.waitSignal(task.signals.finished, timeout=5000):
            run_in_thread(task)

        assert len(started) == 1

    def test_connect_only_async(self, mock_vu_hardware, qtbot):
        """connect_only completes through QThreadPool."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.connect_only()
        assert task is not None

        with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
            run_in_thread(task)

        result = blocker.args[0]
        assert result.ok is True


class TestVUServiceAsyncTests:
    """Test VU test operations through QThreadPool."""

    def test_test_outputs_async(self, mock_vu_hardware, qtbot):
        """test_outputs completes asynchronously with artifacts."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.test_outputs()
        assert task is not None

        with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
            run_in_thread(task)

        result = blocker.args[0]
        assert result.ok is True
        assert "artifacts" in result.data

    def test_test_ramp_async(self, mock_vu_hardware, qtbot):
        """test_ramp completes asynchronously."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.test_ramp()

        with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
            run_in_thread(task)

        result = blocker.args[0]
        assert result.ok is True

    def test_autocal_python_async(self, mock_vu_hardware, qtbot):
        """autocal_python completes asynchronously."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.autocal_python()

        with qtbot.waitSignal(task.signals.finished, timeout=10000) as blocker:
            run_in_thread(task)

        result = blocker.args[0]
        assert result.ok is True


class TestVUServiceAsyncGuard:
    """Test guard operations through QThreadPool."""

    def test_guard_signal_async(self, mock_vu_hardware, qtbot):
        """set_guard_signal completes asynchronously."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.set_guard_signal()

        with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
            run_in_thread(task)

        result = blocker.args[0]
        assert result.ok is True
        assert result.data.get("guard") == "signal"

    def test_guard_ground_async(self, mock_vu_hardware, qtbot):
        """set_guard_ground completes asynchronously."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.set_guard_ground()

        with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
            run_in_thread(task)

        result = blocker.args[0]
        assert result.ok is True
        assert result.data.get("guard") == "ground"


class TestVUServiceDecoratorBehavior:
    """Test require_instrument_ip decorator in async context."""

    def test_no_ip_returns_none(self):
        """Methods decorated with require_instrument_ip return None without IP."""
        service = VoltageUnitService()

        with pytest.warns(UserWarning, match="requires instrument IP"):
            task = service.connect_and_read()

        assert task is None

    def test_disconnect_async(self, mock_vu_hardware, qtbot):
        """disconnect_hardware completes and emits connectedChanged(False)."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        # First connect
        connect_task = service.connect_only()
        with qtbot.waitSignal(connect_task.signals.finished, timeout=5000):
            run_in_thread(connect_task)

        # Then disconnect
        disconnect_task = service.disconnect_hardware()
        with qtbot.waitSignal(disconnect_task.signals.finished, timeout=5000):
            run_in_thread(disconnect_task)

        assert service.connected is False


class TestVUServiceSignalOrder:
    """Test that signals are emitted in correct order."""

    def test_started_before_finished(self, mock_vu_hardware, qtbot):
        """Started signal is emitted before finished signal."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.connect_and_read()
        events = []
        task.signals.started.connect(lambda: events.append("started"))
        task.signals.finished.connect(lambda r: events.append("finished"))

        with qtbot.waitSignal(task.signals.finished, timeout=5000):
            run_in_thread(task)

        assert events == ["started", "finished"]

    def test_log_between_started_and_finished(self, mock_vu_hardware, qtbot):
        """Log signals are emitted between started and finished."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.connect_and_read()
        events = []
        task.signals.started.connect(lambda: events.append("started"))
        task.signals.log.connect(lambda s: events.append("log"))
        task.signals.finished.connect(lambda r: events.append("finished"))

        with qtbot.waitSignal(task.signals.finished, timeout=5000):
            run_in_thread(task)

        assert events[0] == "started"
        assert events[-1] == "finished"
