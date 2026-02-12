"""Hardware mock fixtures for testing services without real hardware.

This module provides a unified mocking infrastructure for all hardware services
(VU, SMU, SU) following DRY principles with a factory-based approach.

The mocks are structured in layers:
1. Base fixtures: Common subprocess/artifact mocking
2. Device-specific fixtures: Mock hardware classes per service

Usage:
    def test_vu_method(mock_vu_hardware):
        service = VoltageUnitService()
        ...

    def test_smu_method(mock_smu_hardware):
        service = SourceMeasureUnitService()
        ...
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.logic.controllers.base_controller import OperationResult

# =============================================================================
# BASE MOCK FACTORIES (DRY - reused by all services)
# =============================================================================


def create_mock_device(device_type: str) -> MagicMock:
    """Factory to create mock device objects with common interface.

    Args:
        device_type: One of 'vu', 'mcu', 'smu', 'su', 'scope'.

    Returns:
        Configured MagicMock for the device type.
    """
    mock = MagicMock()

    # Common methods across devices
    mock.get_serial.return_value = 1
    mock.getSerial.return_value = 1  # SU uses different naming

    # Device-specific defaults
    if device_type == "vu":
        mock.get_correctionvalues.return_value = [1.0, 0.0]
        mock.get_Vout_Amplification.return_value = 1.0
        mock.get_DAC_bits.return_value = 16
    elif device_type == "scope":
        mock.ask.return_value = "RIGOL,DS1054Z,*"
    elif device_type == "smu":
        mock.get_serial.return_value = 1
    elif device_type == "su":
        mock.getSerial.return_value = 1

    return mock


def create_artifact_mocks(mocker, tmp_path: Path, prefix: str = "vu") -> Path:
    """Create mock artifact directory with test files.

    Args:
        mocker: pytest-mock fixture.
        tmp_path: Temporary directory from pytest.
        prefix: Artifact prefix ('vu', 'smu', 'su').

    Returns:
        Path to created artifact directory.
    """
    artifact_dir = tmp_path / f"calibration_{prefix}1"
    artifact_dir.mkdir(exist_ok=True)

    # Create common artifact files
    for name in ["output.png", "ramp.png", "transient.png"]:
        (artifact_dir / name).write_bytes(b"PNG_MOCK")

    return artifact_dir


def patch_subprocess(mocker):
    """Patch subprocess calls used by all services for ping and lsusb."""
    mocker.patch("subprocess.check_call")  # ping
    mocker.patch(
        "subprocess.check_output",
        return_value="iSerial 3 s0001i01\n",  # Fake lsusb output
    )


def patch_artifact_manager(mocker, artifact_dir: Path):
    """Patch ArtifactManager for all services."""
    artifact_files = [str(f) for f in artifact_dir.glob("*.png")]

    # Patch at each service's import location
    for service_module in [
        "src.logic.services.vu_service",
        "src.logic.services.smu_service",
        "src.logic.services.su_service",
    ]:
        mocker.patch(
            f"{service_module}.ArtifactManager.get_artifact_dir",
            return_value=str(artifact_dir),
        )
        mocker.patch(
            f"{service_module}.ArtifactManager.collect_artifacts",
            return_value=artifact_files,
        )


# =============================================================================
# VOLTAGE UNIT SERVICE FIXTURES
# =============================================================================


@pytest.fixture
def mock_vu_hardware(mocker, tmp_path) -> dict[str, Any]:
    """Complete mock for VoltageUnitService testing.

    Patches:
        - DPIVoltageUnit, DPIMainControlUnit, vxi11.Instrument
        - setup_cal module functions
        - subprocess (ping/lsusb)
        - ArtifactManager

    Returns:
        Dict with mock objects for test assertions.
    """
    # Create device mocks
    mock_vu = create_mock_device("vu")
    mock_mcu = create_mock_device("mcu")
    mock_scope = create_mock_device("scope")

    # Patch hardware classes
    mocker.patch(
        "src.logic.services.vu_service.DPIVoltageUnit",
        return_value=mock_vu,
    )
    mocker.patch(
        "src.logic.services.vu_service.DPIMainControlUnit",
        return_value=mock_mcu,
    )
    mocker.patch(
        "src.logic.services.vu_service.vxi11.Instrument",
        return_value=mock_scope,
    )

    # Patch VUController so _ensure_connected creates a mock controller
    mock_controller = MagicMock()
    mock_controller.coeffs = {
        "CH1": [1.0, 0.0],
        "CH2": [1.0, 0.0],
        "CH3": [1.0, 0.0],
    }
    mock_controller.test_outputs.return_value = OperationResult(ok=True)
    mock_controller.test_ramp.return_value = OperationResult(ok=True)
    mock_controller.test_transient.return_value = OperationResult(ok=True)
    mock_controller.test_all.return_value = OperationResult(ok=True)
    mock_controller.auto_calibrate.return_value = OperationResult(
        ok=True, data={"coeffs": mock_controller.coeffs}
    )
    mock_controller.perform_autocalibration.return_value = OperationResult(ok=True)
    mock_controller.read_coefficients.return_value = OperationResult(
        ok=True, data={"coeffs": mock_controller.coeffs}
    )
    mock_controller.set_guard_signal.return_value = OperationResult(ok=True)
    mock_controller.set_guard_ground.return_value = OperationResult(ok=True)
    mock_controller.reset_coefficients.return_value = OperationResult(ok=True)
    mock_controller.write_coefficients.return_value = OperationResult(ok=True)
    mocker.patch(
        "src.logic.services.vu_service.VUController",
        return_value=mock_controller,
    )

    # Common infrastructure
    patch_subprocess(mocker)
    artifact_dir = create_artifact_mocks(mocker, tmp_path, "vu")
    patch_artifact_manager(mocker, artifact_dir)

    return {
        "vu": mock_vu,
        "mcu": mock_mcu,
        "scope": mock_scope,
        "artifact_dir": artifact_dir,
    }


# =============================================================================
# SOURCE MEASURE UNIT SERVICE FIXTURES
# =============================================================================


@pytest.fixture
def mock_smu_hardware(mocker, tmp_path) -> dict[str, Any]:
    """Complete mock for SourceMeasureUnitService testing.

    Patches:
        - DPISourceMeasureUnit
        - SMU calibration modules
        - subprocess (ping/lsusb)
        - ArtifactManager

    Returns:
        Dict with mock objects for test assertions.
    """
    # Create device mock
    mock_smu = create_mock_device("smu")

    # Patch hardware class at service import location
    mocker.patch(
        "src.logic.services.smu_service.DPISourceMeasureUnit",
        return_value=mock_smu,
    )

    # Mock calibration modules (imported dynamically in service)
    mock_cal_measure = MagicMock()
    mock_cal_fit = MagicMock()
    mocker.patch.dict(
        "sys.modules",
        {
            "dpisourcemeasureunit.calibration": MagicMock(
                SMUCalibrationMeasure=mock_cal_measure,
                SMUCalibrationFit=mock_cal_fit,
            ),
        },
    )

    # Common infrastructure
    patch_subprocess(mocker)
    artifact_dir = create_artifact_mocks(mocker, tmp_path, "smu")
    patch_artifact_manager(mocker, artifact_dir)

    return {
        "smu": mock_smu,
        "calibration_measure": mock_cal_measure,
        "calibration_fit": mock_cal_fit,
        "artifact_dir": artifact_dir,
    }


# =============================================================================
# SAMPLING UNIT SERVICE FIXTURES
# =============================================================================


@pytest.fixture
def mock_su_hardware(mocker, tmp_path) -> dict[str, Any]:
    """Complete mock for SamplingUnitService testing.

    Patches:
        - DPISamplingUnit
        - SU calibration modules
        - subprocess (ping/lsusb)
        - ArtifactManager

    Returns:
        Dict with mock objects for test assertions.
    """
    # Create device mock
    mock_su = create_mock_device("su")

    # Patch hardware class at service import location
    mocker.patch(
        "src.logic.services.su_service.DPISamplingUnit",
        return_value=mock_su,
    )

    # Mock calibration modules (imported dynamically by controller)
    mock_cal_measure = MagicMock()
    mock_cal_fit = MagicMock()
    mocker.patch.dict(
        "sys.modules",
        {
            "src.logic.calibration": MagicMock(
                SUCalibrationMeasure=mock_cal_measure,
                SUCalibrationFit=mock_cal_fit,
            ),
        },
    )

    # Common infrastructure
    patch_subprocess(mocker)
    artifact_dir = create_artifact_mocks(mocker, tmp_path, "su")
    patch_artifact_manager(mocker, artifact_dir)

    return {
        "su": mock_su,
        "calibration_measure": mock_cal_measure,
        "calibration_fit": mock_cal_fit,
        "artifact_dir": artifact_dir,
    }
