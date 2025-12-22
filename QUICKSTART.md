# HardwareGUI - Quick Start Guide

Get the application running in 2 simple steps after cloning!

## Prerequisites

- **Python 3.11+** (recommended: 3.12)
- **Linux system** with access to `/measdata/dpi` directory containing DPI modules
- **uv** package manager (will be installed automatically if missing)

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url> HardwareGUI
cd HardwareGUI
```

### Step 2: Run Setup

```bash
./setup.sh
```

This script will:
- ✅ Install `uv` if not present
- ✅ Create virtual environment and install all dependencies
- ✅ Verify DPI module paths
- ✅ Make `run.sh` executable

## Running the Application

After setup, simply run:

```bash
./run.sh
```

This will:
1. Configure DPI module paths automatically
2. Sync any missing dependencies
3. Launch the GUI application

## What Happens Under the Hood

### DPI Path Configuration

The `run.sh` script sources `DPIPathConfiguration.sh`, which sets up `PYTHONPATH` to include:
- `/measdata/dpi/voltageunit/python`
- `/measdata/dpi/maincontrolunit/python`
- `/measdata/dpi/dpi`

This ensures the application can import DPI hardware modules without manual configuration.

### Dependency Management

All dependencies are managed via `uv` and defined in `pyproject.toml`:
- **Runtime dependencies**: Core packages needed to run the app
- **Dev dependencies**: PySide6, matplotlib, testing tools, etc.

## Portable Deployment

To deploy on another machine:

1. **Clone the repository** on the target machine
2. **Ensure `/measdata/dpi` is accessible** (or update paths in `DPIPathConfiguration.sh`)
3. **Run `./setup.sh`** - that's it!

No manual venv creation, no pip installs, no path configuration needed.

## Troubleshooting

### uv not found after installation

```bash
source ~/.bashrc  # or restart your shell
```

### DPI modules not found

Verify paths exist:
```bash
ls -la /measdata/dpi/dpi
ls -la /measdata/dpi/voltageunit/python
ls -la /measdata/dpi/maincontrolunit/python
```

If paths differ, edit `DPIPathConfiguration.sh` to match your system.

### Permission denied on run.sh

```bash
chmod +x run.sh setup.sh
```

## Development

### Running without the script

```bash
source DPIPathConfiguration.sh  # Configure paths
uv sync --all-groups           # Install dependencies
uv run python src/main.py      # Run app
```

### Adding new dependencies

Edit `pyproject.toml`, then run:
```bash
uv add <package-name>
```

### Linting and Formatting

```bash
uv run ruff check .     # Lint
uv run black .          # Format
uv run mypy src/        # Type check
```

## Next Steps

- Read the full [README.md](README.md) for architecture details
- Explore the GUI scripts in `src/gui/scripts/voltage_unit/`
- Check calibration and test workflows

---

**Need help?** Contact the Institute of Microelectronics team.
