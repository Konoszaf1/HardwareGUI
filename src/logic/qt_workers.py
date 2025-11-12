from __future__ import annotations

import io
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class TaskSignals(QObject):
    started = Signal()
    log = Signal(str)
    progress = Signal(float, str)
    artifact = Signal(str)
    finished = Signal(object)
    error = Signal(str)


class _EmittingStream(io.TextIOBase):
    """A text stream that emits written chunks via a signal.

    We buffer until a newline or flush is requested to avoid overwhelming the UI.
    """

    def __init__(self, emit_fn: Callable[[str], None]):
        super().__init__()
        self._emit = emit_fn
        self._buf = ""

    def writable(self) -> bool:  # type: ignore[override]
        return True

    def write(self, s: str) -> int:  # type: ignore[override]
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line:
                self._emit(line)
            else:
                self._emit("")
        return len(s)

    def flush(self) -> None:  # type: ignore[override]
        if self._buf:
            self._emit(self._buf)
            self._buf = ""


@dataclass
class TaskResult:
    name: str
    ok: bool
    data: Optional[Any] = None


class FunctionTask(QRunnable):
    """Run a function in a worker thread with stdout/stderr capture and signals."""

    def __init__(self, name: str, fn: Callable[[], Any]):
        super().__init__()
        self.name = name
        self.fn = fn
        self.signals = TaskSignals()

    def run(self) -> None:  # noqa: D401
        # Configure non-interactive matplotlib to avoid blocking UI if imported here
        try:
            import matplotlib
            matplotlib.use("Agg", force=True)
        except Exception:
            pass

        # Redirect stdout/stderr to log signal for the duration of the task
        old_out, old_err = sys.stdout, sys.stderr
        out_stream = _EmittingStream(lambda s: self.signals.log.emit(s))
        err_stream = _EmittingStream(lambda s: self.signals.log.emit(f"[stderr] {s}"))
        sys.stdout, sys.stderr = out_stream, err_stream
        try:
            self.signals.started.emit()
            result = self.fn()
            self.signals.finished.emit(TaskResult(self.name, True, result))
        except Exception as e:  # noqa: BLE001
            self.signals.error.emit(f"{self.name} failed: {e}")
            self.signals.finished.emit(TaskResult(self.name, False, None))
        finally:
            try:
                out_stream.flush()
                err_stream.flush()
            except Exception:
                pass
            sys.stdout, sys.stderr = old_out, old_err


def run_in_thread(name: str, fn: Callable[[], Any]) -> TaskSignals:
    """Submit a function to the global QThreadPool and return its TaskSignals."""
    task = FunctionTask(name, fn)
    QThreadPool.globalInstance().start(task)
    return task.signals
