"""Unit tests for SUController.

Tests all SU hardware operations with mocked DPISamplingUnit.
"""

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

    def test_perform_autocalibration_success(self, mock_su):
        """Test successful autocalibration."""
        controller = SUController(su=mock_su)
        result = controller.perform_autocalibration()

        assert result.ok is True
        assert result.serial == 1234
        mock_su.performautocalibration.assert_called_once()

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
