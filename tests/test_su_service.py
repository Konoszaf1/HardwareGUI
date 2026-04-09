"""Tests for SamplingUnitService with mocked hardware.

Uses shared mock infrastructure from conftest_hardware.py.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.logic.controllers.base_controller import OperationResult
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


class TestSUServiceConnectionSafeguards:
    """Tests for connection health check, auto-disconnect, and retry logic."""

    def _make_connected_service(self):
        """Create a service that appears connected with mock hardware."""
        service = SamplingUnitService()
        service._su = MagicMock()
        service._mcu = MagicMock()
        service._controller = MagicMock()
        service._connected = True
        return service

    def test_health_check_detects_dead_device(self, mock_su_hardware):  # noqa: F811
        """_ensure_connected should reconnect when health check fails."""
        service = self._make_connected_service()
        old_su = service._su

        # Health check fails
        service._su.get_temperature.side_effect = RuntimeError("USB dead")

        # Patch DPISamplingUnit constructor for the reconnect
        new_su = MagicMock()
        with (
            patch("src.logic.services.su_service.DPISamplingUnit", return_value=new_su),
            patch("src.logic.services.su_service.DPIMainControlUnit", return_value=MagicMock()),
        ):
            service._ensure_connected()

        # Old SU should have been disconnected, new one created
        old_su.disconnect.assert_called_once()
        assert service._su is new_su
        assert service._connected is True

    def test_health_check_passes_skips_reconnect(self):
        """_ensure_connected should return immediately when health check passes."""
        service = self._make_connected_service()
        service._su.get_temperature.return_value = 25.0

        service._ensure_connected()

        # No reconnect should have happened
        service._su.disconnect.assert_not_called()
        assert service._connected is True

    def test_auto_disconnect_on_failed_operation(self):
        """_run_hw_operation should disconnect when operation returns ok=False."""
        service = self._make_connected_service()

        failed_result = OperationResult(ok=False, message="Hardware error")
        result = service._run_hw_operation(lambda c: failed_result)

        assert result.ok is False
        assert service._connected is False
        assert service._su is None
        assert service._controller is None

    def test_auto_disconnect_on_exception(self):
        """_run_hw_operation should disconnect when operation raises."""
        service = self._make_connected_service()

        def exploding_op(c):
            raise RuntimeError("USB stall")

        with pytest.raises(RuntimeError, match="USB stall"):
            service._run_hw_operation(exploding_op)

        assert service._connected is False
        assert service._su is None

    def test_successful_operation_stays_connected(self):
        """_run_hw_operation should keep connection alive on success."""
        service = self._make_connected_service()
        su_ref = service._su

        ok_result = OperationResult(ok=True, data={"value": 42})
        result = service._run_hw_operation(lambda c: ok_result)

        assert result.ok is True
        assert service._connected is True
        assert service._su is su_ref  # Same reference

    def test_partial_connect_failure_cleans_up(self):
        """_ensure_connected should clean up partial handles on failure."""
        service = SamplingUnitService()
        mock_su = MagicMock()

        with (
            patch("src.logic.services.su_service.DPISamplingUnit", return_value=mock_su),
            patch(
                "src.logic.services.su_service.DPIMainControlUnit",
                side_effect=RuntimeError("MCU error"),
            ),
            patch(
                "src.logic.services.su_service.SUController",
                side_effect=RuntimeError("Controller init failed"),
            ),
            patch("time.sleep"),
            pytest.raises(RuntimeError, match="Controller init failed"),
        ):
            service._ensure_connected()

        # SU should have been disconnected during cleanup (once per retry attempt)
        assert mock_su.disconnect.call_count == service._CONNECT_MAX_ATTEMPTS
        assert service._su is None
        assert service._connected is False

    def test_retry_succeeds_on_second_attempt(self):
        """_ensure_connected should retry and succeed on transient failure."""
        service = SamplingUnitService()

        call_count = 0
        mock_su = MagicMock()

        def flaky_su_constructor(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("USB busy")
            return mock_su

        with (
            patch(
                "src.logic.services.su_service.DPISamplingUnit", side_effect=flaky_su_constructor
            ),
            patch("src.logic.services.su_service.DPIMainControlUnit", return_value=MagicMock()),
            patch("time.sleep"),
        ):  # Don't actually sleep in tests
            service._ensure_connected()

        assert service._connected is True
        assert service._su is mock_su
        assert call_count == 2

    def test_retry_exhausted_raises(self):
        """_ensure_connected should raise after max attempts exhausted."""
        service = SamplingUnitService()

        with (
            patch(
                "src.logic.services.su_service.DPISamplingUnit",
                side_effect=RuntimeError("USB gone"),
            ),
            patch("time.sleep"),
            pytest.raises(RuntimeError, match="USB gone"),
        ):
            service._ensure_connected()

        assert service._connected is False

    def test_connectedChanged_emitted_on_invalidation(self, qtbot):
        """_invalidate_connection should emit connectedChanged(False)."""
        service = self._make_connected_service()

        with qtbot.waitSignal(service.connectedChanged, timeout=1000) as blocker:
            service._invalidate_connection()

        assert blocker.args == [False]
        assert service._connected is False
