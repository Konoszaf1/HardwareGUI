"""Step definitions for VU connection feature."""

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from src.logic.qt_workers import run_in_thread
from src.logic.services.vu_service import VoltageUnitService

pytestmark = pytest.mark.bdd


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@scenario("../features/vu_connection.feature", "Successful ping verifies instrument")
def test_successful_ping():
    pass


@scenario("../features/vu_connection.feature", "Failed ping marks instrument as unverified")
def test_failed_ping():
    pass


@scenario("../features/vu_connection.feature", "Connect without scope IP returns None")
def test_no_scope_ip():
    pass


@scenario("../features/vu_connection.feature", "Successful connection emits connectedChanged")
def test_successful_connection():
    pass


@scenario("../features/vu_connection.feature", "Disconnect after connection")
def test_disconnect():
    pass


# ---------------------------------------------------------------------------
# State fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vu_context():
    """Shared state for VU connection scenarios."""
    return {"service": None, "task": None, "result": None}


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given(parsers.parse('a VU service with scope IP "{ip}"'), target_fixture="vu_context")
def vu_service_with_ip(mock_vu_hardware, ip):
    """Create VU service and set scope IP."""
    service = VoltageUnitService()
    service.set_instrument_ip(ip)
    return {"service": service, "task": None, "result": None}


@given("a VU service with no scope IP", target_fixture="vu_context")
def vu_service_no_ip():
    """Create VU service without setting scope IP."""
    service = VoltageUnitService()
    return {"service": service, "task": None, "result": None}


@given("a connected VU service", target_fixture="vu_context")
def connected_vu_service(mock_vu_hardware, qtbot):
    """Create VU service that is already connected."""
    service = VoltageUnitService()
    service.set_instrument_ip("192.168.68.154")

    task = service.connect_only()
    with qtbot.waitSignal(task.signals.finished, timeout=5000):
        run_in_thread(task)

    return {"service": service, "task": None, "result": None}


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when("the ping task completes successfully")
def ping_succeeds(vu_context, qtbot):
    """Run the ping task and wait for completion."""
    service = vu_context["service"]
    task = service.ping_instrument()

    with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
        run_in_thread(task)

    vu_context["result"] = blocker.args[0]


@when("the ping task fails")
def ping_fails(vu_context, mocker, qtbot):
    """Run ping with simulated failure."""
    import subprocess

    mocker.patch(
        "subprocess.check_call", side_effect=subprocess.CalledProcessError(1, "ping")
    )
    service = vu_context["service"]
    task = service.ping_instrument()

    with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
        run_in_thread(task)

    vu_context["result"] = blocker.args[0]


@when("I request connect_and_read")
def request_connect_and_read(vu_context):
    """Call connect_and_read on the service."""
    service = vu_context["service"]
    with pytest.warns(UserWarning, match="requires instrument IP"):
        vu_context["task"] = service.connect_and_read()


@when("the connect task completes successfully")
def connect_succeeds(vu_context, qtbot):
    """Run connect_only and wait for completion."""
    service = vu_context["service"]
    task = service.connect_only()

    with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
        run_in_thread(task)

    vu_context["result"] = blocker.args[0]


@when("I disconnect")
def disconnect(vu_context, qtbot):
    """Run disconnect_hardware and wait for completion."""
    service = vu_context["service"]
    task = service.disconnect_hardware()

    with qtbot.waitSignal(task.signals.finished, timeout=5000) as blocker:
        run_in_thread(task)

    vu_context["result"] = blocker.args[0]


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("the instrument should be verified")
def instrument_verified(vu_context):
    """Check instrument is verified."""
    assert vu_context["service"].is_instrument_verified is True


@then("the instrument should not be verified")
def instrument_not_verified(vu_context):
    """Check instrument is not verified."""
    assert vu_context["service"].is_instrument_verified is False


@then("no task should be returned")
def no_task_returned(vu_context):
    """Check that no task was created."""
    assert vu_context["task"] is None


@then("the service should report connected")
def service_connected(vu_context):
    """Check service reports connected."""
    assert vu_context["service"].connected is True


@then("the service should report disconnected")
def service_disconnected(vu_context):
    """Check service reports disconnected."""
    assert vu_context["service"].connected is False
