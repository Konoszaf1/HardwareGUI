"""Tests for SamplingUnitService with mocked hardware.

Uses shared mock infrastructure from conftest_hardware.py.
"""

import subprocess

import pytest

from src.logic.services.su_service import SamplingUnitService

# Import hardware fixtures
pytest_plugins = ["tests.conftest_hardware"]


class TestSUServiceConfiguration:
    """Test service configuration methods."""

    def test_set_targets_stores_values(self):
        """set_targets should store hardware connection parameters."""
        service = SamplingUnitService()

        service.set_targets(
            keithley_ip="192.168.1.100",
            su_serial=123,
            su_interface=1,
            smu_serial=456,
            smu_interface=2,
        )

        assert service._target_keithley_ip == "192.168.1.100"
        assert service._targets.su_serial == 123
        assert service._targets.su_interface == 1
        assert service._targets.smu_serial == 456

    def test_set_keithley_ip_updates_ip(self):
        """set_keithley_ip should update the stored IP address."""
        service = SamplingUnitService()

        service.set_keithley_ip("10.0.0.1")

        assert service._target_keithley_ip == "10.0.0.1"

    def test_set_keithley_ip_resets_verification(self, qtbot):
        """Changing Keithley IP should reset verification state."""
        service = SamplingUnitService()
        service._keithley_verified_state = True

        with qtbot.waitSignal(service.keithleyVerified, timeout=1000):
            service.set_keithley_ip("10.0.0.2")

        assert service._keithley_verified_state is False


class TestSUServicePing:
    """Test Keithley ping functionality."""

    def test_ping_keithley_success(self, mocker):
        """ping_keithley should return True when ping succeeds."""
        mocker.patch("subprocess.check_call")
        service = SamplingUnitService()
        service._target_keithley_ip = "192.168.1.1"

        result = service.ping_keithley()

        assert result is True
        assert service.is_keithley_verified is True

    def test_ping_keithley_failure(self, mocker):
        """ping_keithley should return False when ping fails."""
        mocker.patch(
            "subprocess.check_call",
            side_effect=subprocess.CalledProcessError(1, "ping"),
        )
        service = SamplingUnitService()
        service._target_keithley_ip = "192.168.1.1"

        result = service.ping_keithley()

        assert result is False
        assert service.is_keithley_verified is False


class TestSUServiceTasks:
    """Test task execution with mocked hardware.

    These tests run tasks synchronously and verify:
    - Task completes successfully
    - Results contain expected data
    """

    def test_run_hw_setup_executes_successfully(self, mock_su_hardware, qtbot):
        """run_hw_setup should execute successfully and return results."""
        service = SamplingUnitService()
        service._su = mock_su_hardware["su"]

        task = service.run_hw_setup(serial=100)
        assert task is not None

        results = []
        task.signals.finished.connect(lambda r: results.append(r))
        task.run()

        assert len(results) == 1
        assert results[0].ok is True

    def test_run_verify_executes_successfully(self, mock_su_hardware, qtbot):
        """run_verify should execute successfully and return results."""
        service = SamplingUnitService()
        service._su = mock_su_hardware["su"]

        task = service.run_verify()
        results = []
        task.signals.finished.connect(lambda r: results.append(r))
        task.run()

        assert len(results) == 1
        assert results[0].ok is True

    def test_connect_only_executes_successfully(self, mock_su_hardware, qtbot):
        """connect_only should execute successfully."""
        service = SamplingUnitService()
        service._su = mock_su_hardware["su"]

        task = service.connect_only()
        results = []
        task.signals.finished.connect(lambda r: results.append(r))
        task.run()

        assert len(results) == 1
        assert results[0].ok is True


class TestSUServiceRequiresKeithley:
    """Test that methods requiring Keithley IP handle missing IP correctly."""

    def test_calibration_measure_without_keithley_returns_none(self):
        """run_calibration_measure should return None when Keithley IP not set."""
        service = SamplingUnitService()

        with pytest.warns(UserWarning, match="requires Keithley IP"):
            task = service.run_calibration_measure()

        assert task is None
