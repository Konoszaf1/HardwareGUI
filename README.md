# HardwareGUI

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
![License](https://img.shields.io/badge/license-MIT-green)

A PySide6 application for controlling and calibrating DPI hardware at the Institute of Microelectronics. Built with a **Model-View-Presenter (MVP)** architecture, it features type-safe configuration, asynchronous hardware communication, and a modular UI.

---

## Key Features

- **Automated Calibration**: Python-based and onboard firmware calibration workflows.
- **Real-Time Monitoring**: Live status updates from Voltage Units and Main Control Units.
- **Visual Feedback**: Real-time plotting and thumbnail generation for calibration results.
- **Modular Design**: Extensible architecture for new hardware types.
- **Portable Deployment**: Automated setup scripts for zero-configuration deployment.

---

## Requirements

### System Requirements
- **OS**: Linux (X11 or Wayland)
- **Python**: 3.12 or later
- **Hardware Access**: Network access to DPI hardware (default scope IP: `192.168.68.154`)

### External Dependencies
The application relies on the standard DPI package library at `/measdata/dpi`:
- `dpi` (Core framework)
- `dpivoltageunit`
- `dpimaincontrolunit`
- `dpiarrayextensionunit`
- `dpipowersupplyunit`
- `dpisamplingunit`
- `dpisourcemeasureunit`

> **Note**: These packages are loaded dynamically via `PYTHONPATH` by the launcher script. You do not need to install them manually.

---

## Quick Start

### 1. Installation

The `setup.sh` script automates the entire installation process, creating a dedicated virtual environment with `uv`.

```bash
# Clone the repository
git clone https://github.com/yourusername/HardwareGUI.git
cd HardwareGUI

# Run setup (handles venv creation and dependencies)
./setup.sh
```

### 2. Running the App

Always use the provided `run.sh` script to launch the application. It handles crucial environment setup (PYTHONPATH, variable updates) that direct Python invocation would miss.

```bash
./run.sh
```

---

## Architecture

The application follows a **Model-View-Presenter (MVP)** pattern to separate UI logic from business rules and hardware communication.

### High-Level Overview

```mermaid
graph TD
    subgraph Presentation_Layer [Presentation Layer]
        View["View (MainWindow, Pages)"]
        Presenter["Presenter (ActionsPresenter)"]
    end

    subgraph Domain_Layer [Domain Layer]
        Model["Model (ActionModel)"]
        Service["Service (VoltageUnitService)"]
    end

    subgraph Infrastructure [Infrastructure]
        Workers["Qt Workers (Background Threads)"]
        Hardware["DPI Hardware (/measdata/dpi)"]
    end

    User((User)) -->|Interacts| View
    View -->|Emits Signals| Presenter
    View -->|Reads Data| Model
    Presenter -->|Commands| Service
    Service -->|Spawns| Workers
    Workers -->|I/O| Hardware
    Workers -->|Signals| Presenter
    Model -->|Provides Structure| View
```

### Component Roles

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **View** | `MainWindow`, `BasePage` | Renders UI, capturing inputs, displaying data. Reads structure from Model. |
| **Presenter** | `ActionsPresenter` | Orchestrates logic. Receives view signals, calls services. |
| **Model** | `ActionModel` | Static data structure defining application hierarchy (read-only). |
| **Service** | `VoltageUnitService` | Handles long-running business logic and hardware communication using independent workers. |

### Configuration System
Configuration is centralized in `src/config.py` using immutable dataclasses (`frozen=True`) to prevent runtime modification and side effects.

---

## Development Workflow

The project uses modern Python tooling for quality assurance.

### Code Style & Quality
We use `ruff` for linting/formatting and `mypy` for static analysis.

```bash
# Format code (Black compliant)
uv run ruff format .

# Run linting check
uv run ruff check .

# Run static type checking
uv run mypy src/
```

### Running Tests
Unit tests use `pytest` with `pytest-qt` for GUI interaction.

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src
```

### Qt Resources
Icons and assets are compiled into a Python module. If you modify `.qrc` files or add icons:

```bash
# Regenerate resources
./scripts/build_resources.sh
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **ModuleNotFoundError: No module named 'dpi'** | Missing PYTHONPATH | Always run using `./run.sh`, not `python src/main.py`. |
| **Qt Platform Plugin Error** | Missing system libs | Install `libxcb-cursor0` and `libxkbcommon-x11-0`. |
| **Permission Denied** | Script execution rights | Run `chmod +x setup.sh run.sh scripts/*.sh`. |

### Debugging
To enable verbose debug logging, export the `LOG_LEVEL` variable before running:

```bash
export LOG_LEVEL=DEBUG
./run.sh
```

---

## Project Structure

```bash
HardwareGUI/
├── src/
│   ├── config.py             # Centralized configuration
│   ├── main.py               # Entry point
│   ├── gui/                  # View layer
│   │   ├── main_window.py
│   │   ├── scripts/          # Hardware specific pages
│   │   └── utils/            # Shared UI components
│   ├── logic/                # Business logic
│   │   ├── presenter.py      # MVP Presenter
│   │   ├── vu_service.py     # Hardware Service
│   │   └── model/            # Data Models
│   └── resources/            # Icons and assets
├── tests/                    # Unit and integration tests
├── setup.sh                  # One-time install script
├── run.sh                    # Application launcher
└── pyproject.toml            # Dependencies & tool config
```
