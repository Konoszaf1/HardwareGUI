"""Unit tests for SUController.

Tests all SU hardware operations with mocked DPISamplingUnit.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.logic.controllers.su_controller import SUController


@pytest.fixture
def mock_su():
    """Create a mock DPISamplingUnit."""
    su = MagicMock()
    su.getSerial.return_value = 1234
    su.getTemperature.return_value = 25.5
    su.readInputVoltage.return_value = 1.5
    su.transientSampling_readData.return_value = ([0.0, 0.1, 0.2], [1.0, 1.1, 1.2])
    su.pulseSampling_readData.return_value = ([0.0, 0.1], [2.0, 2.1])
    return su


@pytest.fixture
def mock_mcu():
    """Create a mock DPIMainControlUnit."""
    return MagicMock()


class TestSUControllerSetup:
    """Tests for SU setup operations."""

    def test_initialize_device_success(self, mock_su):
        """Test successful device initialization."""
        controller = SUController(su=mock_su)
        result = controller.initialize_device(serial=1234)

        assert result.ok is True
        assert result.serial == 1234
        mock_su.initNewDevice.assert_called_once_with(
            serial=1234,
            processorType="746",
            connectorType="BNC",
        )

    def test_initialize_device_with_custom_types(self, mock_su):
        """Test initialization with custom processor/connector types."""
        controller = SUController(su=mock_su)
        result = controller.initialize_device(
            serial=5678,
            processor_type="750",
            connector_type="SMA",
        )

        assert result.ok is True
        mock_su.initNewDevice.assert_called_once_with(
            serial=5678,
            processorType="750",
            connectorType="SMA",
        )

    def test_initialize_device_failure(self, mock_su):
        """Test initialization failure handling."""
        mock_su.initNewDevice.side_effect = RuntimeError("Device error")
        controller = SUController(su=mock_su)
        result = controller.initialize_device(serial=1234)

        assert result.ok is False
        assert "Device error" in result.message


class TestSUControllerTest:
    """Tests for SU test operations."""

    def test_read_temperature_success(self, mock_su):
        """Test successful temperature reading."""
        controller = SUController(su=mock_su)
        result = controller.read_temperature()

        assert result.ok is True
        assert result.data["temperature"] == 25.5
        mock_su.getTemperature.assert_called_once()

    def test_single_shot_measure_success(self, mock_su):
        """Test successful single-shot measurement."""
        controller = SUController(su=mock_su)
        result = controller.single_shot_measure(dac_voltage=1.0)

        assert result.ok is True
        assert result.data["voltage"] == 1.5
        mock_su.setDACValue.assert_called_once_with(1.0)
        mock_su.readInputVoltage.assert_called_once()

    def test_transient_measure_success(self, mock_su, mock_mcu):
        """Test successful transient measurement."""
        controller = SUController(su=mock_su, mcu=mock_mcu)
        result = controller.transient_measure(
            measurement_time=0.5,
            sampling_rate=1e-6,
        )

        assert result.ok is True
        assert "time" in result.data
        assert "values" in result.data
        mock_su.transientSampling_init.assert_called_once()
        mock_su.transientSampling_start.assert_called_once()
        mock_mcu.setSUSyncTimerFrequency.assert_called_once()

    def test_pulse_measure_success(self, mock_su, mock_mcu):
        """Test successful pulse measurement."""
        controller = SUController(su=mock_su, mcu=mock_mcu)
        result = controller.pulse_measure(num_samples=1000)

        assert result.ok is True
        assert "time" in result.data
        mock_su.pulseSampling_init.assert_called_once_with(1000)
        mock_mcu.su_set_trigger.assert_called_once()


class TestSUControllerMCU:
    """Tests for MCU operations."""

    def test_set_sync_frequency_success(self, mock_su, mock_mcu):
        """Test MCU sync frequency setting."""
        controller = SUController(su=mock_su, mcu=mock_mcu)
        result = controller.set_sync_frequency(su_frequency=500e3, vu_frequency=500e3)

        assert result.ok is True
        mock_mcu.setSUSyncTimerFrequency.assert_called_once_with(500e3)
        mock_mcu.setVUSyncTimerFrequency.assert_called_once_with(500e3)

    def test_set_sync_frequency_no_mcu(self, mock_su):
        """Test sync frequency without MCU connection."""
        controller = SUController(su=mock_su, mcu=None)
        result = controller.set_sync_frequency()

        assert result.ok is False
        assert "MCU not connected" in result.message

    def test_trigger_su_success(self, mock_su, mock_mcu):
        """Test MCU trigger."""
        controller = SUController(su=mock_su, mcu=mock_mcu)
        result = controller.trigger_su()

        assert result.ok is True
        mock_mcu.su_set_trigger.assert_called_once()


class TestSUControllerCalibration:
    """Tests for SU calibration data management."""

    def test_speed_presets_exist(self):
        """All three speed presets should be defined."""
        assert "fast" in SUController.SPEED_PRESETS
        assert "normal" in SUController.SPEED_PRESETS
        assert "precise" in SUController.SPEED_PRESETS
        for preset in SUController.SPEED_PRESETS.values():
            assert len(preset) == 3  # (decades, delta_log, delta_lin)

    def test_get_calibration_status_empty_folder(self, mock_su):
        """get_calibration_status should return empty list for empty folder."""
        controller = SUController(su=mock_su)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = controller.get_calibration_status(tmpdir)
            assert result == []

    def test_get_calibration_status_with_h5_data(self, mock_su):
        """get_calibration_status should parse HDF5 keys correctly."""
        h5py = pytest.importorskip("h5py")
        controller = SUController(su=mock_su)
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock raw_data.h5 with SU-format keys
            h5_path = Path(tmpdir) / "raw_data.h5"
            with h5py.File(str(h5_path), "w") as f:
                f.create_dataset("amp=AMP1 v_set=1.000e-03", data=[0.0])
                f.create_dataset("amp=AMP1 v_set=2.000e-03", data=[0.0])
                f.create_dataset("amp=AMP2 v_set=1.000e-03", data=[0.0])

            result = controller.get_calibration_status(tmpdir)
            assert len(result) == 2
            amp1 = next(r for r in result if r["amp_channel"] == "AMP1")
            amp2 = next(r for r in result if r["amp_channel"] == "AMP2")
            assert amp1["measured"] is True
            assert amp1["points"] == 2
            assert amp2["points"] == 1
            assert amp1["verified"] is False

    def test_clear_calibration_file_raw(self, mock_su):
        """clear_calibration_file should delete raw_data.h5."""
        controller = SUController(su=mock_su)
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = Path(tmpdir) / "raw_data.h5"
            raw_path.touch()
            assert raw_path.exists()

            result = controller.clear_calibration_file(tmpdir, target="raw")
            assert result.ok is True
            assert not raw_path.exists()

    def test_clear_calibration_file_verify(self, mock_su):
        """clear_calibration_file should delete raw_data_verify.h5."""
        controller = SUController(su=mock_su)
        with tempfile.TemporaryDirectory() as tmpdir:
            verify_path = Path(tmpdir) / "raw_data_verify.h5"
            verify_path.touch()

            result = controller.clear_calibration_file(tmpdir, target="verify")
            assert result.ok is True
            assert not verify_path.exists()

    def test_clear_fitted_data(self, mock_su):
        """clear_fitted_data should remove aggregated, model, and figures."""
        controller = SUController(su=mock_su)
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "aggregated.h5").touch()
            (Path(tmpdir) / "linear_model.cal").touch()
            figures = Path(tmpdir) / "figures" / "ranges"
            figures.mkdir(parents=True)
            (figures / "amp_AMP1_analyze.png").touch()

            result = controller.clear_fitted_data(tmpdir)
            assert result.ok is True
            assert not (Path(tmpdir) / "aggregated.h5").exists()
            assert not (Path(tmpdir) / "linear_model.cal").exists()
            assert not (Path(tmpdir) / "figures").exists()

    def test_delete_calibration_ranges(self, mock_su):
        """delete_calibration_ranges should remove matching HDF5 entries."""
        h5py = pytest.importorskip("h5py")
        controller = SUController(su=mock_su)
        with tempfile.TemporaryDirectory() as tmpdir:
            h5_path = Path(tmpdir) / "raw_data.h5"
            with h5py.File(str(h5_path), "w") as f:
                f.create_dataset("amp=AMP1 v_set=1.000e-03", data=[0.0])
                f.create_dataset("amp=AMP2 v_set=1.000e-03", data=[0.0])
                f.create_dataset("amp=AMP3 v_set=1.000e-03", data=[0.0])

            result = controller.delete_calibration_ranges(
                tmpdir, ranges=["AMP1", "AMP3"], target="raw"
            )
            assert result.ok is True
            assert result.data["deleted"] == 2

            # Only AMP2 should remain
            with h5py.File(str(h5_path), "r") as f:
                remaining = list(f.keys())
            assert len(remaining) == 1
            assert "AMP2" in remaining[0]

    def test_collect_analysis_plots(self, mock_su):
        """_collect_analysis_plots should find analysis PNGs."""
        controller = SUController(su=mock_su)
        with tempfile.TemporaryDirectory() as tmpdir:
            ranges_dir = Path(tmpdir) / "figures" / "ranges"
            ranges_dir.mkdir(parents=True)
            (ranges_dir / "amp_AMP1_analyze.png").touch()
            (ranges_dir / "amp_AMP2_analyze.png").touch()
            (ranges_dir / "other_file.png").touch()

            plots = controller._collect_analysis_plots(tmpdir)
            assert len(plots) == 2
            assert any("AMP1" in p for p in plots)
            assert any("AMP2" in p for p in plots)

    def test_parse_calibrated_ranges(self):
        """_parse_calibrated_ranges should extract amp_channel from filenames."""
        paths = [
            "/some/path/amp_AMP1_analyze.png",
            "/some/path/amp_AMP2_analyze.png",
            "/some/path/amp_AMP3_analyze.png",
        ]
        result = SUController._parse_calibrated_ranges(paths)
        assert len(result) == 3
        channels = [r["amp_channel"] for r in result]
        assert "AMP1" in channels
        assert "AMP2" in channels
        assert "AMP3" in channels
