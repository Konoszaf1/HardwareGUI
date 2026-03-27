"""Reusable live-plotting widget backed by matplotlib (Qt-embedded).

Designed for real-time data streaming (append_point) and post-acquisition
batch display (plot_batch).  Integrates with the ``data_chunk`` signal on
``TaskSignals`` for worker-thread → GUI updates.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

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
    """A matplotlib-based plotting widget for live and batch data display.

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

        self._figure = Figure(facecolor="#2a2a2a")
        self._figure.subplots_adjust(left=0.12, right=0.95, top=0.90, bottom=0.15)
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._ax = self._figure.add_subplot(111)
        self._style_axes()
        layout.addWidget(self._canvas)

        # series_name -> {"x": list, "y": list, "line": Line2D}
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
        self._ax.set_title(title, color="#cccccc", fontsize=10)
        self._ax.set_xlabel(xlabel, color="#cccccc", fontsize=9)
        self._ax.set_ylabel(ylabel, color="#cccccc", fontsize=9)
        self._figure.tight_layout(pad=1.5)
        self._canvas.draw_idle()

    def append_point(self, series: str, x: float, y: float) -> None:
        """Append a single data point to *series*, creating it if needed.

        Thread-safe when called from a Qt signal slot (auto-queued).
        """
        if series not in self._series:
            self._create_series(series, scatter=True)
        s = self._series[series]
        s["x"].append(x)
        s["y"].append(y)
        s["line"].set_data(s["x"], s["y"])
        self._ax.relim()
        self._ax.autoscale_view()
        self._canvas.draw_idle()

    def plot_batch(
        self,
        x: Sequence[float] | np.ndarray,
        y: Sequence[float] | np.ndarray,
        series: str = "data",
        linestyle: str = "-",
        alpha: float = 1.0,
        color: str | None = None,
    ) -> None:
        """Plot an entire array pair at once (post-acquisition).

        Replaces any existing data for *series*.  Uses line-only mode
        (no markers) to handle large waveforms (50K+ points) without
        freezing the GUI.
        """
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)

        # Drop NaN entries
        mask = np.isfinite(x_arr) & np.isfinite(y_arr)
        x_arr = x_arr[mask]
        y_arr = y_arr[mask]

        if series not in self._series:
            self._create_series(
                series,
                scatter=False,
                linestyle=linestyle,
                alpha=alpha,
                color=color,
            )
        s = self._series[series]
        s["x"] = x_arr.tolist()
        s["y"] = y_arr.tolist()
        s["line"].set_data(x_arr, y_arr)
        self._ax.relim()
        self._ax.autoscale_view()
        self._figure.tight_layout(pad=1.5)
        self._canvas.draw_idle()

    def remove_series(self, name: str) -> None:
        """Remove a single named series from the plot."""
        if name in self._series:
            self._series[name]["line"].remove()
            del self._series[name]
            self._refresh_legend()
            self._ax.relim()
            self._ax.autoscale_view()
            self._canvas.draw_idle()

    def set_series_visible(self, names: set[str] | None = None) -> None:
        """Show only the given series, hiding all others.

        Args:
            names: Set of series names to show. None or empty shows all.
        """
        show_all = not names
        for sname, s in self._series.items():
            s["line"].set_visible(show_all or (names is not None and sname in names))
        self._refresh_legend()
        self._ax.relim()
        self._ax.autoscale_view()
        self._recompute_limits(names)
        self._canvas.draw_idle()

    def series_names(self) -> list[str]:
        """Return the names of all series in insertion order."""
        return list(self._series.keys())

    def clear(self) -> None:
        """Remove all series and reset the plot."""
        self._ax.cla()
        self._style_axes()
        self._series.clear()
        self._color_idx = 0
        self._canvas.draw_idle()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _refresh_legend(self) -> None:
        """Rebuild the legend showing only visible series."""
        visible = [(s["line"], n) for n, s in self._series.items() if s["line"].get_visible()]
        legend = self._ax.get_legend()
        if visible:
            lines, labels = zip(*visible, strict=False)
            self._ax.legend(
                lines,
                labels,
                loc="upper right",
                fontsize=8,
                facecolor="#333333",
                edgecolor="#555555",
                labelcolor="#cccccc",
            )
        elif legend:
            legend.remove()

    def _recompute_limits(self, visible_names: set[str] | None = None) -> None:
        """Recompute axis limits based on visible series only.

        ``relim()`` only considers visible artists in newer matplotlib,
        but to be safe we set limits manually when filtering.
        """
        if not visible_names:
            # Show-all mode — let autoscale handle it
            self._ax.autoscale_view()
            return
        xs, ys = [], []
        for name in visible_names:
            s = self._series.get(name)
            if s and s["x"]:
                xs.extend(s["x"])
                ys.extend(s["y"])
        if xs and ys:
            xmin, xmax = min(xs), max(xs)
            ymin, ymax = min(ys), max(ys)
            xpad = (xmax - xmin) * 0.05 or 1e-12
            ypad = (ymax - ymin) * 0.05 or 1e-12
            self._ax.set_xlim(xmin - xpad, xmax + xpad)
            self._ax.set_ylim(ymin - ypad, ymax + ypad)

    def _style_axes(self) -> None:
        """Apply dark theme styling to axes."""
        self._ax.set_facecolor("#2a2a2a")
        self._ax.tick_params(colors="#cccccc", labelsize=8)
        self._ax.grid(True, alpha=0.3, color="#cccccc")
        self._ax.margins(0.05)
        for spine in self._ax.spines.values():
            spine.set_color("#555555")

    def _create_series(
        self,
        name: str,
        scatter: bool = False,
        linestyle: str = "-",
        alpha: float = 1.0,
        color: str | None = None,
    ) -> None:
        """Create a new named data series with the next colour."""
        if color is None:
            color = _COLORS[self._color_idx % len(_COLORS)]
            self._color_idx += 1
        if scatter:
            (line,) = self._ax.plot(
                [],
                [],
                marker="o",
                markersize=4,
                linestyle=linestyle,
                linewidth=1.5,
                color=color,
                alpha=alpha,
                label=name,
            )
        else:
            (line,) = self._ax.plot(
                [],
                [],
                linestyle=linestyle,
                linewidth=1.5,
                color=color,
                alpha=alpha,
                label=name,
            )
        self._refresh_legend()
        self._series[name] = {"x": [], "y": [], "line": line}
