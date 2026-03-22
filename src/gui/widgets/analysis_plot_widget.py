"""Scrollable widget for displaying calibration analysis PNG images.

Loads matplotlib-generated analysis plots (nrows x 5 subplots) and
displays them in a scrollable area with dark theme background.
Supports cycling through multiple range analysis images.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.image import imread
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class AnalysisPlotWidget(QWidget):
    """Widget that displays calibration analysis PNGs in a scrollable area.

    Usage::

        widget.set_images(["/path/to/vsmu_False_pa_pach0_iv_ivch1_analyze.png", ...])
        widget.clear()
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Range selector
        selector_layout = QHBoxLayout()
        selector_layout.setContentsMargins(4, 4, 4, 0)
        self._lbl_range = QLabel("Range:")
        self._lbl_range.setStyleSheet("color: #cccccc; font-size: 9pt;")
        selector_layout.addWidget(self._lbl_range)
        self._cb_range = QComboBox()
        self._cb_range.setMinimumWidth(250)
        self._cb_range.currentIndexChanged.connect(self._on_range_changed)
        selector_layout.addWidget(self._cb_range)
        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # Matplotlib canvas - no inner scroll area; parent page scrolls
        self._figure = Figure(facecolor="#2a2a2a")
        self._canvas = FigureCanvasQTAgg(self._figure)
        layout.addWidget(self._canvas)

        self._image_paths: list[str] = []
        self._current_image_path: str | None = None
        self._current_image: np.ndarray | None = None
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(100)
        self._resize_timer.timeout.connect(self._refit_image)
        self._lbl_range.hide()
        self._cb_range.hide()
        self._show_placeholder()

    def set_images(self, paths: list[str]) -> None:
        """Set the list of analysis PNG paths and display the first one."""
        self._image_paths = list(paths)
        self._cb_range.blockSignals(True)
        self._cb_range.clear()
        for p in paths:
            label = Path(p).stem.replace("_analyze", "").replace("_", " ")
            self._cb_range.addItem(label)
        self._cb_range.blockSignals(False)

        if paths:
            self._lbl_range.show()
            self._cb_range.show()
            self._cb_range.setCurrentIndex(0)
            self._load_image(paths[0])
        else:
            self.clear()

    def clear(self) -> None:
        """Clear the display and show placeholder."""
        self._image_paths = []
        self._current_image_path = None
        self._current_image = None
        self._cb_range.clear()
        self._lbl_range.hide()
        self._cb_range.hide()
        self._show_placeholder()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._current_image is not None:
            self._resize_timer.start()

    def _show_placeholder(self) -> None:
        """Show a placeholder message on the canvas."""
        self._figure.clear()
        self._figure.set_facecolor("#2a2a2a")
        ax = self._figure.add_axes([0, 0, 1, 1])
        ax.set_facecolor("#2a2a2a")
        ax.text(
            0.5,
            0.5,
            "No analysis data\nRun a fit to generate plots",
            ha="center",
            va="center",
            fontsize=11,
            color="#666666",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
        self._canvas.setMinimumSize(1, 1)
        self._canvas.draw_idle()

    def _on_range_changed(self, index: int) -> None:
        if 0 <= index < len(self._image_paths):
            self._load_image(self._image_paths[index])

    def _load_image(self, path: str) -> None:
        """Load a PNG and display it on the canvas."""
        try:
            img = imread(path)
        except Exception:
            return

        self._current_image_path = path
        self._current_image = img
        self._render_image(img)

    def _render_image(self, img: np.ndarray) -> None:
        """Render the image array onto the canvas, sized to fill available width."""
        self._figure.clear()
        self._figure.set_facecolor("#2a2a2a")
        ax = self._figure.add_axes([0, 0, 1, 1])
        ax.imshow(img)
        ax.set_axis_off()

        h, w = img.shape[:2]
        available_w = self.width()
        if available_w < 100:
            available_w = 800
        scale = available_w / w
        canvas_h = int(h * scale)
        self._canvas.setFixedHeight(canvas_h)
        self._canvas.draw_idle()

    def _refit_image(self) -> None:
        """Re-render the current image after a resize."""
        if self._current_image is not None:
            self._render_image(self._current_image)
