"""Tests for src/config.py — frozen dataclass configuration hierarchy."""

from __future__ import annotations

import dataclasses

import pytest

from src.config import AppConfig, FormLayoutConfig, HardwareConfig, UIConfig, config


# ---------------------------------------------------------------------------
# TestUIConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUIConfig:
    """Tests for UIConfig default values and immutability."""

    def test_default_values(self):
        """UIConfig fields have the expected default values."""
        ui = UIConfig()

        assert ui.sidebar_expanded_width == 250
        assert ui.sidebar_collapsed_width == 70
        assert ui.animation_duration_ms == 500
        assert ui.window_min_width == 900
        assert ui.window_min_height == 600
        assert ui.sidebar_button_icon_size == 36

    def test_frozen_immutable(self):
        """UIConfig raises FrozenInstanceError on attribute assignment."""
        ui = UIConfig()

        with pytest.raises(dataclasses.FrozenInstanceError):
            ui.sidebar_expanded_width = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestAppConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAppConfig:
    """Tests for AppConfig root configuration including env-var overrides."""

    def test_default_log_level_is_info(self, monkeypatch):
        """Default log_level is INFO when LOG_LEVEL env var is unset."""
        monkeypatch.delenv("LOG_LEVEL", raising=False)

        app = AppConfig()

        assert app.log_level == "INFO"

    def test_log_level_from_env_var(self, monkeypatch):
        """log_level reads from the LOG_LEVEL environment variable."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        app = AppConfig()

        assert app.log_level == "DEBUG"

    def test_log_file_default_none(self, monkeypatch):
        """log_file defaults to None when LOG_FILE env var is unset."""
        monkeypatch.delenv("LOG_FILE", raising=False)

        app = AppConfig()

        assert app.log_file is None

    def test_log_file_from_env_var(self, monkeypatch):
        """log_file reads from the LOG_FILE environment variable."""
        monkeypatch.setenv("LOG_FILE", "/tmp/test.log")

        app = AppConfig()

        assert app.log_file == "/tmp/test.log"

    def test_nested_config_access(self):
        """Nested config objects are accessible through dot notation."""
        app = AppConfig()

        assert isinstance(app.ui, UIConfig)
        assert isinstance(app.hardware, HardwareConfig)
        assert isinstance(app.form, FormLayoutConfig)

    def test_frozen_raises_on_assignment(self):
        """AppConfig raises FrozenInstanceError on attribute assignment."""
        app = AppConfig()

        with pytest.raises(dataclasses.FrozenInstanceError):
            app.log_level = "DEBUG"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestGlobalConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGlobalConfig:
    """Tests for the module-level config singleton."""

    def test_config_singleton_is_app_config(self):
        """The global config object is an AppConfig instance."""
        assert isinstance(config, AppConfig)

    def test_config_hardware_defaults(self):
        """The global config has expected hardware default values."""
        assert config.hardware.default_scope_ip == "192.168.68.154"
        assert config.hardware.vu_serial_max == 9999
        assert config.hardware.vu_interface_max == 99
        assert config.hardware.mcu_serial_max == 9999
        assert config.hardware.mcu_interface_max == 99


# ---------------------------------------------------------------------------
# TestFormLayoutConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormLayoutConfig:
    """Tests for FormLayoutConfig sizing defaults."""

    def test_default_group_padding(self):
        """group_padding defaults to (5, 5, 5, 5)."""
        form = FormLayoutConfig()

        assert form.group_padding == (5, 5, 5, 5)

    def test_default_input_height(self):
        """input_height defaults to 32."""
        form = FormLayoutConfig()

        assert form.input_height == 32
