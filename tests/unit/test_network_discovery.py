"""Tests for network discovery of SCPI and VXI-11 instruments."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from src.logic.network_discovery import (
    DiscoveredInstrument,
    _query_scpi_raw,
    _scan_host_scpi,
    _tcp_connect,
    discover_instruments,
    get_local_subnets,
)


# ---------------------------------------------------------------------------
# DiscoveredInstrument
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoveredInstrument:
    """Test the DiscoveredInstrument dataclass and its display_name property."""

    def test_display_name_with_identity(self):
        """display_name should show manufacturer, model, and IP when IDN has >= 2 parts."""
        instr = DiscoveredInstrument(
            ip="192.168.1.10",
            identity="KEITHLEY INSTRUMENTS,MODEL 2450,04560001,1.7.0b",
            port=5025,
        )
        name = instr.display_name
        assert "KEITHLEY INSTRUMENTS" in name
        assert "MODEL 2450" in name
        assert "192.168.1.10" in name

    def test_display_name_without_identity(self):
        """display_name should fall back to bare IP when identity is None."""
        instr = DiscoveredInstrument(ip="10.0.0.5", identity=None, port=5025)
        assert instr.display_name == "10.0.0.5"

    def test_display_name_short_identity(self):
        """display_name should fall back to bare IP when identity has no comma."""
        instr = DiscoveredInstrument(ip="10.0.0.5", identity="UNKNOWN", port=5025)
        assert instr.display_name == "10.0.0.5"


# ---------------------------------------------------------------------------
# get_local_subnets
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetLocalSubnets:
    """Test local subnet detection."""

    def test_returns_list_of_strings(self):
        """get_local_subnets should always return a list of strings."""
        result = get_local_subnets()
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_fallback_when_no_interfaces(self):
        """Should return the fallback subnet when all socket calls fail."""
        with (
            patch("src.logic.network_discovery.socket.socket") as mock_cls,
            patch("src.logic.network_discovery.socket.gethostname", side_effect=OSError),
            patch("src.logic.network_discovery.socket.getaddrinfo", side_effect=OSError),
        ):
            mock_cls.side_effect = OSError("no interfaces")
            result = get_local_subnets()

        assert result == ["192.168.1"]


# ---------------------------------------------------------------------------
# _tcp_connect
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTcpConnect:
    """Test low-level TCP connectivity check."""

    def test_successful_connection(self):
        """Should return True when the socket connects without error."""
        with patch("src.logic.network_discovery.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_sock.connect.return_value = None

            assert _tcp_connect("192.168.1.1", 5025) is True

    def test_connection_refused(self):
        """Should return False when the connection is refused."""
        with patch("src.logic.network_discovery.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_sock.connect.side_effect = ConnectionRefusedError

            assert _tcp_connect("192.168.1.1", 5025) is False

    def test_connection_timeout(self):
        """Should return False when the connection times out."""
        with patch("src.logic.network_discovery.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_sock.connect.side_effect = socket.timeout

            assert _tcp_connect("192.168.1.1", 5025) is False


# ---------------------------------------------------------------------------
# _query_scpi_raw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestQueryScpiRaw:
    """Test raw SCPI *IDN? query over TCP."""

    def test_successful_query(self):
        """Should return the decoded IDN string on success."""
        with patch("src.logic.network_discovery.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_sock.recv.return_value = b"KEITHLEY INSTRUMENTS,MODEL 2450,04560001,1.7.0b\n"

            result = _query_scpi_raw("192.168.1.10", port=5025)

        assert result == "KEITHLEY INSTRUMENTS,MODEL 2450,04560001,1.7.0b"
        mock_sock.sendall.assert_called_once_with(b"*IDN?\n")

    def test_query_timeout_returns_none(self):
        """Should return None when the socket times out."""
        with patch("src.logic.network_discovery.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_sock.connect.side_effect = socket.timeout

            result = _query_scpi_raw("192.168.1.10")

        assert result is None


# ---------------------------------------------------------------------------
# _scan_host_scpi
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanHostScpi:
    """Test single-host SCPI scanner."""

    def test_finds_instrument_with_valid_idn(self):
        """Should return a DiscoveredInstrument when the IDN has a comma."""
        idn = b"KEITHLEY INSTRUMENTS,MODEL 2450,04560001,1.7.0b\n"
        with patch("src.logic.network_discovery.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_sock.recv.return_value = idn

            result = _scan_host_scpi("192.168.1.10", 5025)

        assert result is not None
        assert result.ip == "192.168.1.10"
        assert "KEITHLEY" in result.identity
        assert result.port == 5025

    def test_returns_none_when_no_comma_in_idn(self):
        """Should return None when the IDN response lacks a comma."""
        with patch("src.logic.network_discovery.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_sock.recv.return_value = b"NOCOMMAHERE\n"

            result = _scan_host_scpi("192.168.1.10", 5025)

        assert result is None

    def test_returns_none_on_connection_error(self):
        """Should return None when the TCP connection fails."""
        with patch("src.logic.network_discovery.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_sock.connect.side_effect = ConnectionRefusedError

            result = _scan_host_scpi("192.168.1.10", 5025)

        assert result is None


# ---------------------------------------------------------------------------
# discover_instruments
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoverInstruments:
    """Test the top-level discovery orchestrator."""

    def _keithley_instrument(self, ip: str) -> DiscoveredInstrument:
        """Helper: build a Keithley DiscoveredInstrument."""
        return DiscoveredInstrument(
            ip=ip,
            identity="KEITHLEY INSTRUMENTS,MODEL 2450,04560001,1.7.0b",
            port=5025,
        )

    def _scope_instrument(self, ip: str) -> DiscoveredInstrument:
        """Helper: build a scope DiscoveredInstrument."""
        return DiscoveredInstrument(
            ip=ip,
            identity="RIGOL TECHNOLOGIES,DS1054Z,DS1ZA0000001,00.04.04",
            port=5025,
        )

    def test_scpi_scan_finds_instruments(self):
        """SCPI scan should return all instruments found by _scan_subnet."""
        instruments = [self._keithley_instrument("192.168.1.10")]
        with (
            patch("src.logic.network_discovery.get_local_subnets", return_value=["192.168.1"]),
            patch("src.logic.network_discovery._scan_subnet", return_value=instruments),
        ):
            results = discover_instruments(instrument_type="scpi")

        assert len(results) == 1
        assert results[0].ip == "192.168.1.10"

    def test_keithley_filter(self):
        """Keithley scan should keep only instruments whose IDN contains 'keithley'."""
        instruments = [
            self._keithley_instrument("192.168.1.10"),
            self._scope_instrument("192.168.1.20"),
        ]
        with (
            patch("src.logic.network_discovery.get_local_subnets", return_value=["192.168.1"]),
            patch("src.logic.network_discovery._scan_subnet", return_value=instruments),
        ):
            results = discover_instruments(instrument_type="keithley")

        assert len(results) == 1
        assert "KEITHLEY" in results[0].identity

    def test_scope_filter(self):
        """Scope scan should exclude instruments whose IDN contains 'keithley'."""
        instruments = [
            self._keithley_instrument("192.168.1.10"),
            self._scope_instrument("192.168.1.20"),
        ]
        with (
            patch("src.logic.network_discovery.get_local_subnets", return_value=["192.168.1"]),
            patch("src.logic.network_discovery._scan_subnet", return_value=instruments),
        ):
            results = discover_instruments(instrument_type="scope")

        assert len(results) == 1
        assert "RIGOL" in results[0].identity

    def test_progress_callback_called(self):
        """The progress callback should be invoked at least for start and completion."""
        callback = MagicMock()
        with (
            patch("src.logic.network_discovery.get_local_subnets", return_value=["192.168.1"]),
            patch("src.logic.network_discovery._scan_subnet", return_value=[]),
        ):
            discover_instruments(instrument_type="scpi", progress_callback=callback)

        assert callback.call_count >= 2
        # First call: "Scanning subnets: ..."
        first_msg = callback.call_args_list[0][0][0]
        assert "Scanning subnets" in first_msg
        # Last call: "Scan complete. ..."
        last_msg = callback.call_args_list[-1][0][0]
        assert "Scan complete" in last_msg
