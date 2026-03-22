"""Tests for OperationResult and ChannelConfig frozen dataclasses."""

from dataclasses import FrozenInstanceError

import pytest

from src.logic.controllers.base_controller import ChannelConfig, OperationResult


@pytest.mark.unit
class TestOperationResult:
    """Test the OperationResult immutable dataclass."""

    def test_success_result(self):
        """A successful result should have ok=True."""
        result = OperationResult(ok=True)
        assert result.ok is True

    def test_failure_result_with_message(self):
        """A failed result should carry the error message."""
        result = OperationResult(ok=False, message="Device not found")
        assert result.ok is False
        assert result.message == "Device not found"

    def test_default_serial_none(self):
        """Serial should default to None when not provided."""
        result = OperationResult(ok=True)
        assert result.serial is None

    def test_default_message_empty(self):
        """Message should default to an empty string."""
        result = OperationResult(ok=True)
        assert result.message == ""

    def test_default_data_empty_dict(self):
        """Data should default to an empty dict."""
        result = OperationResult(ok=True)
        assert result.data == {}
        assert isinstance(result.data, dict)

    def test_frozen_raises_on_assignment(self):
        """Assigning to a frozen dataclass field should raise FrozenInstanceError."""
        result = OperationResult(ok=True, message="original")
        with pytest.raises(FrozenInstanceError):
            result.ok = False  # type: ignore[misc]

    def test_data_dict_is_independent_per_instance(self):
        """Each instance should get its own data dict from the default factory."""
        r1 = OperationResult(ok=True)
        r2 = OperationResult(ok=True)
        r1.data["key"] = "value"
        assert "key" not in r2.data

    def test_result_with_all_fields(self):
        """Creating a result with every field set should store them correctly."""
        data = {"temperature": 25.4, "plot": [1, 2, 3]}
        result = OperationResult(ok=True, serial=2503, message="Success", data=data)
        assert result.ok is True
        assert result.serial == 2503
        assert result.message == "Success"
        assert result.data["temperature"] == 25.4
        assert result.data["plot"] == [1, 2, 3]


@pytest.mark.unit
class TestChannelConfig:
    """Test the ChannelConfig immutable dataclass."""

    def test_channel_config_creation(self):
        """All fields should be stored correctly on construction."""
        cfg = ChannelConfig(
            channel_id="AMP1",
            amplifier_type="AMP",
            channel_type="INPUT",
            opamp_type="ADA4898",
            gain=10.0,
            bandwidth=50e6,
            range=1.0,
            unit="V",
        )
        assert cfg.channel_id == "AMP1"
        assert cfg.amplifier_type == "AMP"
        assert cfg.channel_type == "INPUT"
        assert cfg.opamp_type == "ADA4898"
        assert cfg.gain == 10.0
        assert cfg.bandwidth == 50e6
        assert cfg.range == 1.0
        assert cfg.unit == "V"

    def test_channel_config_frozen(self):
        """Assigning to a frozen ChannelConfig field should raise FrozenInstanceError."""
        cfg = ChannelConfig(
            channel_id="AMP2",
            amplifier_type="AMP",
            channel_type="OUTPUT",
            opamp_type="OPA1612",
            gain=5.0,
            bandwidth=80e6,
            range=2.0,
            unit="A",
        )
        with pytest.raises(FrozenInstanceError):
            cfg.gain = 20.0  # type: ignore[misc]
