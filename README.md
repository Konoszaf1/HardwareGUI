# HardwareGUI

A PySide6 application for controlling and calibrating DPI hardware at the Institute of Microelectronics. The application uses a Model-View-Presenter architecture with typed dataclasses for clean separation of concerns.

## Overview

This application provides:
- Hardware initialization and calibration workflows
- Real-time monitoring and control of voltage units, main control units, and other DPI hardware
- Interactive GUI for running tests and viewing calibration results
- Modular architecture for easy extension with new hardware types

## Project Structure

```
HardwareGUI/
├─ src/
│  ├─ main.py                       # Application entry point
│  ├─ setup_cal.py                  # Symlink to calibration utilities
│  ├─ gui/
│  │  ├─ main_window.py             # Main application window
│  │  ├─ scripts/voltage_unit/      # Voltage unit control pages
│  │  └─ utils/                     # GUI helpers and utilities
│  └─ logic/
│     ├─ presenter.py               # MVP presenter layer
│     ├─ vu_service.py              # Voltage unit service
│     ├─ qt_workers.py              # Background task management
│     └─ model/                     # Data models
├─ setup.sh                         # One-time setup script
├─ run.sh                           # Application launcher
├─ pyproject.toml                   # Project dependencies and tools
└─ DPIPathConfiguration.sh          # DPI package path configuration
```

## Requirements

- Python 3.11 or later (3.12 recommended)
- Access to `/measdata/dpi` directory containing DPI hardware packages
- `uv` package manager (installed automatically by setup.sh)
- Linux system with X11 or Wayland

### Hardware Dependencies

The application requires access to the following DPI packages in `/measdata/dpi`:
- `dpi` - Core DPI framework
- `dpivoltageunit` - Voltage unit drivers
- `dpimaincontrolunit` - Main control unit drivers
- `dpiarrayextensionunit` - Array extension unit drivers
- `dpipowersupplyunit` - Power supply unit drivers
- `dpisamplingunit` - Sampling unit drivers
- `dpisourcemeasureunit` - Source measure unit drivers

These packages are accessed via PYTHONPATH at runtime and do not need to be installed.

## Installation

The setup process is simple and automated:

```bash
# 1. Clone the repository (or navigate to your clone)
cd HardwareGUI

# 2. Ensure you are not in any virtual environment
deactivate  # if you're in a venv

# 3. Run the setup script
./setup.sh
```

The setup script will:
- Install the `uv` package manager if needed
- Create a virtual environment in `.venv`
- Install all Python dependencies
- Create a symlink to the calibration utilities

## Running the Application

To launch the application:

```bash
./run.sh
```

The run script handles environment configuration automatically, including:
- Setting the correct working directory
- Configuring PYTHONPATH for DPI package access
- Setting required environment variables

**Important**: Make sure you are not in an active virtual environment before running. The script will check and warn you if needed.

## Development

### Code Quality Tools

The project uses the following tools for code quality:

```bash
# Format code
uv run black .

# Check linting
uv run ruff check .

# Type checking
uv run mypy src/
```

Configuration for these tools is in `pyproject.toml`.

### UI Development

The UI is built with Qt Designer. To regenerate UI files:

```bash
uv tool run --from pyside6-essentials pyside6-uic \
  src/ui/main_window.ui \
  -o src/ui_main_window.py \
  --from-imports
```

### Architecture

- **View Layer**: PySide6 widgets and windows
- **Model Layer**: `QAbstractListModel` implementations for data
- **Presenter Layer**: Connects views to models, handles user interactions
- **Service Layer**: Background task execution and hardware communication

The application uses Qt's signal/slot mechanism for loose coupling between components.

## Features

### Calibration

The calibration page provides:
- Python-based autocalibration (iterative, up to 10 iterations)
- Onboard autocalibration (firmware-based)
- Comprehensive test suite (output tests, ramp tests, transient tests)
- Real-time thumbnail updates showing generated plots

### Testing

The testing page allows you to:
- Run individual validation tests
- Execute all tests sequentially
- View results as they are generated
- Monitor test output in real-time

### Session Management

Control hardware parameters:
- Scope connectivity verification
- Hardware ID configuration
- Coefficient management (RAM and EEPROM)

## Troubleshooting

### Application Won't Start

If you see Qt platform plugin errors:
```bash
sudo apt-get install libxcb-cursor0 libxkbcommon-x11-0
```

### Import Errors

If you see `ModuleNotFoundError` for DPI packages:
- Verify `/measdata/dpi` directory exists and is accessible
- Check that you ran `./setup.sh` successfully
- Ensure you deactivated any other virtual environments before running `./run.sh`

### Plot Thumbnails Not Updating

Thumbnails update automatically during calibration. If they don't:
- Check that the `calibration_vuXXXX` directory is being created
- Verify file permissions allow writing to the project directory

## Portable Deployment

To deploy on another machine:

1. Clone the repository
2. Ensure `/measdata/dpi` is accessible (or update `DPIPathConfiguration.sh` with correct paths)
3. Run `./setup.sh`
4. Run `./run.sh`

No manual configuration is required. The scripts handle all environment setup.

## License

MIT
