"""Service protocols for type-safe page-service contracts.

These protocols define the minimum interface each page expects from its service.
They allow type checkers to verify that a page is only used with a compatible
service, without requiring inheritance.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.logic.qt_workers import FunctionTask


@runtime_checkable
class ConnectableService(Protocol):
    """Base protocol for any service that can connect and be pinged."""

    def set_instrument_ip(self, ip: str) -> None: ...
    def ping_instrument(self) -> bool: ...
    def set_instrument_verified(self, verified: bool) -> None: ...

    @property
    def connected(self) -> bool: ...

    @property
    def is_instrument_verified(self) -> bool: ...


@runtime_checkable
class MeasurementCapable(ConnectableService, Protocol):
    """Protocol for services that support measurement operations.

    Used by SU and SMU test pages.
    """

    def run_temperature_read(self) -> FunctionTask: ...


@runtime_checkable
class CalibrationCapable(ConnectableService, Protocol):
    """Protocol for services that support calibration operations.

    Used by SU and SMU calibration pages.
    """

    def run_calibration_measure(self, **kwargs) -> FunctionTask | None: ...
    def run_calibration_fit(self, **kwargs) -> FunctionTask | None: ...

    @property
    def artifact_dir(self) -> str: ...
