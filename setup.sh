#!/bin/bash
# setup.sh - One-time setup script for HardwareGUI

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "HardwareGUI Setup"
echo "=================="
echo ""

# Warn about existing virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo "[ERROR] You are currently in a virtual environment: $VIRTUAL_ENV"
    echo "        Please deactivate it first with: deactivate"
    echo "        Then run this script again."
    exit 1
fi

# Step 1: Check for uv
if ! command -v uv &> /dev/null; then
    echo "[ERROR] uv is not installed"
    echo ""
    echo "Install it with:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "Then run: source ~/.bashrc"
    echo "And run this script again."
    exit 1
fi
echo "[OK] uv found: $(uv --version)"
echo ""

# Step 2: Create device_scripts directory and symlinks
SCRIPTS_DIR="$PROJECT_ROOT/src/device_scripts"
mkdir -p "$SCRIPTS_DIR"

# Voltage Unit scripts
echo "Creating VU script symlinks..."
VU_DEV_DIR="/measdata/dpi/voltageunit/python/dev"
VU_SCRIPTS=("setup_cal.py:setup_cal.py")

for script_pair in "${VU_SCRIPTS[@]}"; do
    LINK_NAME="${script_pair%%:*}"
    SOURCE_NAME="${script_pair##*:}"
    SOURCE_PATH="$VU_DEV_DIR/$SOURCE_NAME"
    LINK_PATH="$SCRIPTS_DIR/$LINK_NAME"
    
    if [ -f "$SOURCE_PATH" ]; then
        [ -L "$LINK_PATH" ] || [ -f "$LINK_PATH" ] && rm -f "$LINK_PATH"
        ln -s "$SOURCE_PATH" "$LINK_PATH"
        echo "[OK] $LINK_NAME symlink created"
    else
        echo "[WARN] $SOURCE_NAME not found at $SOURCE_PATH"
    fi
done
echo ""

# SMU scripts
echo "Creating SMU script symlinks..."
SMU_DEV_DIR="/measdata/dpi/sourcemeasureunit/python/dev"
SMU_SCRIPTS=("smu_hw_setup.py:hw_setup.py" "smu_dev.py:dev.py" "smu_calibration_measure.py:calibration_measure.py" "smu_calibration_fit.py:calibration_fit.py")

for script_pair in "${SMU_SCRIPTS[@]}"; do
    LINK_NAME="${script_pair%%:*}"
    SOURCE_NAME="${script_pair##*:}"
    SOURCE_PATH="$SMU_DEV_DIR/$SOURCE_NAME"
    LINK_PATH="$SCRIPTS_DIR/$LINK_NAME"
    
    if [ -f "$SOURCE_PATH" ]; then
        [ -L "$LINK_PATH" ] || [ -f "$LINK_PATH" ] && rm -f "$LINK_PATH"
        ln -s "$SOURCE_PATH" "$LINK_PATH"
        echo "[OK] $LINK_NAME symlink created"
    else
        echo "[WARN] $SOURCE_NAME not found at $SOURCE_PATH"
    fi
done
echo ""

# SU (Sampling Unit) scripts
echo "Creating SU script symlinks..."
SU_DEV_DIR="/measdata/dpi/samplingunit/python/dev"
SU_SCRIPTS=("su_hw_setup.py:hw_setup.py" "su_dev.py:dev.py" "su_calibration_measure.py:calibration_measure.py" "su_calibration_fit.py:calibration_fit.py")

for script_pair in "${SU_SCRIPTS[@]}"; do
    LINK_NAME="${script_pair%%:*}"
    SOURCE_NAME="${script_pair##*:}"
    SOURCE_PATH="$SU_DEV_DIR/$SOURCE_NAME"
    LINK_PATH="$SCRIPTS_DIR/$LINK_NAME"
    
    if [ -f "$SOURCE_PATH" ]; then
        [ -L "$LINK_PATH" ] || [ -f "$LINK_PATH" ] && rm -f "$LINK_PATH"
        ln -s "$SOURCE_PATH" "$LINK_PATH"
        echo "[OK] $LINK_NAME symlink created"
    else
        echo "[WARN] $SOURCE_NAME not found at $SOURCE_PATH"
    fi
done
echo ""

# Step 3: Sync dependencies (standard packages only)
echo "Installing dependencies..."
uv sync --all-groups
echo "[OK] Dependencies installed"
echo ""

# Step 4: Make run script executable
chmod +x run.sh
echo "[OK] Made run.sh executable"
echo ""

echo "[COMPLETE] Setup complete!"
echo ""
echo "DPI packages will be accessed via PYTHONPATH at runtime."
echo ""
echo "To run the application:"
echo "  ./run.sh"
echo ""
