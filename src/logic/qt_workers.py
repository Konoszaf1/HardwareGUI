"""Used to wrap dpi scripts and redirect stdout and stderr to the application"""
from __future__ import annotations

import io
import sys
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

    The stream is buffered until a newline is encountered, at which point it is emitted.
    """

    def __init__(self, emit_fn: Callable[[str], None]):
        super().__init__()
        self._emit = emit_fn
        self._buf = ""

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line:
                self._emit(line)
            else:
                self._emit("")
        return len(s)

    def flush(self) -> None:
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

    def run(self) -> None:
        # Configure non-interactive matplotlib to avoid blocking UI if imported here
        try:
            import matplotlib
            matplotlib.use("Agg", force=True)
        except Exception:
            pass

        # Redirect stdout/stderr to log signal for the duration of the task
        from contextlib import redirect_stdout, redirect_stderr
        
        out_stream = _EmittingStream(lambda s: self.signals.log.emit(s))
        err_stream = _EmittingStream(lambda s: self.signals.log.emit(f"[stderr] {s}"))
        
        try:
            self.signals.started.emit()
            with redirect_stdout(out_stream), redirect_stderr(err_stream):
                result = self.fn()
            print(f"DEBUG: Task {self.name} finished execution, emitting signal")
            self.signals.finished.emit(TaskResult(self.name, True, result))
        except Exception as e:
            self.signals.error.emit(f"{self.name} failed: {e}")
            self.signals.finished.emit(TaskResult(self.name, False, None))
        finally:
            try:
                out_stream.flush()
                err_stream.flush()
            except Exception:
                pass

def make_task(name: str, fn: Callable[[], Any]) -> FunctionTask:
    return FunctionTask(name, fn)

def run_in_thread(task: FunctionTask) -> TaskSignals:
    """Submit a function to the global QThreadPool and return its TaskSignals."""
    QThreadPool.globalInstance().start(task)
    return task.signals
