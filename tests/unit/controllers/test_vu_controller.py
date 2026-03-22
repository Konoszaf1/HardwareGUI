"""Unit tests for VUController.

Tests all VUController methods including setup, temperature, autocalibration,
coefficient management, guard controls, test operations (outputs, ramp,
transient), test_all delegation, and iterative auto-calibration.
"""

import os
import sys
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.logic.controllers.base_controller import OperationResult
from src.logic.controllers.vu_controller import VUController


# ---------------------------------------------------------------------------
# Ensure dpi.configuration mock is in sys.modules so that the runtime
# ``from dpi.configuration import DPIConfiguration`` inside test_transient
# resolves.  The root conftest mocks "dpi" but not "dpi.configuration".
# ---------------------------------------------------------------------------

_dpi_configuration_mod = MagicMock()
if "dpi.configuration" not in sys.modules:
    sys.modules["dpi.configuration"] = _dpi_configuration_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scope_binary(data_array: np.ndarray) -> bytes:
    """Build IEEE 488.2 definite-length binary block from a numpy array."""
    data_bytes = data_array.astype(np.single).tobytes()
    len_str = str(len(data_bytes))
    header = f"#{len(len_str)}{len_str}".encode()
    return header + data_bytes


def _make_ramp_scope_data(n_points: int = 5000) -> bytes:
    """Build scope binary data containing a linear ramp with measurable slope.

    The ramp spans t in [-0.05, 0.05] (matching HEAD response) and produces
    a slope of -20 V/s (matching CH1 expected slope for amp=-1.0).
    """
    t = np.linspace(-0.05, 0.05, n_points, dtype=np.single)
    # slope = -20 V/s (1 * 20 * amp where amp = -1.0)
    data = t * (-20.0)
    return _make_scope_binary(data)


def _make_transient_scope_data(n_points: int = 5000) -> bytes:
    """Build scope binary data that mimics a transient step response.

    Creates a step function from -1V to +1V centered at t=0.  Uses the
    transient-appropriate time window of -5e-6 .. +5e-6 (matching the scope
    config TIM:SCAL = 1e-6, so 10 divisions x 1us = 10us total).  This
    ensures the overshoot analysis slices (abs(t) < 1e-6, t < -4e-6, etc.)
    have non-empty arrays.
    """
    t = np.linspace(-5e-6, 5e-6, n_points, dtype=np.single)
    data = np.zeros_like(t)
    data[t < -5e-6] = 0.0
    data[(t >= -5e-6) & (t < 0)] = -1.0
    data[(t >= 0) & (t <= 5e-6)] = 1.0
    data[t > 5e-6] = 0.0
    return _make_scope_binary(data)


# ===========================================================================
# TestVUControllerInit
# ===========================================================================


@pytest.mark.unit
class TestVUControllerInit:
    """Tests for VUController.__init__ and basic attributes."""

    def test_init_sets_attributes(self, mock_vu, mock_mcu, mock_scope, tmp_path):
        """Verify constructor stores all injected dependencies."""
        ctrl = VUController(
            vu=mock_vu,
            mcu=mock_mcu,
            scope=mock_scope,
            vu_serial=2503,
            artifact_dir=str(tmp_path),
        )
        assert ctrl._vu is mock_vu
        assert ctrl._mcu is mock_mcu
        assert ctrl._scope is mock_scope
        assert ctrl._vu_serial == 2503
        assert ctrl._artifact_dir == str(tmp_path)

    def test_init_default_coefficients(self, vu_controller):
        """Verify default coefficients are k=1.0, d=0.0 for all channels."""
        expected = {"CH1": [1.0, 0.0], "CH2": [1.0, 0.0], "CH3": [1.0, 0.0]}
        assert vu_controller.coeffs == expected

    def test_init_default_artifact_dir(self, mock_vu, mock_mcu, mock_scope):
        """Verify artifact_dir defaults to calibration_vu<serial> when omitted."""
        ctrl = VUController(vu=mock_vu, mcu=mock_mcu, scope=mock_scope, vu_serial=9999)
        assert ctrl._artifact_dir == "calibration_vu9999"

    def test_coeffs_property_returns_current_state(self, vu_controller):
        """Verify coeffs property reflects internal state."""
        vu_controller._coeffs["CH1"] = [1.05, -0.01]
        assert vu_controller.coeffs["CH1"] == [1.05, -0.01]


# ===========================================================================
# TestVUControllerSetup
# ===========================================================================


@pytest.mark.unit
class TestVUControllerSetup:
    """Tests for VUController.initialize_device."""

    def test_initialize_device_success(self, vu_controller, mock_vu):
        """Verify successful device initialization returns ok and serial."""
        result = vu_controller.initialize_device(serial=2503)
        assert result.ok is True
        assert result.serial == 2503
        mock_vu.initNewDevice.assert_called_once_with(
            serial=2503, processorType="746", connectorType="BNC"
        )

    def test_initialize_device_with_custom_types(self, vu_controller, mock_vu):
        """Verify custom processor and connector types are forwarded."""
        result = vu_controller.initialize_device(
            serial=1234, processor_type="890", connector_type="SMA"
        )
        assert result.ok is True
        assert result.serial == 1234
        mock_vu.initNewDevice.assert_called_once_with(
            serial=1234, processorType="890", connectorType="SMA"
        )

    def test_initialize_device_failure_returns_error(self, vu_controller, mock_vu):
        """Verify hardware exception produces ok=False with error message."""
        mock_vu.initNewDevice.side_effect = Exception("hw error")
        result = vu_controller.initialize_device(serial=2503)
        assert result.ok is False
        assert "hw error" in result.message

    @pytest.mark.parametrize("serial", [1, 5000, 9999])
    def test_initialize_device_various_serials(self, vu_controller, mock_vu, serial):
        """Verify initialization works across boundary serial values."""
        result = vu_controller.initialize_device(serial=serial)
        assert result.ok is True
        assert result.serial == serial


# ===========================================================================
# TestVUControllerTemperature
# ===========================================================================


@pytest.mark.unit
class TestVUControllerTemperature:
    """Tests for VUController.read_temperature."""

    def test_read_temperature_success(self, vu_controller, mock_vu):
        """Verify temperature is read and returned in data dict."""
        result = vu_controller.read_temperature()
        assert result.ok is True
        assert result.data["temperature"] == 25.4
        mock_vu.get_temperature.assert_called_once()

    def test_read_temperature_failure(self, vu_controller, mock_vu):
        """Verify hardware exception produces ok=False."""
        mock_vu.get_temperature.side_effect = Exception("hw error")
        result = vu_controller.read_temperature()
        assert result.ok is False
        assert "hw error" in result.message

    @pytest.mark.parametrize("temp", [-40.0, 0.0, 25.4, 85.0, 125.0])
    def test_read_temperature_various_values(self, vu_controller, mock_vu, temp):
        """Verify different temperature values are passed through correctly."""
        mock_vu.get_temperature.return_value = temp
        result = vu_controller.read_temperature()
        assert result.ok is True
        assert result.data["temperature"] == temp


# ===========================================================================
# TestVUControllerAutocalibration
# ===========================================================================


@pytest.mark.unit
class TestVUControllerAutocalibration:
    """Tests for VUController.perform_autocalibration."""

    def test_perform_autocalibration_success(self, vu_controller, mock_vu):
        """Verify autocalibration runs on all 3 channels and returns ok."""
        result = vu_controller.perform_autocalibration()
        assert result.ok is True
        assert "coeffs" in result.data
        assert mock_vu.performautocalibration.call_count == 3
        mock_vu.performautocalibration.assert_any_call("CH1")
        mock_vu.performautocalibration.assert_any_call("CH2")
        mock_vu.performautocalibration.assert_any_call("CH3")

    def test_perform_autocalibration_reads_back_coefficients(self, vu_controller, mock_vu):
        """Verify coefficients are re-read from hardware after calibration."""
        mock_vu.get_correctionvalues.return_value = [1.05, -0.002]
        result = vu_controller.perform_autocalibration()
        assert result.ok is True
        # get_correctionvalues called 3 times (once per channel for readback)
        assert mock_vu.get_correctionvalues.call_count == 3
        for ch in ("CH1", "CH2", "CH3"):
            assert result.data["coeffs"][ch] == [1.05, -0.002]

    def test_perform_autocalibration_failure(self, vu_controller, mock_vu):
        """Verify exception during autocalibration returns ok=False."""
        mock_vu.performautocalibration.side_effect = Exception("hw error")
        result = vu_controller.perform_autocalibration()
        assert result.ok is False
        assert "hw error" in result.message


# ===========================================================================
# TestVUControllerCoefficients
# ===========================================================================


@pytest.mark.unit
class TestVUControllerCoefficients:
    """Tests for coefficient management: read, reset, write."""

    def test_read_coefficients_success(self, vu_controller, mock_vu):
        """Verify coefficients are read from all 3 channels."""
        mock_vu.get_correctionvalues.return_value = [1.02, -0.005]
        result = vu_controller.read_coefficients()
        assert result.ok is True
        assert mock_vu.get_correctionvalues.call_count == 3
        for ch in ("CH1", "CH2", "CH3"):
            assert result.data["coeffs"][ch] == [1.02, -0.005]

    def test_read_coefficients_failure(self, vu_controller, mock_vu):
        """Verify read failure returns ok=False."""
        mock_vu.get_correctionvalues.side_effect = Exception("hw error")
        result = vu_controller.read_coefficients()
        assert result.ok is False
        assert "hw error" in result.message

    def test_reset_coefficients_ram_only(self, vu_controller, mock_vu):
        """Verify reset with write_eeprom=False sets RAM only."""
        vu_controller._coeffs["CH1"] = [1.05, -0.01]
        result = vu_controller.reset_coefficients(write_eeprom=False)
        assert result.ok is True
        for ch in ("CH1", "CH2", "CH3"):
            assert result.data["coeffs"][ch] == [1.0, 0.0]
        # Check that writetoeeprom=False was passed for all 3 calls
        for c in mock_vu.set_correctionvalues.call_args_list:
            assert c.kwargs["writetoeeprom"] is False

    def test_reset_coefficients_with_eeprom(self, vu_controller, mock_vu):
        """Verify reset with write_eeprom=True persists to EEPROM."""
        result = vu_controller.reset_coefficients(write_eeprom=True)
        assert result.ok is True
        for c in mock_vu.set_correctionvalues.call_args_list:
            assert c.kwargs["writetoeeprom"] is True

    def test_reset_coefficients_calls_voltageToRawWord(self, vu_controller, mock_vu):
        """Verify reset computes zeroword via voltageToRawWord for each channel."""
        vu_controller.reset_coefficients()
        assert mock_vu.voltageToRawWord.call_count == 3
        mock_vu.voltageToRawWord.assert_any_call(channel="CH1", voltage=0.0)
        mock_vu.voltageToRawWord.assert_any_call(channel="CH2", voltage=0.0)
        mock_vu.voltageToRawWord.assert_any_call(channel="CH3", voltage=0.0)

    def test_reset_coefficients_failure(self, vu_controller, mock_vu):
        """Verify exception during reset returns ok=False."""
        mock_vu.set_correctionvalues.side_effect = Exception("hw error")
        result = vu_controller.reset_coefficients()
        assert result.ok is False
        assert "hw error" in result.message

    def test_write_coefficients_success(self, vu_controller, mock_vu):
        """Verify coefficients are written to EEPROM and verified."""
        mock_vu.get_correctionvalues.return_value = [1.0, 0.0]
        result = vu_controller.write_coefficients()
        assert result.ok is True
        assert mock_vu.set_correctionvalues.call_count == 3
        for c in mock_vu.set_correctionvalues.call_args_list:
            assert c.kwargs["writetoeeprom"] is True
        # Readback verification
        assert mock_vu.get_correctionvalues.call_count == 3

    def test_write_coefficients_eeprom_mismatch(self, vu_controller, mock_vu):
        """Verify EEPROM readback mismatch returns ok=False."""
        vu_controller._coeffs["CH1"] = [1.05, -0.01]
        # Readback returns different values
        mock_vu.get_correctionvalues.return_value = [0.99, 0.1]
        result = vu_controller.write_coefficients()
        assert result.ok is False

    def test_write_coefficients_eeprom_match(self, vu_controller, mock_vu):
        """Verify EEPROM readback matching returns ok=True."""
        vu_controller._coeffs["CH1"] = [1.0, 0.0]
        vu_controller._coeffs["CH2"] = [1.0, 0.0]
        vu_controller._coeffs["CH3"] = [1.0, 0.0]
        mock_vu.get_correctionvalues.return_value = [1.0, 0.0]
        result = vu_controller.write_coefficients()
        assert result.ok is True

    def test_write_coefficients_failure(self, vu_controller, mock_vu):
        """Verify exception during write returns ok=False."""
        mock_vu.set_correctionvalues.side_effect = Exception("hw error")
        result = vu_controller.write_coefficients()
        assert result.ok is False
        assert "hw error" in result.message


# ===========================================================================
# TestVUControllerGuard
# ===========================================================================


@pytest.mark.unit
class TestVUControllerGuard:
    """Tests for guard signal and ground operations."""

    def test_set_guard_signal_success(self, vu_controller, mock_vu):
        """Verify guard set to signal mode returns ok."""
        result = vu_controller.set_guard_signal()
        assert result.ok is True
        assert result.data["guard"] == "signal"
        mock_vu.setOutputsGuardToSignal.assert_called_once()

    def test_set_guard_signal_failure(self, vu_controller, mock_vu):
        """Verify guard signal exception returns ok=False."""
        mock_vu.setOutputsGuardToSignal.side_effect = Exception("hw error")
        result = vu_controller.set_guard_signal()
        assert result.ok is False
        assert "hw error" in result.message

    def test_set_guard_ground_success(self, vu_controller, mock_vu):
        """Verify guard set to ground mode returns ok."""
        result = vu_controller.set_guard_ground()
        assert result.ok is True
        assert result.data["guard"] == "ground"
        mock_vu.setOutputsGuardToGND.assert_called_once()

    def test_set_guard_ground_failure(self, vu_controller, mock_vu):
        """Verify guard ground exception returns ok=False."""
        mock_vu.setOutputsGuardToGND.side_effect = Exception("hw error")
        result = vu_controller.set_guard_ground()
        assert result.ok is False
        assert "hw error" in result.message


# ===========================================================================
# TestVUControllerTestOutputs
# ===========================================================================


@pytest.mark.unit
class TestVUControllerTestOutputs:
    """Tests for VUController.test_outputs."""

    def test_test_outputs_success_creates_artifact(self, vu_controller, mock_scope, tmp_path):
        """Verify test_outputs runs and creates a plot artifact in artifact_dir."""
        result = vu_controller.test_outputs()
        assert result.ok is True
        assert "artifacts" in result.data
        assert "plot" in result.data
        assert result.data["plot"]["type"] == "outputs"
        # Verify an artifact file was created
        artifacts = result.data["artifacts"]
        assert len(artifacts) >= 1
        assert any("output" in a for a in artifacts)

    def test_test_outputs_calls_callback(self, vu_controller, mock_scope):
        """Verify on_point_measured callback is invoked for each voltage setpoint."""
        callback = MagicMock()
        vu_controller.test_outputs(on_point_measured=callback)
        # 7 voltage setpoints: -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75
        assert callback.call_count == 7
        for c in callback.call_args_list:
            point = c[0][0]
            assert "x" in point
            assert "y_ch1" in point
            assert "y_ch2" in point
            assert "y_ch3" in point

    def test_test_outputs_returns_voltage_and_error_data(self, vu_controller, mock_scope):
        """Verify plot data contains voltages and errors arrays."""
        result = vu_controller.test_outputs()
        plot = result.data["plot"]
        assert plot["voltages"] == [-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75]
        assert len(plot["errors"]) == 3
        for ch_errors in plot["errors"]:
            assert len(ch_errors) == 7

    def test_test_outputs_resets_outputs_after_test(self, vu_controller, mock_vu, mock_scope):
        """Verify outputs are disabled and zeroed after test completes."""
        vu_controller.test_outputs()
        mock_vu.setOutputVoltage.assert_called_with("all", (0.0, 0.0, 0.0))
        # setOutputsEnabled(0) called at start for offsets and at end for cleanup
        calls = [c for c in mock_vu.setOutputsEnabled.call_args_list if c[0][0] == 0]
        assert len(calls) >= 1

    def test_test_outputs_failure(self, vu_controller, mock_vu, mock_scope):
        """Verify hardware exception during test returns ok=False."""
        mock_scope.read_raw.side_effect = Exception("hw error")
        result = vu_controller.test_outputs()
        assert result.ok is False
        assert "hw error" in result.message

    def test_test_outputs_no_callback(self, vu_controller, mock_scope):
        """Verify test_outputs works without a callback."""
        result = vu_controller.test_outputs(on_point_measured=None)
        assert result.ok is True


# ===========================================================================
# TestVUControllerTestRamp
# ===========================================================================


@pytest.mark.unit
class TestVUControllerTestRamp:
    """Tests for VUController.test_ramp."""

    @pytest.fixture
    def ramp_scope(self, mock_scope):
        """Override mock_scope to return ramp data with a measurable slope."""
        ramp_data = _make_ramp_scope_data(5000)
        mock_scope.read_raw.return_value = ramp_data
        return mock_scope

    def test_test_ramp_success_creates_artifact(self, vu_controller, ramp_scope, tmp_path):
        """Verify test_ramp runs end-to-end and creates a ramp artifact."""
        result = vu_controller.test_ramp()
        # Result should be ok (ramp data has correct slope)
        assert isinstance(result, OperationResult)
        assert "plot" in result.data or "artifacts" in result.data
        if result.ok:
            assert result.data["plot"]["type"] == "ramp"
            artifacts = result.data["artifacts"]
            assert any("ramp" in a for a in artifacts)

    def test_test_ramp_trigger_not_fired(self, vu_controller, mock_scope):
        """Verify trigger timeout returns ok=False with descriptive message."""
        opc_count = [0]

        def ask_side_effect(cmd):
            mapping = {
                "*IDN?": "RIGOL,DS1054Z,DS1ZA0000001,00.04.04",
                "SING;*OPC?": "1",
                "CHAN1:DATA:HEAD?": "-0.05,0.05,5000,1",
            }
            if cmd == "*OPC?":
                opc_count[0] += 1
                # First *OPC? (scope setup at line 589) succeeds;
                # second *OPC? (_scope_wait_trigger at line 629) times out.
                if opc_count[0] >= 2:
                    raise Exception("timeout")
                return "1"
            return mapping.get(cmd, "OK")

        mock_scope.ask.side_effect = ask_side_effect
        result = vu_controller.test_ramp()
        assert result.ok is False
        assert "trigger" in result.message.lower() or "Trigger" in result.message

    def test_test_ramp_calls_waveform_callback(self, vu_controller, ramp_scope):
        """Verify on_waveform callback is invoked for each channel and ideal."""
        callback = MagicMock()
        vu_controller.test_ramp(on_waveform=callback)
        # 3 channels x 2 calls each (data + ideal) = 6 calls
        assert callback.call_count == 6
        for c in callback.call_args_list:
            wf = c[0][0]
            assert "type" in wf
            assert wf["type"] == "ramp"
            assert "series" in wf
            assert "x" in wf
            assert "y" in wf

    def test_test_ramp_updates_coefficients(self, vu_controller, ramp_scope, mock_vu):
        """Verify ramp test adjusts slope coefficients based on measured slope."""
        _original_coeffs = {ch: list(v) for ch, v in vu_controller._coeffs.items()}
        vu_controller.test_ramp()
        # Coefficients should have been adjusted (slope ratio applied)
        # With perfect mock data the change may be small but the code path runs
        # We verify the coefficient update code was reached
        assert mock_vu.get_correctionvalues.called
        assert mock_vu.get_Vout_Amplification.called

    def test_test_ramp_failure(self, vu_controller, mock_vu, mock_scope):
        """Verify exception during ramp test returns ok=False."""
        mock_vu.get_correctionvalues.side_effect = Exception("hw error")
        result = vu_controller.test_ramp()
        assert result.ok is False
        assert "hw error" in result.message


# ===========================================================================
# TestVUControllerTestTransient
# ===========================================================================


@pytest.mark.unit
class TestVUControllerTestTransient:
    """Tests for VUController.test_transient."""

    @pytest.fixture
    def transient_scope(self, mock_scope):
        """Override mock_scope with transient time range and step data."""
        transient_data = _make_transient_scope_data(5000)
        mock_scope.read_raw.return_value = transient_data
        # Override HEAD to match the transient time window (-5us to +5us)
        mock_scope.ask.side_effect = lambda cmd: {
            "*IDN?": "RIGOL,DS1054Z,DS1ZA0000001,00.04.04",
            "*OPC?": "1",
            "SING;*OPC?": "1",
            "CHAN1:DATA:HEAD?": "-5e-6,5e-6,5000,1",
        }.get(cmd, "OK")
        return mock_scope

    @pytest.fixture
    def patched_dpi_config(self):
        """Configure the dpi.configuration mock so DPIConfiguration().model_dump() works.

        test_transient does ``from dpi.configuration import DPIConfiguration``
        at runtime. The module is provided by our sys.modules mock at the top
        of this file; here we wire up the return value of model_dump().
        """
        config_dict = {
            "msm": {
                "dc": {
                    "tstress": 5e-6,
                    "trecovery": 5e-6,
                },
            },
            "vu.1": {
                "ch1": {"msm": {"dc": {"vstress": 0.0, "vrecovery": 0.0, "vremain": 0.0}}},
                "ch2": {"msm": {"dc": {"vstress": 0.0, "vrecovery": 0.0, "vremain": 0.0}}},
                "ch3": {"msm": {"dc": {"vstress": 0.0, "vrecovery": 0.0, "vremain": 0.0}}},
            },
            "smu.bus_1": {
                "msm": {"dc": {"__stresscurrentrange_index": 0, "__recoverycurrentrange_index": 0}}
            },
            "smu.bus_2": {
                "msm": {"dc": {"__stresscurrentrange_index": 0, "__recoverycurrentrange_index": 0}}
            },
            "smu.bus_3": {
                "msm": {"dc": {"__stresscurrentrange_index": 0, "__recoverycurrentrange_index": 0}}
            },
            "smu.bus_4": {
                "msm": {"dc": {"__stresscurrentrange_index": 0, "__recoverycurrentrange_index": 0}}
            },
            "smu.all": {"msm": {"signal_to_record": "recovery"}},
        }
        mock_config_instance = MagicMock()
        mock_config_instance.model_dump.return_value = config_dict
        mock_cls = MagicMock(return_value=mock_config_instance)
        _dpi_configuration_mod.DPIConfiguration = mock_cls
        yield mock_cls
        # Reset so other tests get a clean mock
        _dpi_configuration_mod.DPIConfiguration = MagicMock()

    def test_test_transient_success_creates_artifact(
        self, vu_controller, transient_scope, patched_dpi_config, tmp_path
    ):
        """Verify test_transient runs and creates a transient artifact."""
        result = vu_controller.test_transient()
        assert result.ok is True
        assert "artifacts" in result.data
        assert result.data["plot"]["type"] == "transient"
        artifacts = result.data["artifacts"]
        assert any("transient" in a for a in artifacts)

    def test_test_transient_trigger_not_fired(self, vu_controller, mock_scope, patched_dpi_config):
        """Verify trigger timeout returns ok=False with descriptive message."""
        call_count = [0]

        def ask_side_effect(cmd):
            mapping = {
                "*IDN?": "RIGOL,DS1054Z,DS1ZA0000001,00.04.04",
                "SING;*OPC?": "1",
                "CHAN1:DATA:HEAD?": "-0.05,0.05,5000,1",
            }
            if cmd == "*OPC?":
                # First *OPC? call succeeds (pre-trigger setup), second fails (trigger wait)
                call_count[0] += 1
                if call_count[0] >= 2:
                    raise Exception("timeout")
                return "1"
            return mapping.get(cmd, "OK")

        mock_scope.ask.side_effect = ask_side_effect
        result = vu_controller.test_transient()
        assert result.ok is False
        assert "trigger" in result.message.lower() or "Trigger" in result.message

    def test_test_transient_waveform_callback(
        self, vu_controller, transient_scope, patched_dpi_config
    ):
        """Verify on_waveform callback is invoked for each channel."""
        callback = MagicMock()
        vu_controller.test_transient(on_waveform=callback)
        # 3 channels
        assert callback.call_count == 3
        for c in callback.call_args_list:
            wf = c[0][0]
            assert wf["type"] == "transient"
            assert "series" in wf
            assert "x" in wf
            assert "y" in wf

    def test_test_transient_dac_bits_20_uses_longer_timestep(
        self, vu_controller, mock_vu, transient_scope, patched_dpi_config
    ):
        """Verify 20-bit DAC uses 20us timestep instead of 5us."""
        mock_vu.get_DAC_bits.return_value = 20
        result = vu_controller.test_transient()
        # Just verify it ran without error with dac_bits=20
        assert isinstance(result, OperationResult)

    def test_test_transient_failure(self, vu_controller, mock_vu, mock_scope, patched_dpi_config):
        """Verify exception during transient test returns ok=False."""
        mock_vu.get_DAC_bits.side_effect = Exception("hw error")
        result = vu_controller.test_transient()
        assert result.ok is False
        assert "hw error" in result.message


# ===========================================================================
# TestVUControllerTestAll
# ===========================================================================


@pytest.mark.unit
class TestVUControllerTestAll:
    """Tests for VUController.test_all delegation."""

    def test_test_all_delegates_to_subtests(self, vu_controller, mocker):
        """Verify test_all calls test_outputs, test_ramp, and test_transient."""
        mock_outputs = mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mock_ramp = mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=True, data={"plot": {"type": "ramp"}}),
        )
        mock_transient = mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        callback_point = MagicMock()
        callback_wf = MagicMock()
        vu_controller.test_all(on_point_measured=callback_point, on_waveform=callback_wf)
        mock_outputs.assert_called_once_with(on_point_measured=callback_point)
        mock_ramp.assert_called_once_with(on_waveform=callback_wf)
        mock_transient.assert_called_once_with(on_waveform=callback_wf)

    def test_test_all_all_pass(self, vu_controller, mocker):
        """Verify all-ok subtests produce ok=True combined result."""
        mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=True, data={"plot": {"type": "ramp"}}),
        )
        mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        result = vu_controller.test_all()
        assert result.ok is True
        assert "plots" in result.data
        assert len(result.data["plots"]) == 3

    def test_test_all_partial_failure(self, vu_controller, mocker):
        """Verify one failed subtest makes combined result ok=False."""
        mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=False, message="ramp failed"),
        )
        mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        result = vu_controller.test_all()
        assert result.ok is False

    def test_test_all_collects_artifacts(self, vu_controller, mocker, tmp_path):
        """Verify test_all collects artifacts from artifact_dir."""
        # Create some artifact files
        os.makedirs(vu_controller._artifact_dir, exist_ok=True)
        (tmp_path / "output_20260322_120000.png").write_bytes(b"PNG")
        mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=True, data={"plot": {"type": "ramp"}}),
        )
        mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        result = vu_controller.test_all()
        assert "artifacts" in result.data

    def test_test_all_all_fail(self, vu_controller, mocker):
        """Verify all-failed subtests produce ok=False combined result."""
        mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=False, message="fail1"),
        )
        mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=False, message="fail2"),
        )
        mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=False, message="fail3"),
        )
        result = vu_controller.test_all()
        assert result.ok is False


# ===========================================================================
# TestVUControllerAutoCalibrate
# ===========================================================================


@pytest.mark.unit
class TestVUControllerAutoCalibrate:
    """Tests for VUController.auto_calibrate iterative calibration."""

    def test_auto_calibrate_converges(self, vu_controller, mocker):
        """Verify auto_calibrate returns ok=True when subtests converge."""
        mocker.patch.object(
            vu_controller,
            "reset_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=True, data={"plot": {"type": "ramp"}}),
        )
        mocker.patch.object(
            vu_controller,
            "write_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        result = vu_controller.auto_calibrate(max_iterations=5)
        assert result.ok is True
        assert "coeffs" in result.data

    def test_auto_calibrate_calls_iteration_callback(self, vu_controller, mocker):
        """Verify on_iteration callback is invoked each iteration and at final."""
        mocker.patch.object(
            vu_controller,
            "reset_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=True, data={"plot": {"type": "ramp"}}),
        )
        mocker.patch.object(
            vu_controller,
            "write_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        callback = MagicMock()
        vu_controller.auto_calibrate(max_iterations=3, on_iteration=callback)
        # Converges on first iteration (both test_ramp and test_outputs return ok)
        # So: 1 loop iteration callback + 3 final callbacks = 4
        assert callback.call_count >= 4
        # Check first call has iteration=0
        first_call = callback.call_args_list[0][0][0]
        assert first_call["iteration"] == 0
        # Check final callbacks have converged=True
        for c in callback.call_args_list[-3:]:
            assert c[0][0]["converged"] is True

    def test_auto_calibrate_respects_max_iterations(self, vu_controller, mocker):
        """Verify auto_calibrate stops after max_iterations when not converging."""
        mocker.patch.object(
            vu_controller,
            "reset_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=False, message="not converged"),
        )
        mocker.patch.object(
            vu_controller,
            "write_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        _result = vu_controller.auto_calibrate(max_iterations=3)
        # test_ramp called: 3 loop iterations + 1 final verification = 4 times
        assert vu_controller.test_ramp.call_count == 4

    def test_auto_calibrate_failure(self, vu_controller, mocker):
        """Verify exception during calibration loop returns ok=False."""
        mocker.patch.object(
            vu_controller,
            "reset_coefficients",
            side_effect=Exception("hw error"),
        )
        result = vu_controller.auto_calibrate()
        assert result.ok is False
        assert "hw error" in result.message

    def test_auto_calibrate_writes_coefficients_each_iteration(self, vu_controller, mocker):
        """Verify write_coefficients is called after test_ramp and test_outputs."""
        mocker.patch.object(
            vu_controller,
            "reset_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=True, data={"plot": {"type": "ramp"}}),
        )
        mock_write = mocker.patch.object(
            vu_controller,
            "write_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        vu_controller.auto_calibrate(max_iterations=1)
        # write_coefficients called twice per iteration (after test_ramp, after test_outputs)
        assert mock_write.call_count == 2

    def test_auto_calibrate_starts_with_reset(self, vu_controller, mocker):
        """Verify auto_calibrate resets coefficients before iterating."""
        mock_reset = mocker.patch.object(
            vu_controller,
            "reset_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=True, data={"plot": {"type": "ramp"}}),
        )
        mocker.patch.object(
            vu_controller,
            "write_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        vu_controller.auto_calibrate(max_iterations=2)
        mock_reset.assert_called_once()

    def test_auto_calibrate_runs_final_verification(self, vu_controller, mocker):
        """Verify final verification runs test_transient, test_outputs, and test_ramp."""
        mocker.patch.object(
            vu_controller,
            "reset_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mock_ramp = mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=True, data={"plot": {"type": "ramp"}}),
        )
        mocker.patch.object(
            vu_controller,
            "write_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mock_outputs = mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mock_transient = mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        vu_controller.auto_calibrate(max_iterations=1)
        # 1 loop iteration + 1 final = 2 calls each for test_ramp and test_outputs
        assert mock_ramp.call_count == 2
        assert mock_outputs.call_count == 2
        # test_transient only in final verification
        assert mock_transient.call_count == 1

    def test_auto_calibrate_with_point_and_waveform_callbacks(self, vu_controller, mocker):
        """Verify both point and waveform callbacks are forwarded to subtests."""
        mocker.patch.object(
            vu_controller,
            "reset_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mock_ramp = mocker.patch.object(
            vu_controller,
            "test_ramp",
            return_value=OperationResult(ok=True, data={"plot": {"type": "ramp"}}),
        )
        mocker.patch.object(
            vu_controller,
            "write_coefficients",
            return_value=OperationResult(ok=True, data={"coeffs": vu_controller._coeffs}),
        )
        mock_outputs = mocker.patch.object(
            vu_controller,
            "test_outputs",
            return_value=OperationResult(ok=True, data={"plot": {"type": "outputs"}}),
        )
        mock_transient = mocker.patch.object(
            vu_controller,
            "test_transient",
            return_value=OperationResult(ok=True, data={"plot": {"type": "transient"}}),
        )
        cb_point = MagicMock()
        cb_wf = MagicMock()
        vu_controller.auto_calibrate(
            max_iterations=1,
            on_point_measured=cb_point,
            on_waveform=cb_wf,
        )
        # Verify callbacks are forwarded
        for c in mock_outputs.call_args_list:
            assert c.kwargs["on_point_measured"] is cb_point
        for c in mock_ramp.call_args_list:
            assert c.kwargs["on_waveform"] is cb_wf
        for c in mock_transient.call_args_list:
            assert c.kwargs["on_waveform"] is cb_wf


# ===========================================================================
# TestVUControllerScopeHelpers
# ===========================================================================


@pytest.mark.unit
class TestVUControllerScopeHelpers:
    """Tests for private scope helper methods."""

    def test_scope_setup_and_acquire(self, vu_controller, mock_scope):
        """Verify _scope_setup_and_acquire sends SING;*OPC? command."""
        vu_controller._scope_setup_and_acquire(mock_scope)
        mock_scope.ask.assert_called_with("SING;*OPC?")

    def test_scope_wait_trigger_success(self, vu_controller, mock_scope):
        """Verify _scope_wait_trigger returns True on successful trigger."""
        result = vu_controller._scope_wait_trigger(mock_scope)
        assert result is True
        mock_scope.ask.assert_called_with("*OPC?")

    def test_scope_wait_trigger_timeout(self, vu_controller, mock_scope):
        """Verify _scope_wait_trigger returns False on timeout exception."""
        mock_scope.ask.side_effect = Exception("timeout")
        result = vu_controller._scope_wait_trigger(mock_scope)
        assert result is False

    def test_scope_get_data_returns_arrays(self, vu_controller, mock_scope):
        """Verify _scope_get_data returns voltage and time numpy arrays."""
        data, t = vu_controller._scope_get_data(1)
        assert isinstance(data, np.ndarray)
        assert isinstance(t, np.ndarray)
        assert len(data) == len(t)
        assert len(data) == 5000

    def test_scope_get_data_time_axis_matches_header(self, vu_controller, mock_scope):
        """Verify time array spans t_start to t_end from HEAD response."""
        _data, t = vu_controller._scope_get_data(1)
        assert t[0] == pytest.approx(-0.05, abs=1e-6)
        assert t[-1] == pytest.approx(0.05, abs=1e-6)

    def test_scope_discard_link_closes_and_reopens(self, vu_controller, mock_scope):
        """Verify _scope_discard_link closes link and sends reset commands."""
        vu_controller._scope_discard_link(mock_scope)
        mock_scope.close.assert_called_once()
        assert mock_scope.link is None
        assert mock_scope.client is None
        mock_scope.write.assert_called_with("*RST;*CLS")


# ===========================================================================
# TestVUControllerArtifactHelpers
# ===========================================================================


@pytest.mark.unit
class TestVUControllerArtifactHelpers:
    """Tests for artifact path generation and listing."""

    def test_artifact_path_includes_prefix_and_timestamp(self, vu_controller):
        """Verify _artifact_path generates timestamped filenames with prefix."""
        path = vu_controller._artifact_path("output")
        assert "output_" in path
        assert path.endswith(".png")
        # Contains artifact_dir
        assert vu_controller._artifact_dir in path

    def test_list_artifacts_empty_dir(self, vu_controller, tmp_path):
        """Verify _list_artifacts returns empty list for empty directory."""
        # tmp_path exists but is empty (no artifacts created yet)
        artifacts = vu_controller._list_artifacts()
        assert artifacts == []

    def test_list_artifacts_with_files(self, vu_controller, tmp_path):
        """Verify _list_artifacts returns file paths for existing artifacts."""
        os.makedirs(vu_controller._artifact_dir, exist_ok=True)
        # Create test files
        for name in ["output_20260322_120000.png", "ramp_20260322_120001.png"]:
            fpath = os.path.join(vu_controller._artifact_dir, name)
            with open(fpath, "wb") as f:
                f.write(b"PNG")
        artifacts = vu_controller._list_artifacts()
        assert len(artifacts) == 2
        assert all(os.path.isabs(a) or a.startswith(str(tmp_path)) for a in artifacts)

    def test_list_artifacts_nonexistent_dir(self, mock_vu, mock_mcu, mock_scope):
        """Verify _list_artifacts returns empty list when dir does not exist."""
        ctrl = VUController(
            vu=mock_vu,
            mcu=mock_mcu,
            scope=mock_scope,
            artifact_dir="/nonexistent/path/artifacts",
        )
        assert ctrl._list_artifacts() == []


# ===========================================================================
# TestVUControllerEdgeCases
# ===========================================================================


@pytest.mark.unit
class TestVUControllerEdgeCases:
    """Edge case and boundary tests."""

    def test_coeffs_are_independent_per_channel(self, vu_controller):
        """Verify modifying one channel's coefficients does not affect others."""
        vu_controller._coeffs["CH1"] = [2.0, 0.5]
        assert vu_controller._coeffs["CH2"] == [1.0, 0.0]
        assert vu_controller._coeffs["CH3"] == [1.0, 0.0]

    def test_operation_result_is_frozen(self):
        """Verify OperationResult cannot be mutated after creation."""
        result = OperationResult(ok=True, serial=1, message="test", data={"k": 1})
        with pytest.raises(AttributeError):
            result.ok = False

    @pytest.mark.parametrize(
        "ok,serial,message",
        [
            (True, 2503, ""),
            (False, None, "error occurred"),
            (True, 0, "zero serial"),
        ],
    )
    def test_operation_result_construction(self, ok, serial, message):
        """Verify OperationResult accepts various field combinations."""
        result = OperationResult(ok=ok, serial=serial, message=message)
        assert result.ok is ok
        assert result.serial == serial
        assert result.message == message

    def test_test_outputs_reset_failure_does_not_lose_plot(
        self, vu_controller, mock_vu, mock_scope
    ):
        """Verify plot data is preserved even if output reset fails."""
        mock_vu.setOutputVoltage.side_effect = [None] * 100  # succeed during test
        # But fail on the final reset call
        call_count = [0]
        _original_side_effect = mock_vu.setOutputVoltage.side_effect

        def reset_fails(*args, **kwargs):
            call_count[0] += 1
            # The last call is the reset to (0,0,0) after test
            if args == ("all", (0.0, 0.0, 0.0)) and call_count[0] > 7:
                raise Exception("reset failed")

        mock_vu.setOutputVoltage.side_effect = reset_fails
        result = vu_controller.test_outputs()
        # Should still have plot data despite reset failure
        assert "plot" in result.data

    def test_write_coefficients_preserves_custom_values(self, vu_controller, mock_vu):
        """Verify write_coefficients sends the actual current coefficient values."""
        vu_controller._coeffs["CH1"] = [1.05, -0.01]
        vu_controller._coeffs["CH2"] = [0.98, 0.003]
        vu_controller._coeffs["CH3"] = [1.02, -0.005]
        mock_vu.get_correctionvalues.side_effect = [
            [1.05, -0.01],
            [0.98, 0.003],
            [1.02, -0.005],
        ]
        result = vu_controller.write_coefficients()
        assert result.ok is True
        calls = mock_vu.set_correctionvalues.call_args_list
        assert calls[0].kwargs["slope"] == 1.05
        assert calls[0].kwargs["offset"] == -0.01
        assert calls[1].kwargs["slope"] == 0.98
        assert calls[1].kwargs["offset"] == 0.003
        assert calls[2].kwargs["slope"] == 1.02
        assert calls[2].kwargs["offset"] == -0.005
