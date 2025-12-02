#!/bin/bash
# DPIPathConfiguration.sh - Configure Python paths for DPI modules

# Add DPI module paths to PYTHONPATH
export PYTHONPATH="/measdata/dpi/voltageunit/python:${PYTHONPATH}"
export PYTHONPATH="/measdata/dpi/voltageunit/python/dev:${PYTHONPATH}"
export PYTHONPATH="/measdata/dpi/maincontrolunit/python:${PYTHONPATH}"
export PYTHONPATH="/measdata/dpi/dpi:${PYTHONPATH}"

echo "[OK] DPI Python paths configured"
