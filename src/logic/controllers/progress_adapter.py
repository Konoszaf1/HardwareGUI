"""Progress adapter base for calibration measurement progress.

Mimics tqdm interface to redirect DPI calibration progress to GUI callbacks.
Shared by SMU and SU controllers.
"""

import re
import time
from collections.abc import Callable
from typing import Any


class CalibrationProgressAdapter:
    """Base progress adapter that mimics tqdm for calibration progress.

    Subclasses must implement ``_build_point_data`` and ``_parse_desc``
    to customise the data emitted for each measured point and range.
    """

    def __init__(
        self,
        total: int,
        scm: Any,
        on_point: Callable[[dict], None] | None,
        on_range: Callable[[dict], None] | None,
        verify: bool = False,
    ) -> None:
        self.total = total
        self.n = 0
        self._scm = scm
        self._on_point = on_point
        self._on_range = on_range
        self._verify = verify
        self._current_desc = ""
        self._range_points = 0
        self._range_start = 0.0

    def update(self, n: int = 1) -> None:
        self.n += n
        self._range_points += n
        if self._on_point and self._scm.data:
            point_data = self._build_point_data(self._scm.data[-1])
            if point_data is not None:
                self._on_point(point_data)

    def _build_point_data(self, df: Any) -> dict | None:
        """Build the data dict emitted for each measured point.

        Args:
            df: The last DataFrame from scm.data.

        Returns:
            Dict to emit via on_point, or None to skip.
        """
        raise NotImplementedError

    @staticmethod
    def _parse_desc(desc: str) -> dict:
        """Extract range metadata from a description string.

        Returns:
            Dict with parsed fields, or empty dict.
        """
        raise NotImplementedError

    def _range_trigger_key(self) -> str:
        """Return the dict key that must be present to emit a range-running event.

        Defaults to "pa" for SMU compatibility. Override for SU.
        """
        return "pa"

    def set_description(self, desc: str) -> None:
        if desc != self._current_desc:
            if self._current_desc and self._on_range:
                self._on_range(self._done_data(self._current_desc))
            self._current_desc = desc
            self._range_points = 0
            self._range_start = time.time()
            if self._on_range:
                running_data: dict[str, Any] = {
                    "type": "cal_range",
                    "status": "running",
                    "verify": self._verify,
                }
                running_data.update(self._parse_desc(desc))
                if self._range_trigger_key() in running_data:
                    self._on_range(running_data)

    def close(self) -> None:
        if self._current_desc and self._on_range:
            self._on_range(self._done_data(self._current_desc))

    def _done_data(self, desc: str) -> dict[str, Any]:
        elapsed = time.time() - self._range_start
        data: dict[str, Any] = {
            "type": "cal_range",
            "status": "done",
            "desc": desc,
            "verify": self._verify,
            "points": self._range_points,
            "duration": elapsed,
        }
        data.update(self._parse_desc(desc))
        return data


class SMUProgressAdapter(CalibrationProgressAdapter):
    """SMU-specific progress adapter."""

    def _build_point_data(self, df: Any) -> dict | None:
        return {
            "type": "cal_point",
            "vsmu": df.attrs.get("vsmu_mode"),
            "pa": df.attrs.get("pa_channel"),
            "iv": df.attrs.get("iv_channel"),
            "verify": self._verify,
            "x": float(df.attrs.get("i_ref", 0)),
            "y": float(df["current"].mean()),
            "i_set": float(df.attrs.get("i_set", 0)),
            "point_index": self.n,
            "total_points": self.total,
        }

    @staticmethod
    def _parse_desc(desc: str) -> dict:
        m = re.match(r"PA: (\w+), IV: (\w+), VSMU: (\w+)", desc)
        if m:
            return {"pa": m.group(1), "iv": m.group(2), "vsmu": m.group(3) == "True"}
        return {}


class SUProgressAdapter(CalibrationProgressAdapter):
    """SU-specific progress adapter."""

    def _build_point_data(self, df: Any) -> dict | None:
        return {
            "type": "cal_point",
            "amp_channel": df.attrs.get("amp_channel"),
            "verify": self._verify,
            "x": float(df.attrs.get("v_ref", 0)),
            "y": float(df["voltage"].mean()),
            "v_set": float(df.attrs.get("v_set", 0)),
            "point_index": self.n,
            "total_points": self.total,
        }

    @staticmethod
    def _parse_desc(desc: str) -> dict:
        m = re.match(r"AMP:\s*(\w+)", desc)
        if m:
            return {"amp_channel": m.group(1)}
        return {}

    def _range_trigger_key(self) -> str:
        return "amp_channel"
