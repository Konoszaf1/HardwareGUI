"""Component tests for LivePlotWidget.

Tests append_point, plot_batch, clear, and set_labels on the
matplotlib-based live plot widget.
"""

import pytest

from src.gui.widgets.live_plot_widget import LivePlotWidget

pytestmark = pytest.mark.component


@pytest.fixture
def plot_widget(qtbot) -> LivePlotWidget:
    """Create a LivePlotWidget and register with qtbot."""
    w = LivePlotWidget()
    qtbot.addWidget(w)
    return w


class TestLivePlotWidgetInit:
    """Tests for LivePlotWidget initialization."""

    def test_widget_creates_successfully(self, plot_widget):
        """Widget instantiates without error."""
        assert plot_widget is not None

    def test_widget_has_canvas(self, plot_widget):
        """Widget contains a matplotlib canvas."""
        assert plot_widget._canvas is not None

    def test_widget_has_axes(self, plot_widget):
        """Widget has a matplotlib Axes object."""
        assert plot_widget._ax is not None


class TestLivePlotWidgetSetLabels:
    """Tests for set_labels method."""

    def test_set_labels_updates_title(self, plot_widget):
        """set_labels updates the plot title."""
        plot_widget.set_labels("My Title", "X Axis", "Y Axis")

        assert plot_widget._ax.get_title() == "My Title"

    def test_set_labels_updates_xlabel(self, plot_widget):
        """set_labels updates the x-axis label."""
        plot_widget.set_labels("Title", "X Label", "Y Label")

        assert plot_widget._ax.get_xlabel() == "X Label"

    def test_set_labels_updates_ylabel(self, plot_widget):
        """set_labels updates the y-axis label."""
        plot_widget.set_labels("Title", "X", "Y Label")

        assert plot_widget._ax.get_ylabel() == "Y Label"


class TestLivePlotWidgetAppendPoint:
    """Tests for append_point (scatter) method."""

    def test_append_point_creates_series(self, plot_widget):
        """First append_point for a series creates it."""
        plot_widget.append_point("CH1", 1.0, 2.0)

        assert "CH1" in plot_widget._series

    def test_append_point_stores_coordinates(self, plot_widget):
        """Appended point is stored in the series data."""
        plot_widget.append_point("CH1", 1.0, 2.0)

        assert plot_widget._series["CH1"]["x"] == [1.0]
        assert plot_widget._series["CH1"]["y"] == [2.0]

    def test_append_point_multiple_points(self, plot_widget):
        """Multiple appends accumulate in the series."""
        plot_widget.append_point("CH1", 1.0, 2.0)
        plot_widget.append_point("CH1", 3.0, 4.0)

        assert len(plot_widget._series["CH1"]["x"]) == 2

    def test_append_point_different_series(self, plot_widget):
        """Different series names create separate series."""
        plot_widget.append_point("CH1", 1.0, 2.0)
        plot_widget.append_point("CH2", 3.0, 4.0)

        assert "CH1" in plot_widget._series
        assert "CH2" in plot_widget._series


class TestLivePlotWidgetPlotBatch:
    """Tests for plot_batch (line) method."""

    def test_plot_batch_creates_line(self, plot_widget):
        """plot_batch creates a line on the axes."""
        plot_widget.plot_batch([0, 1, 2], [0, 1, 4], series="test")

        assert "test" in plot_widget._series

    def test_plot_batch_stores_data(self, plot_widget):
        """plot_batch stores x/y data in the series."""
        x = [0, 1, 2, 3]
        y = [0, 1, 4, 9]
        plot_widget.plot_batch(x, y, series="curve")

        assert plot_widget._series["curve"]["x"] == x
        assert plot_widget._series["curve"]["y"] == y

    def test_plot_batch_with_custom_linestyle(self, plot_widget):
        """plot_batch accepts linestyle parameter."""
        plot_widget.plot_batch([0, 1], [0, 1], series="dashed", linestyle="--")

        assert "dashed" in plot_widget._series

    def test_plot_batch_with_alpha(self, plot_widget):
        """plot_batch accepts alpha parameter."""
        plot_widget.plot_batch([0, 1], [0, 1], series="faded", alpha=0.5)

        assert "faded" in plot_widget._series


class TestLivePlotWidgetClear:
    """Tests for clear method."""

    def test_clear_removes_all_series(self, plot_widget):
        """clear removes all series data."""
        plot_widget.append_point("CH1", 1.0, 2.0)
        plot_widget.append_point("CH2", 3.0, 4.0)

        plot_widget.clear()

        assert len(plot_widget._series) == 0

    def test_clear_on_empty_widget_is_safe(self, plot_widget):
        """clear on empty widget doesn't crash."""
        plot_widget.clear()  # Should not raise

    def test_clear_then_append_works(self, plot_widget):
        """Appending after clear works normally."""
        plot_widget.append_point("CH1", 1.0, 2.0)
        plot_widget.clear()
        plot_widget.append_point("CH1", 5.0, 6.0)

        assert len(plot_widget._series["CH1"]["x"]) == 1
        assert plot_widget._series["CH1"]["x"] == [5.0]
