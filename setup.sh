#!/bin/bash
# setup.sh - One-time setup script for HardwareGUI
# Run this after cloning the repository

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "🔧 HardwareGUI Setup"
echo "===================="
echo ""

# Step 1: Check for uv
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✓ uv installed"
    echo "  Please run: source ~/.bashrc (or restart your shell)"
    echo "  Then run this script again"
    exit 0
fi
echo "✓ uv found: $(uv --version)"
echo ""

# Step 2: Sync dependencies
echo "📦 Installing dependencies..."
uv sync --all-groups
echo "✓ Dependencies installed"
echo ""

# Step 3: Verify DPI paths
echo "🔍 Verifying DPI module paths..."
if [ -d "/measdata/dpi" ]; then
    echo "✓ /measdata/dpi directory found"
    
    # Check for required modules
    for module in "dpi" "voltageunit/python" "maincontrolunit/python"; do
        if [ -d "/measdata/dpi/$module" ]; then
            echo "  ✓ $module exists"
        else
            echo "  ⚠️  $module not found"
        fi
    done
else
    echo "⚠️  /measdata/dpi directory not found"
    echo "   DPI modules will need to be configured manually"
fi
echo ""

# Step 4: Make run script executable
chmod +x run.sh
echo "✓ Made run.sh executable"
echo ""

echo "✅ Setup complete!"
echo ""
echo "To run the application:"
echo "  ./run.sh"
echo ""
