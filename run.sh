#!/bin/bash
# run.sh - Unified startup script for HardwareGUI
# Activates DPI venv, installs dependencies, creates symlinks, runs app

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DPI_VENV="/measdata/dpi/venv/dpi"

echo "HardwareGUI Startup"
echo "==================="

# 1. Activate DPI venv
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$DPI_VENV/bin/activate" ]; then
        echo "[INFO] Activating DPI venv..."
        source "$DPI_VENV/bin/activate"
    else
        echo "[ERROR] DPI venv not found at: $DPI_VENV"
        echo "        Please ensure the DPI environment is set up."
        exit 1
    fi
elif [ "$VIRTUAL_ENV" != "$DPI_VENV" ]; then
    echo "[WARN] Different venv active: $VIRTUAL_ENV"
    echo "       Expected: $DPI_VENV"
    echo "       Continuing with current venv..."
fi

echo "[OK] Virtual environment: $VIRTUAL_ENV"

# 2. Install HardwareGUI dependencies (auto-install uv if needed)
install_deps() {
    local req_file="$PROJECT_ROOT/requirements-gui.txt"
    
    if [ ! -f "$req_file" ]; then
        echo "[WARN] requirements-gui.txt not found, skipping dependency check"
        return 0
    fi

    if command -v uv &> /dev/null; then
        echo "[INFO] Syncing dependencies via uv..."
        uv pip install -q -r "$req_file"
    else
        echo "[INFO] uv not found, attempting to install..."
        if curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null; then
            # Add uv to PATH for this session
            export PATH="$HOME/.local/bin:$PATH"
            if command -v uv &> /dev/null; then
                echo "[OK] uv installed successfully"
                uv pip install -q -r "$req_file"
            else
                echo "[WARN] uv install succeeded but not in PATH, using pip..."
                pip install -q -r "$req_file"
            fi
        else
            echo "[WARN] uv install failed, falling back to pip..."
            pip install -q -r "$req_file"
        fi
    fi
    echo "[OK] Dependencies synced"
}
install_deps

# 3. Create device script symlinks (idempotent)
create_symlinks() {
    local scripts_dir="$PROJECT_ROOT/src/device_scripts"
    mkdir -p "$scripts_dir"

    # Helper: create symlink if source exists
    link() {
        local src="$1" dst="$2"
        if [ -f "$src" ]; then
            ln -sf "$src" "$dst"
        fi
    }

    # Voltage Unit
    link "/measdata/dpi/voltageunit/python/dev/setup_cal.py" "$scripts_dir/setup_cal.py"

    # Source Measure Unit (SMU)
    link "/measdata/dpi/sourcemeasureunit/python/dev/hw_setup.py" "$scripts_dir/smu_hw_setup.py"
    link "/measdata/dpi/sourcemeasureunit/python/dev/dev.py" "$scripts_dir/smu_dev.py"
    link "/measdata/dpi/sourcemeasureunit/python/dev/calibration_measure.py" "$scripts_dir/smu_calibration_measure.py"
    link "/measdata/dpi/sourcemeasureunit/python/dev/calibration_fit.py" "$scripts_dir/smu_calibration_fit.py"

    # Sampling Unit (SU)
    link "/measdata/dpi/samplingunit/python/dev/hw_setup.py" "$scripts_dir/su_hw_setup.py"
    link "/measdata/dpi/samplingunit/python/dev/dev.py" "$scripts_dir/su_dev.py"
    link "/measdata/dpi/samplingunit/python/dev/calibration_measure.py" "$scripts_dir/su_calibration_measure.py"
    link "/measdata/dpi/samplingunit/python/dev/calibration_fit.py" "$scripts_dir/su_calibration_fit.py"

    echo "[OK] Device script symlinks ready"
}
create_symlinks

# 4. Set up environment and run
cd "$PROJECT_ROOT/src"
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src"
export PYTHONUNBUFFERED=1

echo ""
echo "Starting main.py..."
echo ""
python main.py "$@"
