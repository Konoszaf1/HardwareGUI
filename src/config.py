"""Application configuration with sensible defaults.

Configuration values can be overridden via environment variables
or a config file in future iterations.

Usage:
    from src.config import config

    # Access configuration values
    width = config.ui.sidebar_expanded_width
    ip = config.hardware.default_scope_ip
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class UIConfig:
    """UI-related configuration.

    Attributes:
        sidebar_expanded_width (int): Width of the sidebar when expanded.
        sidebar_collapsed_width (int): Width of the sidebar when collapsed.
        animation_duration_ms (int): Duration of sidebar animations in milliseconds.
        expand_hover_delay_ms (int): Delay before sidebar expands on hover.
        collapse_hover_delay_ms (int): Delay before sidebar collapses on mouse leave.
        window_min_width (int): Minimum window width.
        window_min_height (int): Minimum window height.
        sidebar_button_icon_size (int): Size of icons in sidebar buttons.
        panel_toggle_size (int): Height/Width of the toggle header/bar.
        artifacts_expanded_width (int): Fixed width of the artifacts panel content.
        terminal_expanded_height (int): Default height of the terminal panel content.
        terminal_min_height (int): Minimum height when expanded.
        panel_animation_duration_ms (int): Duration of panel animations.
        panel_animation_easing (str): Easing curve for panel animations.
        max_widget_size (int): Maximum widget size (QWIDGETSIZE_MAX).
    """

    sidebar_expanded_width: int = 250
    sidebar_collapsed_width: int = 70
    animation_duration_ms: int = 500
    expand_hover_delay_ms: int = 10000
    collapse_hover_delay_ms: int = 200
    window_min_width: int = 900
    window_min_height: int = 600
    sidebar_button_icon_size: int = 24

    # Shared Panels
    panel_toggle_size: int = 24
    artifacts_expanded_width: int = 250
    terminal_expanded_height: int = 200
    terminal_min_height: int = 100
    panel_animation_duration_ms: int = 150
    panel_animation_easing: str = "OutCubic"
    max_widget_size: int = 16777215


@dataclass(frozen=True)
class ConsoleConfig:
    """Console widget configuration.

    Attributes:
        max_block_count (int): Maximum lines in the console buffer.
        max_block_count_small (int): Reduced buffer size for constrained environments.
    """

    max_block_count: int = 20000
    max_block_count_small: int = 10000


@dataclass(frozen=True)
class ThumbnailConfig:
    """Artifact thumbnail configuration.

    Attributes:
        icon_size (int): Size of the thumbnail icon (square).
        grid_width (int): Width of the thumbnail grid item.
        grid_height (int): Height of the thumbnail grid item.
        spacing (int): Spacing between grid items.
        refresh_debounce_ms (int): Debounce time for refreshing thumbnails.
    """

    icon_size: int = 128
    grid_width: int = 140
    grid_height: int = 160
    spacing: int = 10
    refresh_debounce_ms: int = 500


@dataclass(frozen=True)
class HardwareConfig:
    """Hardware connection defaults.

    Attributes:
        default_scope_ip (str): Default IP address for the oscilloscope.
        vu_serial_max (int): Maximum value for VU serial number.
        vu_interface_max (int): Maximum value for VU interface ID.
        mcu_serial_max (int): Maximum value for MCU serial number.
        mcu_interface_max (int): Maximum value for MCU interface ID.
    """

    default_scope_ip: str = "192.168.68.154"
    vu_serial_max: int = 9999
    vu_interface_max: int = 99
    mcu_serial_max: int = 9999
    mcu_interface_max: int = 99


@dataclass(frozen=True)
class DialogConfig:
    """Dialog window defaults.

    Attributes:
        image_viewer_width (int): Default width for the image viewer dialog.
        image_viewer_height (int): Default height for the image viewer dialog.
    """

    image_viewer_width: int = 800
    image_viewer_height: int = 600


@dataclass(frozen=True)
class TooltipConfig:
    """Sidebar tooltip configuration.

    Attributes:
        show_delay_ms (int): Delay before showing the tooltip.
        grace_period_ms (int): Time period to keep tooltip active when moving between buttons.
    """

    show_delay_ms: int = 400
    grace_period_ms: int = 300


@dataclass(frozen=True)
class StatusBarConfig:
    """Status bar configuration.

    Attributes:
        default_timeout_ms (int): Default timeout for status messages.
        animation_interval_ms (int): Interval for status bar animations (e.g., dots).
    """

    default_timeout_ms: int = 5000
    animation_interval_ms: int = 500


@dataclass(frozen=True)
class FormLayoutConfig:
    """Form layout and widget sizing configuration.

    Provides consistent sizing for form elements to prevent layout squishing.

    Attributes:
        input_height (int): Minimum height for input widgets (spinbox, combobox, lineedit).
        input_width (int): Minimum width for input widgets.
        button_height (int): Standard button height.
        button_height_large (int): Large button height (e.g., primary actions).
        radio_height (int): Height for radio buttons and checkboxes.
        label_height (int): Height for labels.
        group_padding (tuple): Padding inside group boxes (left, top, right, bottom).
        form_spacing (int): Vertical spacing between form rows.
        layout_spacing (int): Spacing between major layout sections.
        content_min_width (int): Minimum width for scrollable content.
        group_min_height (int): Default minimum height for group boxes.
    """

    input_height: int = 32
    input_width: int = 120
    button_height: int = 32
    button_height_large: int = 40
    radio_height: int = 28
    label_height: int = 28
    group_padding: tuple[int, int, int, int] = (5, 5, 5, 5)
    form_spacing: int = 5
    layout_spacing: int = 5
    content_min_width: int = 500
    group_min_height: int = 100


@dataclass(frozen=True)
class AppConfig:
    """Root application configuration.

    Groups all configuration categories and provides optional
    environment variable overrides for logging settings.

    Attributes:
        ui (UIConfig): UI configuration.
        console (ConsoleConfig): Console configuration.
        thumbnails (ThumbnailConfig): Thumbnail configuration.
        hardware (HardwareConfig): Hardware configuration.
        dialogs (DialogConfig): Dialog configuration.
        tooltip (TooltipConfig): Tooltip configuration.
        status_bar (StatusBarConfig): Status bar configuration.
        form (FormLayoutConfig): Form layout configuration.
        log_level (str): Logging level (e.g., "INFO", "DEBUG").
        log_file (str | None): Path to the log file, or None if logging to stdout.
    """

    ui: UIConfig = field(default_factory=UIConfig)
    console: ConsoleConfig = field(default_factory=ConsoleConfig)
    thumbnails: ThumbnailConfig = field(default_factory=ThumbnailConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    dialogs: DialogConfig = field(default_factory=DialogConfig)
    tooltip: TooltipConfig = field(default_factory=TooltipConfig)
    status_bar: StatusBarConfig = field(default_factory=StatusBarConfig)
    form: FormLayoutConfig = field(default_factory=FormLayoutConfig)

    # Logging configuration (can be overridden by env vars)
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: str | None = field(default_factory=lambda: os.getenv("LOG_FILE"))


# Global singleton instance
config = AppConfig()
