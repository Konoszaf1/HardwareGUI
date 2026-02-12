"""Pytest configuration and shared fixtures for HardwareGUI tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# =============================================================================
# HARDWARE MODULE MOCKS
# =============================================================================
# These mocks must be installed BEFORE any imports that might trigger loading
# of hardware-specific modules (dpi, vxi11, etc.) which aren't available in
# the test environment.
# =============================================================================

# Create mock modules for hardware libraries
_hardware_mocks = {
    "dpi": MagicMock(),
    "dpi.measurement": MagicMock(),
    "dpi.utilities": MagicMock(),
    "dpi.utilities.pycrv": MagicMock(),
    "dpivoltageunit": MagicMock(),
    "dpivoltageunit.dpivoltageunit": MagicMock(),
    "dpimaincontrolunit": MagicMock(),
    "dpimaincontrolunit.dpimaincontrolunit": MagicMock(),
    "dpisourcemeasureunit": MagicMock(),
    "dpisourcemeasureunit.dpisourcemeasureunit": MagicMock(),
    "dpisamplingunit": MagicMock(),
    "dpisamplingunit.dpisamplingunit": MagicMock(),
    "vxi11": MagicMock(),
}

# Install mocks into sys.modules
for mod_name, mock_obj in _hardware_mocks.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock_obj

import pytest

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture
def temp_artifact_dir(tmp_path):
    """Create a temporary directory structure mimicking calibration artifacts.

    Creates:
        calibration_vu123/
            output.png
            ramp.png
            transient.png
            other_file.png

    Returns:
        Path to the temporary directory.
    """
    vu_dir = tmp_path / "calibration_vu123"
    vu_dir.mkdir()

    # Create test PNG files (priority files first)
    for name in ["output.png", "ramp.png", "transient.png", "other_file.png"]:
        (vu_dir / name).write_bytes(b"PNG_MOCK_DATA")

    return tmp_path


@pytest.fixture
def sample_actions():
    """Provide sample ActionDescriptor objects for model testing."""
    from src.logic.action_dataclass import ActionDescriptor

    return [
        ActionDescriptor(
            id=1,
            hardware_id=1,
            label="Session & Coeffs",
            page_id="workbench",
            order=0,
        ),
        ActionDescriptor(
            id=2,
            hardware_id=1,
            label="Calibration",
            page_id="calibration",
            order=1,
        ),
        ActionDescriptor(
            id=3,
            hardware_id=2,
            label="Other Device",
            page_id="other",
            order=0,
        ),
    ]
