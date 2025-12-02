#!/bin/bash
# run.sh - Portable startup script for HardwareGUI
# This script handles DPI path configuration and starts the application

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 HardwareGUI Startup"
echo "======================="
echo ""

# Step 1: Source DPI path configuration
echo "📁 Configuring DPI module paths..."
if [ -f "DPIPathConfiguration.sh" ]; then
    source DPIPathConfiguration.sh
else
    echo "⚠️  Warning: DPIPathConfiguration.sh not found"
    echo "   Creating default configuration..."
    cat > DPIPathConfiguration.sh << 'DPICFG'
#!/bin/bash
# DPIPathConfiguration.sh - Configure Python paths for DPI modules

# Add DPI module paths to PYTHONPATH
export PYTHONPATH="/measdata/dpi/voltageunit/python:${PYTHONPATH}"
export PYTHONPATH="/measdata/dpi/maincontrolunit/python:${PYTHONPATH}"
export PYTHONPATH="/measdata/dpi/dpi:${PYTHONPATH}"

echo "✓ DPI Python paths configured:"
echo "  - /measdata/dpi/voltageunit/python"
echo "  - /measdata/dpi/maincontrolunit/python"
echo "  - /measdata/dpi/dpi"
DPICFG
    source DPIPathConfiguration.sh
fi
echo ""

# Step 2: Check for uv
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed"
    echo "   Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "✓ uv found: $(uv --version)"
echo ""

# Step 3: Sync dependencies
echo "📦 Syncing dependencies with uv..."
uv sync --all-groups
echo ""

# Step 4: Run the application
echo "▶️  Starting HardwareGUI..."
echo ""
uv run python src/main.py
