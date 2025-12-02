# Navigate to your project
cd /path/to/HardwareGUI

# Create a .pth file in your venv's site-packages
cat > .venv/lib/python3.12/site-packages/dpi_packages.pth << 'EOF'
/measdata/dpi/dpi
/measdata/dpi/arrayextensionunit/python
/measdata/dpi/maincontrolunit/python
/measdata/dpi/powersupplyunit/python
/measdata/dpi/samplingunit/python
/measdata/dpi/sourcemeasureunit/python
/measdata/dpi/voltageunit/python
EOF
