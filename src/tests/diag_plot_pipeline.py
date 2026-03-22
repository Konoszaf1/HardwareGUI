#!/usr/bin/env python3
"""Diagnostic: test scope data acquisition and pyqtgraph rendering pipeline.

Usage:
    python -m src.tests.diag_plot_pipeline

Tests:
    1. Scope communication (vxi11 to 192.168.68.154)
    2. LivePlotWidget rendering with synthetic data
    3. LivePlotWidget rendering with real scope data
    4. Full VU service pipeline tracing (what TaskResult.data contains)
"""

from __future__ import annotations

import sys
import traceback
from typing import Any

import numpy as np

SCOPE_IP = "192.168.68.154"


# =========================================================================
# Test 1: Scope Communication
# =========================================================================
def test_scope_communication():
    print("\n=== TEST 1: Scope Communication ===")
    import vxi11

    scope = vxi11.Instrument(SCOPE_IP)
    idn = scope.ask("*IDN?")
    print(f"  IDN: {idn}")

    # Simple single acquisition
    scope.write("*RST")
    scope.write("CHAN:TYPE HRES")
    scope.write("ACQ:POIN 5000")
    scope.write("TIM:SCAL 1e-2")
    scope.write("CHAN1:SCAL 0.20")
    scope.write("FORM REAL")
    scope.write("FORM:BORD LSBF")
    scope.write("CHAN:DATA:POIN DMAX")
    scope.write("CHAN1:STAT ON")

    print("  Triggering single acquisition...")
    scope.ask("SING;*OPC?")

    # Read header + data
    head = scope.ask("CHAN1:DATA:HEAD?")
    print(f"  Header: {head}")

    scope.write("CHAN1:DATA?")
    raw = scope.read_raw()
    lead_digits = int(raw[1:2].decode("utf-8"))
    len_bytes = int(raw[2 : 2 + lead_digits].decode("utf-8"))
    data = np.frombuffer(
        raw[lead_digits + 2 : lead_digits + 2 + len_bytes],
        dtype=np.single,
    )
    t0 = float(head.split(",")[0])
    t1 = float(head.split(",")[1])
    t = np.linspace(t0, t1, len(data))

    print(f"  Data points: {len(data)}")
    print(f"  Time range:  [{t[0]:.6e}, {t[-1]:.6e}] s")
    print(f"  Data range:  [{np.nanmin(data):.6f}, {np.nanmax(data):.6f}] V")
    print(f"  NaN count:   {np.sum(np.isnan(data))}")
    print(f"  Mean:        {np.nanmean(data):.6f} V")

    scope.write("*RST")
    return t, data


# =========================================================================
# Test 2: LivePlotWidget with synthetic data
# =========================================================================
def test_synthetic_plot(app):
    from src.gui.widgets.live_plot_widget import LivePlotWidget

    print("\n=== TEST 2: LivePlotWidget with Synthetic Data ===")

    widget = LivePlotWidget()
    widget.setWindowTitle("TEST 2: Synthetic Data")
    widget.set_labels("Synthetic Test", "X", "Y")
    widget.setMinimumSize(800, 400)

    # Scatter test (like test_outputs)
    voltages = [-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75]
    for v in voltages:
        widget.append_point("CH1", v, float(np.random.normal(0, 0.001)))
        widget.append_point("CH2", v, float(np.random.normal(0, 0.0015)))
        widget.append_point("CH3", v, float(np.random.normal(0, 0.0008)))

    series_info = widget._series
    for name, s in series_info.items():
        print(
            f"  Series '{name}': {len(s['x'])} points, "
            f"x=[{min(s['x']):.3f}..{max(s['x']):.3f}], "
            f"y=[{min(s['y']):.6f}..{max(s['y']):.6f}]"
        )

    widget.show()
    print("  Widget shown. Close to continue...")
    app.exec()
    print("  PASSED: Synthetic scatter rendered.")


# =========================================================================
# Test 3: LivePlotWidget with real scope data
# =========================================================================
def test_scope_plot(app, t, data):
    from src.gui.widgets.live_plot_widget import LivePlotWidget

    print("\n=== TEST 3: LivePlotWidget with Scope Data ===")

    widget = LivePlotWidget()
    widget.setWindowTitle("TEST 3: Real Scope Data")
    widget.set_labels("Scope CH1", "Time / s", "Voltage / V")
    widget.setMinimumSize(800, 400)

    print(f"  Feeding {len(t)} points to plot_batch...")
    print(f"  NaN before filter: {np.sum(np.isnan(data))}")

    widget.plot_batch(t, data, "CH1")

    series_info = widget._series
    for name, s in series_info.items():
        print(f"  Series '{name}': {len(s['x'])} points after NaN filter")

    widget.show()
    print("  Widget shown. Close to continue...")
    app.exec()
    print("  PASSED: Scope data rendered.")


# =========================================================================
# Test 4: Trace the full VU service pipeline return value
# =========================================================================
def test_pipeline_trace():
    """Simulate what the VU service pipeline does and print each stage."""
    print("\n=== TEST 4: Pipeline Data Structure Trace ===")

    # Build the plot dict as the controller would for test_outputs
    voltages = (-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75)
    errors = [
        [float(np.random.normal(0, 0.001)) for _ in voltages],
        [float(np.random.normal(0, 0.0015)) for _ in voltages],
        [float(np.random.normal(0, 0.0008)) for _ in voltages],
    ]

    # Stage 1: Controller OperationResult.data
    controller_data: dict[str, Any] = {
        "artifacts": ["calibration_vu1/output.png"],
        "plot": {
            "type": "outputs",
            "voltages": list(voltages),
            "errors": errors,
        },
    }
    plot_d: dict[str, Any] = controller_data["plot"]
    print(f"  Controller data keys: {list(controller_data.keys())}")
    print(f"  Controller plot type: {plot_d['type']}")
    print(f"  Controller voltages:  {plot_d['voltages']}")
    print(
        f"  Controller errors shape: {len(plot_d['errors'])} channels x "
        f"{len(plot_d['errors'][0])} points"
    )

    # Stage 2: Service job return dict
    service_result = {
        "ok": True,
        "artifacts": [],
        "plot": controller_data.get("plot"),
    }
    print(f"\n  Service result keys: {list(service_result.keys())}")
    print(f"  Service plot present: {service_result['plot'] is not None}")

    # Stage 3: TaskResult wrapping
    from src.logic.qt_workers import TaskResult

    task_result = TaskResult(name="test_outputs", ok=True, data=service_result)
    print(f"\n  TaskResult.name: {task_result.name}")
    print(f"  TaskResult.ok:   {task_result.ok}")
    print(f"  TaskResult.data type: {type(task_result.data).__name__}")

    # Stage 4: GUI _on_task_finished extraction
    data = getattr(task_result, "data", None)
    print(f"\n  getattr(result, 'data'): {type(data).__name__}")
    print(f"  isinstance(data, dict): {isinstance(data, dict)}")
    if isinstance(data, dict):
        plot = data.get("plot")
        plots = data.get("plots")
        print(f"  data.get('plot'):  {type(plot).__name__ if plot else None}")
        print(f"  data.get('plots'): {type(plots).__name__ if plots else None}")
        if plot:
            print(f"  plot['type']: {plot.get('type')}")
            print(f"  plot has 'voltages': {'voltages' in plot}")
            print(f"  plot has 'errors':   {'errors' in plot}")
            print(f"  plot has 'waveforms': {'waveforms' in plot}")
    print("\n  PASSED: Pipeline structure looks correct.")

    # Now trace test_ramp
    print("\n  --- Ramp pipeline ---")
    ramp_data: dict[str, Any] = {
        "plot": {
            "type": "ramp",
            "waveforms": [
                {"series": "CH1", "x": [0.0, 0.1, 0.2], "y": [0.0, 0.5, 1.0]},
                {"series": "CH2", "x": [0.0, 0.1, 0.2], "y": [0.0, -0.5, -1.0]},
            ],
        },
    }
    plot = ramp_data["plot"]
    print(f"  Ramp plot type: {plot['type']}")
    print(f"  Ramp waveforms: {len(plot['waveforms'])} series")
    for wf in plot["waveforms"]:
        print(f"    {wf['series']}: {len(wf['x'])} points")

    # Now trace test_all (the broken 'plots' path)
    print("\n  --- test_all pipeline (plots plural) ---")
    all_data: dict[str, Any] = {
        "plots": [
            {"type": "outputs", "voltages": list(voltages), "errors": errors},
            {"type": "ramp", "waveforms": [{"series": "CH1", "x": [0], "y": [0]}]},
            {"type": "transient", "waveforms": [{"series": "CH1", "x": [0], "y": [0]}]},
        ],
    }
    plots: list[dict[str, Any]] = all_data.get("plots", [])
    print(f"  plots count: {len(plots)}")
    print(
        f"  'for p in reversed(plots): ... break' renders: "
        f"{plots[-1]['type']} (only 1 of {len(plots)})"
    )


# =========================================================================
# Main
# =========================================================================
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    # Test 4 first (no hardware needed)
    test_pipeline_trace()

    try:
        t, data = test_scope_communication()
    except Exception:
        print(f"\n  FAILED: {traceback.format_exc()}")
        print("  Continuing without scope data...")
        t, data = None, None

    app = QApplication(sys.argv)

    test_synthetic_plot(app)

    if t is not None:
        app2: Any = QApplication.instance() or QApplication(sys.argv)
        test_scope_plot(app2, t, data)

    print("\n=== ALL TESTS COMPLETE ===")
