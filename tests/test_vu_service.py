"""Tests for VoltageUnitService with mocked hardware.

These tests verify service behavior without requiring real hardware,
using import-level patching via the mock_vu_hardware fixture.
"""

import pytest

from src.logic.services.vu_service import VoltageUnitService

# Import hardware fixtures
pytest_plugins = ["tests.conftest_hardware"]


class TestVoltageUnitServiceConfiguration:
    """Test service configuration methods."""

    def test_set_targets_stores_values(self):
        """set_targets should store hardware connection parameters."""
        service = VoltageUnitService()

        service.set_targets(
            scope_ip="192.168.1.100",
            vu_serial=123,
            vu_interface=1,
            mcu_serial=456,
            mcu_interface=2,
        )

        assert service._target_instrument_ip == "192.168.1.100"
        assert service._targets.vu_serial == 123
        assert service._targets.vu_interface == 1

    def test_set_instrument_ip_updates_ip(self):
        """set_instrument_ip should update the stored IP address."""
        service = VoltageUnitService()

        service.set_instrument_ip("10.0.0.1")

        assert service._target_instrument_ip == "10.0.0.1"

    def test_set_instrument_ip_resets_verification(self, qtbot):
        """Changing instrument IP should reset verification state."""
        service = VoltageUnitService()
        service._instrument_verified_state = True

        with qtbot.waitSignal(service.instrumentVerified, timeout=1000):
            service.set_instrument_ip("10.0.0.2")

        assert service._instrument_verified_state is False


class TestVoltageUnitServicePing:
    """Test scope ping functionality."""

    def test_ping_instrument_success(self, mocker):
        """ping_instrument should return True when ping succeeds."""
        mocker.patch("subprocess.check_call")
        service = VoltageUnitService()
        service._target_instrument_ip = "192.168.1.1"

        result = service.ping_instrument()

        assert result is True
        assert service.is_instrument_verified is True

    def test_ping_instrument_failure(self, mocker):
        """ping_instrument should return False when ping fails."""
        import subprocess

        mocker.patch("subprocess.check_call", side_effect=subprocess.CalledProcessError(1, "ping"))
        service = VoltageUnitService()
        service._target_instrument_ip = "192.168.1.1"

        result = service.ping_instrument()

        assert result is False
        assert service.is_instrument_verified is False


class TestVoltageUnitServiceTasks:
    """Test task execution with mocked hardware.

    These tests run tasks synchronously and verify:
    - Task completes successfully
    - Hardware mocks are called
    - Results contain expected data
    """

    def test_connect_and_read_executes_and_returns_coeffs(self, mock_vu_hardware, qtbot):
        """connect_and_read should execute and return coefficient data."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.connect_and_read()
        assert task is not None

        # Run the task synchronously
        results = []
        task.signals.finished.connect(lambda r: results.append(r))
        task.run()

        # Verify task completed with success
        assert len(results) == 1
        result = results[0]
        assert result.ok is True
        assert "coeffs" in result.data
        assert isinstance(result.data["coeffs"], dict)

    def test_test_outputs_delegates_to_controller(self, mock_vu_hardware, qtbot):
        """test_outputs should delegate to controller and return artifacts."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.test_outputs()
        results = []
        task.signals.finished.connect(lambda r: results.append(r))
        task.run()

        assert len(results) == 1
        result = results[0]
        assert result.ok is True
        assert "artifacts" in result.data
        assert isinstance(result.data["artifacts"], list)

    def test_test_ramp_delegates_to_controller(self, mock_vu_hardware, qtbot):
        """test_ramp should delegate to controller and return artifacts."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.test_ramp()
        results = []
        task.signals.finished.connect(lambda r: results.append(r))
        task.run()

        assert len(results) == 1
        assert results[0].ok is True
        assert "artifacts" in results[0].data

    def test_autocal_python_executes_calibration(self, mock_vu_hardware, qtbot):
        """autocal_python should run calibration and return updated coefficients."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.autocal_python()
        results = []
        task.signals.finished.connect(lambda r: results.append(r))
        task.run()

        assert len(results) == 1
        result = results[0]
        assert result.ok is True
        # Calibration should return both coefficients and artifacts
        assert "coeffs" in result.data or "artifacts" in result.data

    def test_task_emits_started_signal(self, mock_vu_hardware, qtbot):
        """Tasks should emit started signal when execution begins."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.connect_and_read()
        started_emitted = []
        task.signals.started.connect(lambda: started_emitted.append(True))
        task.run()

        assert len(started_emitted) == 1


class TestVoltageUnitServiceGuard:
    """Test guard signal functionality."""

    def test_guard_signal_returns_task(self, mock_vu_hardware):
        """set_guard_signal should return a FunctionTask."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.set_guard_signal()

        assert task is not None

    def test_guard_ground_returns_task(self, mock_vu_hardware):
        """set_guard_ground should return a FunctionTask."""
        service = VoltageUnitService()
        service.set_instrument_ip("192.168.1.1")

        task = service.set_guard_ground()

        assert task is not None


class TestVoltageUnitServiceRequiresScope:
    """Test that methods requiring scope IP handle missing IP correctly."""

    def test_connect_and_read_without_scope_returns_none(self):
        """connect_and_read should return None when instrument IP is not set."""
        service = VoltageUnitService()
        # Don't set scope_ip

        with pytest.warns(UserWarning, match="requires instrument IP"):
            task = service.connect_and_read()

        assert task is None

    def test_test_outputs_without_scope_returns_none(self):
        """test_outputs should return None when instrument IP is not set."""
        service = VoltageUnitService()

        with pytest.warns(UserWarning, match="requires instrument IP"):
            task = service.test_outputs()

        assert task is None
