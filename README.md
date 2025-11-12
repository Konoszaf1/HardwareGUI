# HardwareGUI

PySide6 app with a frameless main window for handling the initialization of hardware in the Institute of Microelectronics
Uses a simple Model–View–Presenter split and typed dataclasses for the domain layer.

## What it does

* Perform all necessary actions for rebooting any hardware as well has having
an overview of all calibration steps that have already commenced.
* Easily extensible with more hardware and intiialization steps only with 
minimal code

## Repo layout

```
HardwareGUI/
├─ src/
│  ├─ main.py                       # App entrypoint (applies qt-material theme)
│  ├─ populate_items.py             # Static seed data for hardware/actions
│  ├─ ui_main_window.py             # Generated from Qt Designer .ui
│  ├─ gui/
│  │  ├─ main_window.py             # Frameless main window + wiring
│  │  ├─ button_factory.py          # Builds SidebarButton instances
│  │  ├─ sidebar_button.py          # Animated tool button (expand/collapse)
│  │  ├─ expanding_splitter.py      # Hover-to-expand sidebar splitter
│  │  └─ hiding_listview.py         # ListView with zero-width min size hint
│  └─ logic/
│     ├─ presenter.py               # ActionsPresenter (connects view and model)
│     ├─ action_dataclass.py        # ActionDescriptor dataclass
│     ├─ hardware_dataclass.py      # HardwareDescriptor dataclass
│     └─ model/
│        └─ actions_model.py        # QAbstractListModel + filter proxy
├─ requirements.txt                 # Runtime + tooling deps
├─ pyproject.toml                   # ruff + mypy settings
└─ .gitignore
```

## Requirements

* Python 3.11+ (recommended: 3.12.3)
* Qt runtime via `PySide6` (installed through `uv`)
* Access to `/measdata/dpi` directory with DPI hardware packages
* Linux: X11 users may need `libxcb` and related Qt platform packages
* Windows/macOS: no extra system deps beyond Python

## Quick start

```bash
# 1) Create and activate a virtualenv
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
# .venv\Scripts\activate   # Windows

# 2) Install project dependencies
uv sync

# 3) Install DPI hardware packages (editable mode)
./install_dpi.sh

# 4) Run the application
python src/main.py
```

The app loads the `dark_amber.xml` theme from `qt-material` and opens the main
window of the application.

## DPI Package Installation

The application depends on local DPI hardware packages that are not on PyPI:

- **dpi** - Main DPI framework (`/measdata/dpi/dpi`)
- **dpivoltageunit** - Voltage Unit drivers (`/measdata/dpi/voltageunit/python`)
- **dpimaincontrolunit** - Main Control Unit drivers (`/measdata/dpi/maincontrolunit/python`)

These are installed in **editable mode** via the `install_dpi.sh` script, which runs:

```bash
cd /measdata/dpi/dpi && uv pip install -e .
cd /measdata/dpi/voltageunit/python && uv pip install -e .
cd /measdata/dpi/maincontrolunit/python && uv pip install -e .
```

Editable mode means changes to the DPI source code are immediately reflected without reinstallation.

## Development

### Tooling

* Formatting: `black`
* Linting: `ruff`
* Typing: `mypy` with `strict = true`

```bash
# format
black .

# lint
ruff check .

# type-check
mypy .
```

### UI generation

`ui_main_window.py` is generated from a Qt Designer `.ui` file. If you change the `.ui`, re-generate:

```bash
# example (adjust paths to your environment)
pyside6-uic main_window.ui -o src/ui_main_window.py
```
Or directly using uv with
``` 
uv tool run --from pyside6-essentials pyside6-uic src/ui/main_window.ui -o src/ui_main_window.py --from-imports
```
## Resources (Qt Resource System)

Goal: add images/icons/styles and load them via `:/...` paths.

### Layout

```
src/
├─ resources/
│  ├─ icons/        # .svg/.png
│  └─ icons.qrc     # Qt resource collection
```

### Create `icons.qrc`

Minimal example:

```xml
<RCC>
  <qresource prefix="/icons">
    <file>icons/gear.svg</file>
    <file>icons/plus.svg</file>
  </qresource>
  <qresource prefix="/images">
    <file>images/banner.png</file>
  </qresource>
</RCC>
```

### Compile to Python

Run after adding/removing files:

```bash
# from repo root
pyside6-rcc src/resources/resources.qrc -o src/icons_rc.py
```

Commit `src/icons_rc.py`. This embeds assets into the binary and avoids runtime file lookups.

#### Use in Qt Designer

Set properties to resource paths (e.g., `:/icons/plus.svg`). After regenerating `ui_main_window.py`, ensure `import icons_rc` executes before UI uses those paths (import it in `main.py` or at the top of `ui_main_window.py`).

### Update workflow

1. Add files under `src/resources/...`
2. Update `resources.qrc`
3. Re-run `pyside6-rcc` to refresh `icons_rc.py`
4. Run app

### Troubleshooting

Icons not visible → confirm the `:/...` path, `icons_rc.py` is up to date, and `import icons_rc` happens before any UI loads paths.

### Tests

A placeholder `src/test_main.py` exists. Add your tests and run with `pytest` (not pinned in requirements; install if used):

```bash
pip install pytest
pytest -q
```

## Architecture notes

* **View**: `MainWindow`, `ExpandingSplitter`, `SidebarButton`, `HidingListView`, `Ui_MainWindow`
* **Model**: `ActionModel` (`QAbstractListModel`) exposes roles: `id`, `hardware_id`, `label`, `order`
* **Proxy**: `ActionsByHardwareProxy` filters `ActionModel` by selected hardware id
* **Presenter**: `ActionsPresenter` binds sidebar button toggles → proxy filter and sets the list’s model
* **Data**: `populate_items.py` seeds `HARDWARE` and `ACTIONS` for the demo

## Packaging (optional)

For a quick single-file build using PyInstaller:

```bash
pip install pyinstaller
pyinstaller -n HardwareGUI -F -w src/main.py
```

Adjust hidden imports for PySide6 if needed.

## Troubleshooting

* App doesn’t start and mentions Qt platform plugin “xcb”: install system packages for X11 (e.g., `libxcb`, `libxkbcommon-x11`) or run on Wayland/XQuartz with appropriate Qt plugins.
* If icons don’t render, ensure `icons_rc.py` and the resource paths (e.g., `:/icons/*.png`) are available.

## License

MIT
