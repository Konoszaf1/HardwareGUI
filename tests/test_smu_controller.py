"""Unit tests for SMUController.

Tests all SMU hardware operations with mocked DPISourceMeasureUnit.
"""

from unittest.mock import MagicMock

import pytest

from src.logic.controllers.smu_controller import SMUController


@pytest.fixture
def mock_smu():
    """Create a mock DPISourceMeasureUnit."""
    smu = MagicMock()
    smu.get_serial.return_value = 2014
    smu.get_temperature.return_value = 27.3
    smu.ivconverter_getchannel.return_value = 1
    smu.ivconverter_getchannelreference.return_value = "GND"
    smu.highpass_state.return_value = 0
    smu.saturationdetection_state.return_value = (0, 0)
    return smu


class TestSMUControllerSetup:
    """Tests for SMU setup operations."""

    def test_initialize_device_success(self, mock_smu):
        """Test successful device initialization."""
        controller = SMUController(smu=mock_smu)
        result = controller.initialize_device(serial=2014)

        assert result.ok is True
        assert result.serial == 2014
        mock_smu.set_eeprom_default_values.assert_called_once()
        mock_smu.initNewDevice.assert_called_once_with(
            serial=2014,
            processorType="746",
            connectorType="BNC",
        )

    def test_initialize_device_with_triax(self, mock_smu):
        """Test initialization with TRIAX connector."""
        controller = SMUController(smu=mock_smu)
        result = controller.initialize_device(
            serial=3000,
            connector_type="TRIAX",
        )

        assert result.ok is True
        mock_smu.initNewDevice.assert_called_once_with(
            serial=3000,
            processorType="746",
            connectorType="TRIAX",
        )

    def test_set_eeprom_defaults_success(self, mock_smu):
        """Test EEPROM defaults reset."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_eeprom_defaults()

        assert result.ok is True
        mock_smu.set_eeprom_default_values.assert_called_once()

    def test_calibrate_eeprom_success(self, mock_smu):
        """Test EEPROM calibration."""
        controller = SMUController(smu=mock_smu)
        result = controller.calibrate_eeprom()

        assert result.ok is True
        mock_smu.calibrate_eeprom.assert_called_once()


class TestSMUControllerTest:
    """Tests for SMU test operations."""

    def test_read_temperature_success(self, mock_smu):
        """Test successful temperature reading."""
        controller = SMUController(smu=mock_smu)
        result = controller.read_temperature()

        assert result.ok is True
        assert result.data["temperature"] == 27.3
        mock_smu.get_temperature.assert_called_once()


class TestSMUControllerRelays:
    """Tests for SMU relay control operations."""

    def test_set_iv_channel_enable(self, mock_smu):
        """Test IV channel enable."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_iv_channel(channel=5, reference="VSMU")

        assert result.ok is True
        assert result.data["channel"] == 5
        mock_smu.ivconverter_channelreference.assert_called_once_with(channel=5, reference="VSMU")

    def test_set_iv_channel_disable(self, mock_smu):
        """Test IV channel disable."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_iv_channel(channel=0)

        assert result.ok is True
        mock_smu.ivconverter_channel.assert_called_once_with(channel=0)

    def test_get_iv_channel(self, mock_smu):
        """Test get IV channel."""
        controller = SMUController(smu=mock_smu)
        result = controller.get_iv_channel()

        assert result.ok is True
        assert result.data["channel"] == 1

    def test_set_pa_channel_enable(self, mock_smu):
        """Test PA channel enable."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_pa_channel(channel=3)

        assert result.ok is True
        mock_smu.postamplifier_enable.assert_called_once_with(channel=3)

    def test_set_pa_channel_disable(self, mock_smu):
        """Test PA channel disable."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_pa_channel(channel=0)

        assert result.ok is True
        mock_smu.postamplifier_disable.assert_called_once()

    def test_set_highpass_enable(self, mock_smu):
        """Test highpass enable."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_highpass(enabled=True)

        assert result.ok is True
        mock_smu.highpass_enable.assert_called_once()

    def test_set_highpass_disable(self, mock_smu):
        """Test highpass disable."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_highpass(enabled=False)

        assert result.ok is True
        mock_smu.highpass_disable.assert_called_once()

    def test_get_highpass_state(self, mock_smu):
        """Test get highpass state."""
        controller = SMUController(smu=mock_smu)
        result = controller.get_highpass_state()

        assert result.ok is True
        assert result.data["enabled"] is False

    def test_set_input_routing_gnd(self, mock_smu):
        """Test input routing to GND."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_input_routing("GND")

        assert result.ok is True
        mock_smu.iin_to_gnd.assert_called_once()

    def test_set_input_routing_vsmu_and_su(self, mock_smu):
        """Test input routing to VSMU and SU."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_input_routing("VSMU_AND_SU")

        assert result.ok is True
        mock_smu.iin_to_vsmu_and_su.assert_called_once()

    def test_set_vguard_gnd(self, mock_smu):
        """Test VGUARD to GND."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_vguard("GND")

        assert result.ok is True
        mock_smu.vguard_to_gnd.assert_called_once()

    def test_set_vguard_vsmu(self, mock_smu):
        """Test VGUARD to VSMU."""
        controller = SMUController(smu=mock_smu)
        result = controller.set_vguard("VSMU")

        assert result.ok is True
        mock_smu.vguard_to_vsmu.assert_called_once()

    def test_get_saturation_state(self, mock_smu):
        """Test get saturation state."""
        controller = SMUController(smu=mock_smu)
        result = controller.get_saturation_state()

        assert result.ok is True
        assert result.data["iv_saturated"] is False
        assert result.data["pa_saturated"] is False

    def test_clear_saturation(self, mock_smu):
        """Test clear saturation."""
        controller = SMUController(smu=mock_smu)
        result = controller.clear_saturation()

        assert result.ok is True
        mock_smu.saturationdetection_clear.assert_called_once()
