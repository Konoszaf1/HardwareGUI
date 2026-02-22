"""Reusable live-plotting widget backed by pyqtgraph.

Designed for real-time data streaming (append_point) and post-acquisition
batch display (plot_batch).  Integrates with the ``data_chunk`` signal on
``TaskSignals`` for worker-thread → GUI updates.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget

# ---------------------------------------------------------------------------
# Module-level pyqtgraph configuration (called once at import time)
# ---------------------------------------------------------------------------
pg.setConfigOptions(
    antialias=True,
    background="#2a2a2a",
    foreground="#cccccc",
)

# Consistent colour cycle for up to 8 series
_COLORS = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # grey
]


class LivePlotWidget(QWidget):
    """A pyqtgraph-based plotting widget for live and batch data display.

    Usage
    -----
    Live (Category A – iterative operations)::

        widget.clear()
        widget.set_labels("Calibration", "V_ref", "V_meas")
        # called from data_chunk signal handler:
        widget.append_point("AMP01", x, y)

    Batch (Category B – post-acquisition)::

        widget.clear()
        widget.set_labels("Transient", "Time / s", "Voltage / V")
        widget.plot_batch(time_array, voltage_array, "transient")
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plot_widget = pg.PlotWidget()
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.addLegend(offset=(10, 10))
        layout.addWidget(self._plot_widget)

        # series_name -> {"x": list, "y": list, "curve": PlotDataItem}
        self._series: dict[str, dict] = {}
        self._color_idx = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_labels(
        self,
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
    ) -> None:
        """Configure axis labels and title."""
        self._plot_widget.setTitle(title)
        self._plot_widget.setLabel("bottom", xlabel)
        self._plot_widget.setLabel("left", ylabel)

    def append_point(self, series: str, x: float, y: float) -> None:
        """Append a single data point to *series*, creating it if needed.

        Thread-safe when called from a Qt signal slot (auto-queued).
        """
        if series not in self._series:
            self._create_series(series)
        s = self._series[series]
        s["x"].append(x)
        s["y"].append(y)
        s["curve"].setData(s["x"], s["y"])

    def plot_batch(
        self,
        x: Sequence[float] | np.ndarray,
        y: Sequence[float] | np.ndarray,
        series: str = "data",
    ) -> None:
        """Plot an entire array pair at once (post-acquisition).

        Replaces any existing data for *series*.
        """
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)

        if series not in self._series:
            self._create_series(series)
        s = self._series[series]
        s["x"] = x_arr.tolist()
        s["y"] = y_arr.tolist()
        s["curve"].setData(x_arr, y_arr)

    def clear(self) -> None:
        """Remove all series and reset the plot."""
        self._plot_widget.clear()
        # Re-add legend after clear (pyqtgraph removes it)
        self._plot_widget.addLegend(offset=(10, 10))
        self._series.clear()
        self._color_idx = 0

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _create_series(self, name: str) -> None:
        """Create a new named data series with the next colour."""
        color = _COLORS[self._color_idx % len(_COLORS)]
        self._color_idx += 1
        pen = pg.mkPen(color=color, width=2)
        curve = self._plot_widget.plot(
            [],
            [],
            pen=pen,
            symbol="o",
            symbolSize=5,
            symbolBrush=color,
            name=name,
        )
        self._series[name] = {"x": [], "y": [], "curve": curve}
