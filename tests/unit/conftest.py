"""Unit-level conftest — no Qt event loop required.

Provides mock hardware objects for controller testing.
"""

from unittest.mock import MagicMock

import numpy as np
import pytest

from src.logic.controllers.base_controller import OperationResult


# ---------------------------------------------------------------------------
# Mock device factories
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_vu() -> MagicMock:
    """Create a mock DPIVoltageUnit with standard return values."""
    vu = MagicMock()
    vu.get_serial.return_value = 2503
    vu.get_temperature.return_value = 25.4
    vu.get_correctionvalues.return_value = [1.0, 0.0]
    vu.get_Vout_Amplification.return_value = -1.0
    vu.get_DAC_bits.return_value = 16
    vu.voltageToRawWord.return_value = 32768
    return vu


@pytest.fixture
def mock_mcu() -> MagicMock:
    """Create a mock DPIMainControlUnit."""
    mcu = MagicMock()
    mcu.get_serial.return_value = 100
    return mcu


@pytest.fixture
def mock_scope() -> MagicMock:
    """Create a mock vxi11.Instrument with realistic scope responses."""
    scope = MagicMock()
    scope.ask.return_value = "RIGOL,DS1054Z,DS1ZA0000001,00.04.04"

    # Build realistic binary waveform data for read_raw()
    n_points = 5000
    data = np.zeros(n_points, dtype=np.single)
    data_bytes = data.tobytes()
    # IEEE 488.2 definite-length block: #<num_digits><byte_count><data>
    len_str = str(len(data_bytes))
    header = f"#{len(len_str)}{len_str}".encode("utf-8")
    scope.read_raw.return_value = header + data_bytes

    # HEAD response: "t_start,t_end,n_points,values_per_interval"
    scope.ask.side_effect = lambda cmd: {
        "*IDN?": "RIGOL,DS1054Z,DS1ZA0000001,00.04.04",
        "*OPC?": "1",
        "SING;*OPC?": "1",
        "CHAN1:DATA:HEAD?": "-0.05,0.05,5000,1",
    }.get(cmd, "OK")

    return scope


@pytest.fixture(autouse=True)
def _patch_sleep(monkeypatch):
    """Eliminate hardware settling delays in unit tests."""
    monkeypatch.setattr("time.sleep", lambda _: None)


@pytest.fixture
def vu_controller(mock_vu, mock_mcu, mock_scope, tmp_path):
    """Create a VUController with mock hardware and temp artifact dir."""
    from src.logic.controllers.vu_controller import VUController

    return VUController(
        vu=mock_vu,
        mcu=mock_mcu,
        scope=mock_scope,
        vu_serial=2503,
        artifact_dir=str(tmp_path),
    )
