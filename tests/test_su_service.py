"""Tests for SamplingUnitService with mocked hardware.

Uses shared mock infrastructure from conftest_hardware.py.
"""

import tempfile
from pathlib import Path

from src.logic.services.su_service import SamplingUnitService
from tests.conftest_hardware import mock_su_hardware  # noqa: F401


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

        assert service._target_instrument_ip == "192.168.1.100"
        assert service._targets.su_serial == 123
        assert service._targets.su_interface == 1
        assert service._targets.smu_serial == 456

    def test_set_instrument_ip_updates_ip(self):
        """set_instrument_ip should update the stored IP address."""
        service = SamplingUnitService()

        service.set_instrument_ip("10.0.0.1")

        assert service._target_instrument_ip == "10.0.0.1"

    def test_set_instrument_ip_resets_verification(self, qtbot):
        """Changing instrument IP should reset verification state."""
        service = SamplingUnitService()
        service._instrument_verified_state = True

        with qtbot.waitSignal(service.instrumentVerified, timeout=1000):
            service.set_instrument_ip("10.0.0.2")

        assert service._instrument_verified_state is False


class TestSUServiceTasks:
    """Test task execution with mocked hardware.

    These tests run tasks synchronously and verify:
    - Task completes successfully
    - Results contain expected data
    """

    def test_run_hw_setup_executes_successfully(self, mock_su_hardware, qtbot):  # noqa: F811
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

    def test_run_verify_executes_successfully(self, mock_su_hardware, qtbot):  # noqa: F811
        """run_verify should execute successfully and return results."""
        service = SamplingUnitService()
        service._su = mock_su_hardware["su"]

        task = service.run_verify()
        results = []
        task.signals.finished.connect(lambda r: results.append(r))
        task.run()

        assert len(results) == 1
        assert results[0].ok is True

    def test_connect_only_executes_successfully(self, mock_su_hardware, qtbot):  # noqa: F811
        """connect_only should execute successfully."""
        service = SamplingUnitService()
        service._su = mock_su_hardware["su"]

        task = service.connect_only()
        results = []
        task.signals.finished.connect(lambda r: results.append(r))
        task.run()

        assert len(results) == 1
        assert results[0].ok is True


class TestSUServiceCalibration:
    """Test calibration-related service methods."""

    def test_run_calibration_measure_returns_none_without_ip(self):
        """run_calibration_measure should return None when Keithley IP is not set."""
        service = SamplingUnitService()
        service._target_instrument_ip = ""

        result = service.run_calibration_measure()
        assert result is None

    def test_run_load_calibration_status_returns_none_without_folder(self):
        """run_load_calibration_status should return None when no folder exists."""
        service = SamplingUnitService()
        service._calibration_folder = "/nonexistent/path"

        result = service.run_load_calibration_status()
        assert result is None

    def test_resolve_calibration_folder_with_serial(self):
        """_resolve_calibration_folder should construct path from serial."""
        service = SamplingUnitService()
        with tempfile.TemporaryDirectory() as tmpdir:
            cal_dir = Path(tmpdir) / "calibration" / "su_calibration_sn4020"
            cal_dir.mkdir(parents=True)

            # Temporarily change working dir to find the calibration folder
            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                service._targets.su_serial = 4020
                result = service._resolve_calibration_folder()
                assert "su_calibration_sn4020" in result
            finally:
                os.chdir(old_cwd)

    def test_run_clear_calibration_file_returns_none_without_folder(self):
        """run_clear_calibration_file should return None when no folder exists."""
        service = SamplingUnitService()
        service._calibration_folder = "/nonexistent/path"

        result = service.run_clear_calibration_file("raw")
        assert result is None

    def test_run_clear_fitted_data_returns_none_without_folder(self):
        """run_clear_fitted_data should return None when no folder exists."""
        service = SamplingUnitService()
        service._calibration_folder = "/nonexistent/path"

        result = service.run_clear_fitted_data()
        assert result is None
