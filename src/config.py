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
    """UI-related configuration."""

    sidebar_expanded_width: int = 250
    sidebar_collapsed_width: int = 50
    animation_duration_ms: int = 500
    expand_hover_delay_ms: int = 10000
    collapse_hover_delay_ms: int = 200
    window_min_width: int = 900
    window_min_height: int = 600
    sidebar_button_icon_size: int = 24


@dataclass(frozen=True)
class ConsoleConfig:
    """Console widget configuration."""

    max_block_count: int = 20000
    max_block_count_small: int = 10000


@dataclass(frozen=True)
class ThumbnailConfig:
    """Artifact thumbnail configuration."""

    icon_size: int = 128
    grid_width: int = 140
    grid_height: int = 160
    spacing: int = 10
    refresh_debounce_ms: int = 500


@dataclass(frozen=True)
class HardwareConfig:
    """Hardware connection defaults."""

    default_scope_ip: str = "192.168.68.154"
    vu_serial_max: int = 9999
    vu_interface_max: int = 99
    mcu_serial_max: int = 9999
    mcu_interface_max: int = 99


@dataclass(frozen=True)
class DialogConfig:
    """Dialog window defaults."""

    image_viewer_width: int = 800
    image_viewer_height: int = 600


@dataclass(frozen=True)
class TooltipConfig:
    """Sidebar tooltip configuration."""

    show_delay_ms: int = 400
    grace_period_ms: int = 300


@dataclass
class AppConfig:
    """Root application configuration.

    Groups all configuration categories and provides optional
    environment variable overrides for logging settings.
    """

    ui: UIConfig = field(default_factory=UIConfig)
    console: ConsoleConfig = field(default_factory=ConsoleConfig)
    thumbnails: ThumbnailConfig = field(default_factory=ThumbnailConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    dialogs: DialogConfig = field(default_factory=DialogConfig)
    tooltip: TooltipConfig = field(default_factory=TooltipConfig)

    # Logging configuration (can be overridden by env vars)
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: str | None = field(default_factory=lambda: os.getenv("LOG_FILE"))


# Global singleton instance
config = AppConfig()
