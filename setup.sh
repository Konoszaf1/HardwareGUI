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

# Step 2: Create symlink for setup_cal.py
echo "Creating setup_cal.py symlink..."
SETUP_CAL_SOURCE="/measdata/dpi/voltageunit/python/dev/setup_cal.py"
SETUP_CAL_LINK="$PROJECT_ROOT/src/setup_cal.py"

if [ -f "$SETUP_CAL_SOURCE" ]; then
    if [ -L "$SETUP_CAL_LINK" ] || [ -f "$SETUP_CAL_LINK" ]; then
        rm -f "$SETUP_CAL_LINK"
    fi
    ln -s "$SETUP_CAL_SOURCE" "$SETUP_CAL_LINK"
    echo "[OK] setup_cal.py symlink created"
else
    echo "[WARN] setup_cal.py not found at $SETUP_CAL_SOURCE"
fi
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
