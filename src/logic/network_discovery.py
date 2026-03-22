"""Network discovery for SCPI and VXI-11 instruments.

Scans the local subnet(s) for instruments responding on common ports
and identifies them via ``*IDN?`` queries.
"""

from __future__ import annotations

import socket
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from src.logging_config import get_logger

logger = get_logger(__name__)

# Common instrument ports
SCPI_RAW_PORT = 5025  # Keithley, R&S, Keysight raw SCPI socket
VXI11_PORT = 111  # VXI-11 portmapper (oscilloscopes)

# Scanning parameters
_CONNECT_TIMEOUT = 0.5  # seconds per host for TCP connect
_QUERY_TIMEOUT = 2.0  # seconds for *IDN? response
_MAX_WORKERS = 64  # parallel scan threads


@dataclass
class DiscoveredInstrument:
    """An instrument found on the network.

    Attributes:
        ip: IP address of the instrument.
        identity: *IDN? response string, or None if identification failed.
        port: Port the instrument was found on.
    """

    ip: str
    identity: str | None
    port: int

    @property
    def display_name(self) -> str:
        """Short display string for GUI dropdowns."""
        if self.identity:
            # *IDN? typically returns: manufacturer,model,serial,firmware
            parts = self.identity.split(",")
            if len(parts) >= 2:
                return f"{parts[0].strip()} {parts[1].strip()} ({self.ip})"
        return self.ip


def get_local_subnets() -> list[str]:
    """Detect /24 subnet prefixes from local network interfaces.

    Returns:
        List of subnet prefixes like ``["192.168.68"]``.
    """
    subnets = set()
    try:
        # Get all local IPs by connecting to a non-routable address
        # This works cross-platform without netifaces
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Connect to a non-routable address to determine default interface
            s.settimeout(0.1)
            try:
                s.connect(("10.255.255.255", 1))
                ip = s.getsockname()[0]
            except OSError:
                ip = "127.0.0.1"

        if ip != "127.0.0.1":
            parts = ip.split(".")
            if len(parts) == 4:
                subnets.add(f"{parts[0]}.{parts[1]}.{parts[2]}")
    except Exception as e:
        logger.debug("Failed to detect local subnet: %s", e)

    # Also try to get all interface IPs via getaddrinfo
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = str(info[4][0])
            if ip.startswith("127."):
                continue
            parts = ip.split(".")
            if len(parts) == 4:
                subnets.add(f"{parts[0]}.{parts[1]}.{parts[2]}")
    except Exception as e:
        logger.debug("Failed to enumerate interfaces: %s", e)

    return list(subnets) if subnets else ["192.168.1"]


def _tcp_connect(ip: str, port: int, timeout: float = _CONNECT_TIMEOUT) -> bool:
    """Check if a TCP port is open on the given IP."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((ip, port))
            return True
    except (TimeoutError, OSError):
        return False


def _query_scpi_raw(
    ip: str, port: int = SCPI_RAW_PORT, timeout: float = _QUERY_TIMEOUT
) -> str | None:
    """Send ``*IDN?`` over a raw TCP socket and return the response."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((ip, port))
            s.sendall(b"*IDN?\n")
            data = s.recv(1024)
            return data.decode("ascii", errors="replace").strip()
    except (TimeoutError, OSError, UnicodeDecodeError):
        return None


def _query_vxi11(ip: str, timeout: float = _QUERY_TIMEOUT) -> str | None:
    """Query ``*IDN?`` via VXI-11 protocol."""
    try:
        import vxi11

        instr = vxi11.Instrument(ip)
        instr.timeout = timeout
        idn = instr.ask("*IDN?")
        instr.close()
        return idn.strip() if idn else None
    except Exception:
        return None


def _scan_host_scpi(ip: str, port: int) -> DiscoveredInstrument | None:
    """Scan a single host for SCPI on the given port.

    Uses a single TCP connection for both port-open check and ``*IDN?`` query.
    A previous two-connection approach (connect-close-reconnect) caused
    instruments that accept only one SCPI connection at a time (e.g. Keithley)
    to refuse the second connection, making the first scan always fail.

    Only returns a result if the host responds with a valid ``*IDN?`` string
    (must contain at least one comma, per IEEE 488.2 format).
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(_CONNECT_TIMEOUT)
            s.connect((ip, port))
            # Port is open - now query *IDN? on the same socket
            s.settimeout(_QUERY_TIMEOUT)
            s.sendall(b"*IDN?\n")
            data = s.recv(1024)
            identity = data.decode("ascii", errors="replace").strip()
    except (TimeoutError, OSError, UnicodeDecodeError):
        return None
    if not identity or "," not in identity:
        return None
    return DiscoveredInstrument(ip=ip, identity=identity, port=port)


def _scan_host_vxi11(ip: str) -> DiscoveredInstrument | None:
    """Scan a single host for VXI-11 instrument."""
    if not _tcp_connect(ip, VXI11_PORT):
        return None
    identity = _query_vxi11(ip)
    if identity:
        return DiscoveredInstrument(ip=ip, identity=identity, port=VXI11_PORT)
    return None


def discover_instruments(
    instrument_type: str = "scpi",
    progress_callback: Callable[[str], None] | None = None,
) -> list[DiscoveredInstrument]:
    """Scan the local network for instruments.

    Args:
        instrument_type: Type of scan to perform:
            - ``"keithley"``: Scan port 5025 for SCPI instruments (Keithley).
            - ``"scope"``: Scan for VXI-11 instruments (oscilloscopes),
              falls back to SCPI port 5025.
            - ``"scpi"``: Scan port 5025 for any SCPI instrument.
        progress_callback: Optional callback receiving status messages.

    Returns:
        List of discovered instruments.
    """
    subnets = get_local_subnets()
    if progress_callback:
        progress_callback(f"Scanning subnets: {', '.join(s + '.0/24' for s in subnets)}")

    results: list[DiscoveredInstrument] = []

    for subnet in subnets:
        hosts = [f"{subnet}.{i}" for i in range(1, 255)]

        if instrument_type == "scope":
            # Try VXI-11 first, then fall back to SCPI
            if progress_callback:
                progress_callback(f"Scanning {subnet}.0/24 for VXI-11 instruments...")
            results.extend(_scan_subnet(hosts, _scan_host_vxi11))

            if not results:
                if progress_callback:
                    progress_callback(f"No VXI-11 found, scanning SCPI port {SCPI_RAW_PORT}...")
                results.extend(_scan_subnet(hosts, lambda ip: _scan_host_scpi(ip, SCPI_RAW_PORT)))
        else:
            # SCPI / Keithley scan
            if progress_callback:
                progress_callback(f"Scanning {subnet}.0/24 on port {SCPI_RAW_PORT}...")
            results.extend(_scan_subnet(hosts, lambda ip: _scan_host_scpi(ip, SCPI_RAW_PORT)))

    # Filter by instrument type - strict, no fallback
    if instrument_type == "keithley":
        results = [r for r in results if r.identity and "keithley" in r.identity.lower()]
    elif instrument_type == "scope":
        results = [r for r in results if r.identity and "keithley" not in r.identity.lower()]

    if progress_callback:
        progress_callback(f"Scan complete. Found {len(results)} instrument(s).")

    return results


def _scan_subnet(
    hosts: list[str],
    scan_fn: Callable[[str], DiscoveredInstrument | None],
) -> list[DiscoveredInstrument]:
    """Scan a list of hosts in parallel using the given scan function."""
    found: list[DiscoveredInstrument] = []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(scan_fn, ip): ip for ip in hosts}
        for future in as_completed(futures):
            try:
                result = future.result()
                if result is not None:
                    found.append(result)
            except Exception as e:
                logger.debug("Scan error for %s: %s", futures[future], e)
    return found
