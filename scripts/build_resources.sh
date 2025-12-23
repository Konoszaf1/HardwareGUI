#!/usr/bin/env bash
# Build Qt resource files for HardwareGUI
#
# This script compiles Qt resource (.qrc) files into Python modules
# that can be imported directly. This embeds icons and other assets
# into the application without requiring external file access.
#
# Prerequisites:
#   - uv and project dependencies installed (run ./setup.sh first)
#   - PySide6 installed (provides pyside6-rcc)
#
# Usage:
#   ./scripts/build_resources.sh
#
# The script will:
#   1. Compile src/resources/icons.qrc -> src/icons_rc.py
#   2. Report success or any errors encountered

set -e

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Building Qt Resources"
echo "====================="
echo ""

# Compile icons.qrc
echo "Compiling icons.qrc -> src/icons_rc.py..."
uv tool run --from pyside6-essentials pyside6-rcc src/resources/icons.qrc -o src/icons_rc.py

echo ""
echo "✓ Resource compilation complete!"
echo ""
echo "Note: The generated icons_rc.py file is imported in the application"
echo "to access embedded icons. Do not modify it manually."
