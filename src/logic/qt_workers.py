"""Used to wrap dpi scripts and redirect stdout and stderr to the application."""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

try:
    import matplotlib

    matplotlib.use("Agg", force=True)
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False

from src.logging_config import get_logger

logger = get_logger(__name__)


class TaskSignals(QObject):
    """Signals emitted by ``FunctionTask`` during its lifecycle.

    Attributes:
        started: Emitted when the task begins execution.
        log: Emitted with a log line captured from stdout/stderr.
        progress: Emitted with (fraction, message) for progress updates.
        artifact: Emitted with the path of a newly created artifact.
        finished: Emitted with a ``TaskResult`` when the task completes.
        error: Emitted with an error message string on failure.
    """

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
    """Immutable result payload emitted by ``FunctionTask.signals.finished``.

    Attributes:
        name: Human-readable task name.
        ok: Whether the task completed without error.
        data: Arbitrary result data returned by the task callable.
    """

    name: str
    ok: bool
    data: Any | None = None


class FunctionTask(QRunnable):
    """Run a function in a worker thread with stdout/stderr capture and signals."""

    def __init__(self, name: str, fn: Callable[[], Any]):
        super().__init__()
        self.name = name
        self.fn = fn
        self.signals = TaskSignals()

    def run(self) -> None:
        # Log if matplotlib was not available at import time
        if not _MATPLOTLIB_AVAILABLE:
            logger.debug("Matplotlib not available - Agg backend not configured")

        # Redirect stdout/stderr to log signal for the duration of the task
        out_stream = _EmittingStream(lambda s: self.signals.log.emit(s))
        err_stream = _EmittingStream(lambda s: self.signals.log.emit(f"[stderr] {s}"))

        try:
            self.signals.started.emit()
            with redirect_stdout(out_stream), redirect_stderr(err_stream):
                result = self.fn()
            logger.debug("Task %s finished execution, emitting signal", self.name)
            self.signals.finished.emit(TaskResult(self.name, True, result))
        except Exception as e:
            logger.error("Task %s failed: %s", self.name, e, exc_info=True)
            self.signals.error.emit(f"{self.name} failed: {e}")
            self.signals.finished.emit(TaskResult(self.name, False, None))
        finally:
            try:
                out_stream.flush()
                err_stream.flush()
            except Exception as e:
                logger.debug("Stream flush failed (expected during cleanup): %s", e)


def make_task(name: str, fn: Callable[[], Any]) -> FunctionTask:
    """Create a ``FunctionTask`` with the given name and callable.

    Args:
        name: Human-readable task name.
        fn: Zero-argument callable executed in a worker thread.

    Returns:
        A new ``FunctionTask`` ready to be submitted.
    """
    return FunctionTask(name, fn)


def run_in_thread(task: FunctionTask) -> TaskSignals:
    """Submit a ``FunctionTask`` to the global ``QThreadPool``.

    Args:
        task: The task to execute.

    Returns:
        The task's ``TaskSignals`` instance for connecting slots.
    """
    QThreadPool.globalInstance().start(task)
    return task.signals
