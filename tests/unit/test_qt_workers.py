"""Tests for src/logic/qt_workers.py — TaskSignals, _EmittingStream, TaskResult, FunctionTask."""

from __future__ import annotations


import pytest

from src.logic.qt_workers import (
    FunctionTask,
    TaskResult,
    TaskSignals,
    _EmittingStream,
    make_task,
    run_in_thread,
)


# ---------------------------------------------------------------------------
# TestEmittingStream
# ---------------------------------------------------------------------------


@pytest.mark.component
class TestEmittingStream:
    """Tests for the _EmittingStream line-buffered text stream."""

    def test_write_emits_complete_lines(self):
        """Complete lines (terminated by newline) are emitted immediately."""
        emitted: list[str] = []
        stream = _EmittingStream(emitted.append)

        stream.write("hello\n")

        assert emitted == ["hello"]

    def test_write_buffers_partial_lines(self):
        """Partial lines without a newline are buffered, not emitted."""
        emitted: list[str] = []
        stream = _EmittingStream(emitted.append)

        stream.write("partial")

        assert emitted == []

    def test_flush_emits_remaining_buffer(self):
        """Flushing emits whatever is left in the internal buffer."""
        emitted: list[str] = []
        stream = _EmittingStream(emitted.append)

        stream.write("leftover")
        stream.flush()

        assert emitted == ["leftover"]

    def test_writable_returns_true(self):
        """The stream reports itself as writable."""
        stream = _EmittingStream(lambda s: None)

        result = stream.writable()

        assert result is True

    def test_write_returns_length(self):
        """write() returns the number of characters written."""
        stream = _EmittingStream(lambda s: None)

        result = stream.write("five!\n")

        assert result == 6


# ---------------------------------------------------------------------------
# TestTaskResult
# ---------------------------------------------------------------------------


@pytest.mark.component
class TestTaskResult:
    """Tests for the TaskResult dataclass."""

    def test_task_result_creation(self):
        """TaskResult stores name, ok, and data fields."""
        result = TaskResult(name="test_op", ok=True, data={"key": "value"})

        assert result.name == "test_op"
        assert result.ok is True
        assert result.data == {"key": "value"}

    def test_task_result_defaults(self):
        """TaskResult.data defaults to None when not provided."""
        result = TaskResult(name="op", ok=False)

        assert result.data is None

    def test_task_result_with_data(self):
        """TaskResult correctly carries arbitrary dict payloads."""
        payload = {"plot": [1, 2, 3], "status": "done"}

        result = TaskResult(name="plot_task", ok=True, data=payload)

        assert result.data is payload


# ---------------------------------------------------------------------------
# TestFunctionTask
# ---------------------------------------------------------------------------


@pytest.mark.component
class TestFunctionTask:
    """Tests for FunctionTask QRunnable execution and signal emission."""

    def test_run_emits_started_signal(self, qtbot):
        """Calling run() emits the started signal before the function executes."""
        started_received: list[bool] = []
        task = FunctionTask("test", lambda: None)
        task.signals.started.connect(lambda: started_received.append(True))

        task.run()

        assert started_received == [True]

    def test_run_emits_finished_with_result(self, qtbot):
        """run() emits finished with a TaskResult containing the return value."""
        results: list[TaskResult] = []
        task = FunctionTask("adder", lambda: {"sum": 42})
        task.signals.finished.connect(results.append)

        task.run()

        assert len(results) == 1
        assert results[0].name == "adder"
        assert results[0].ok is True
        assert results[0].data == {"sum": 42}

    def test_run_captures_stdout(self, qtbot):
        """print() calls inside the task function are captured via the log signal."""
        log_lines: list[str] = []
        task = FunctionTask("printer", lambda: print("hello from task"))
        task.signals.log.connect(log_lines.append)

        task.run()

        assert "hello from task" in log_lines

    def test_run_captures_stderr(self, qtbot):
        """Stderr writes inside the task function are captured with a [stderr] prefix."""
        import sys

        log_lines: list[str] = []

        def write_stderr():
            sys.stderr.write("err msg\n")

        task = FunctionTask("stderr_test", write_stderr)
        task.signals.log.connect(log_lines.append)

        task.run()

        assert any("[stderr]" in line and "err msg" in line for line in log_lines)

    def test_run_on_exception_emits_error(self, qtbot):
        """When the task function raises, the error signal is emitted."""
        errors: list[str] = []

        def failing():
            raise ValueError("boom")

        task = FunctionTask("fail_task", failing)
        task.signals.error.connect(errors.append)

        task.run()

        assert len(errors) == 1
        assert "boom" in errors[0]

    def test_run_on_exception_finished_ok_false(self, qtbot):
        """When the task function raises, finished is emitted with ok=False."""
        results: list[TaskResult] = []

        def failing():
            raise RuntimeError("crash")

        task = FunctionTask("fail_task", failing)
        task.signals.finished.connect(results.append)

        task.run()

        assert len(results) == 1
        assert results[0].ok is False
        assert results[0].data is None

    def test_cancel_sets_event(self, qtbot):
        """cancel() sets the internal threading Event."""
        task = FunctionTask("cancellable", lambda: None)

        task.cancel()

        assert task.cancel_event.is_set()

    def test_cancel_emits_cancelled_signal(self, qtbot):
        """If cancel_event is set before run completes, the cancelled signal is emitted."""
        cancelled_received: list[bool] = []
        task = FunctionTask("cancellable", lambda: None)
        task.signals.cancelled.connect(lambda: cancelled_received.append(True))
        task.cancel()

        task.run()

        assert cancelled_received == [True]

    def test_is_cancelled_default_false(self, qtbot):
        """A freshly created task is not cancelled."""
        task = FunctionTask("fresh", lambda: None)

        assert task.is_cancelled is False


# ---------------------------------------------------------------------------
# TestMakeTask
# ---------------------------------------------------------------------------


@pytest.mark.component
class TestMakeTask:
    """Tests for the make_task factory function."""

    def test_make_task_returns_function_task(self):
        """make_task returns a FunctionTask instance."""
        task = make_task("my_task", lambda: None)

        assert isinstance(task, FunctionTask)

    def test_make_task_sets_name(self):
        """make_task correctly sets the task name."""
        task = make_task("named_task", lambda: None)

        assert task.name == "named_task"


# ---------------------------------------------------------------------------
# TestRunInThread
# ---------------------------------------------------------------------------


@pytest.mark.component
class TestRunInThread:
    """Tests for the run_in_thread thread-pool submission helper."""

    def test_run_in_thread_returns_signals(self, qtbot):
        """run_in_thread submits the task and returns its TaskSignals."""
        task = FunctionTask("threaded", lambda: {"result": 1})

        with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
            signals = run_in_thread(task)

        assert isinstance(signals, TaskSignals)
        result = blocker.args[0]
        assert result.ok is True
