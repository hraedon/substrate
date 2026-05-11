from __future__ import annotations

import socket
import subprocess
import time
import uuid
from pathlib import Path

import psycopg
import pytest

from substrate._errors import ErrorCode, SubstrateError
from substrate._hooks import check_validator_io_safety, run_validator
from substrate._types import ValidatorContext
from substrate.testing import drop_project_schema

TESTS_DIR = Path(__file__).parent
DSN = "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test"
KEY_PATH = str(TESTS_DIR / "test_keys.json")

WORKFLOW_WITH_VALIDATOR = """\
name: validator_test
version: 1
substrate_version: "0.1.0"

states:
  - name: new
    initial: true
  - name: done
    terminal: true

transitions:
  - name: finish
    from: new
    to: done
    validator: check_finish

roles: []

work_item_types:
  - name: task
    custom_fields: []

link_types: []

attempt_threshold: 99
"""


def _make_ctx():
    return ValidatorContext(
        work_item_id=uuid.uuid4(),
        workflow_name="test",
        workflow_version=1,
        work_item_type="task",
        current_state="new",
        new_state="done",
        transition_name="finish",
        payload=None,
        custom_fields={},
        actor_id="agent-1",
        actor_metadata=None,
    )


class TestValidatorIODetection:
    def test_rejects_handler_referencing_io_module(self):
        def uses_socket(ctx):
            socket.gethostname()

        with pytest.raises(SubstrateError) as exc_info:
            check_validator_io_safety(uses_socket, "uses_socket")
        assert exc_info.value.code == ErrorCode.VALIDATOR_IO_UNSAFE
        assert "socket" in exc_info.value.message

    def test_allows_pure_handler(self):
        import json

        def pure_handler(ctx):
            json.dumps({"ok": True})

        check_validator_io_safety(pure_handler, "pure_handler")

    def test_allows_lambda(self):
        check_validator_io_safety(lambda ctx: None, "lam")

    def test_allows_builtin_handler(self):
        check_validator_io_safety(print, "print")

    def test_rejects_psycopg_reference(self):
        def uses_db(ctx):
            psycopg.connect("")

        with pytest.raises(SubstrateError) as exc_info:
            check_validator_io_safety(uses_db, "uses_db")
        assert exc_info.value.code == ErrorCode.VALIDATOR_IO_UNSAFE
        assert "psycopg" in exc_info.value.message

    def test_rejects_subprocess_reference(self):
        def uses_subprocess(ctx):
            subprocess.run(["echo", "hi"])

        with pytest.raises(SubstrateError) as exc_info:
            check_validator_io_safety(uses_subprocess, "uses_subprocess")
        assert exc_info.value.code == ErrorCode.VALIDATOR_IO_UNSAFE
        assert "subprocess" in exc_info.value.message


class TestValidatorWatchdog:
    def test_emits_near_timeout_on_slow_validator(self):
        slow_duration = 0.45
        timeout = 0.5

        def slow_handler(ctx):
            time.sleep(slow_duration)

        from prometheus_client import CollectorRegistry

        from substrate._observability import Metrics

        registry = CollectorRegistry()
        metrics = Metrics(registry=registry)
        ctx = _make_ctx()

        run_validator("slow", slow_handler, ctx, timeout=timeout, metrics=metrics, project="test")

        counter = metrics._counter(
            "substrate_validators_near_timeout_total",
            "Validators near timeout (>= 80% of threshold)",
        )
        value = counter.labels(project="test")._value.get()
        assert value == 1.0

    def test_no_emission_on_fast_validator(self):
        timeout = 5.0

        def fast_handler(ctx):
            pass

        from prometheus_client import CollectorRegistry

        from substrate._observability import Metrics

        registry = CollectorRegistry()
        metrics = Metrics(registry=registry)
        ctx = _make_ctx()

        run_validator("fast", fast_handler, ctx, timeout=timeout, metrics=metrics, project="test")

        counter = metrics._counter(
            "substrate_validators_near_timeout_total",
            "Validators near timeout (>= 80% of threshold)",
        )
        value = counter.labels(project="test")._value.get()
        assert value == 0.0


@pytest.fixture(scope="module")
def substrate():
    from substrate import Substrate

    project = f"test_bc112_{uuid.uuid4().hex[:8]}"
    sub = Substrate.create_project(DSN, project, KEY_PATH)
    sub.register_workflow(WORKFLOW_WITH_VALIDATOR)
    yield sub
    sub.close()
    drop_project_schema(DSN, project)


class TestStatementTimeout:
    def test_validator_success_with_statement_timeout(self, substrate):
        def clean_validator(ctx):
            pass

        substrate.register_validator("check_finish", clean_validator)

        wi, _ = substrate.create_work_item(
            workflow_name="validator_test",
            work_item_type="task",
            actor_id="agent-1",
        )

        evt = substrate.transition(
            work_item_id=wi.work_item_id,
            transition_name="finish",
            actor_id="agent-1",
        )
        assert evt.transition == "finish"

    def test_validator_timeout_with_statement_timeout(self, substrate):
        def slow_validator(ctx):
            time.sleep(10)

        substrate.register_validator("check_finish", slow_validator)

        wi, _ = substrate.create_work_item(
            workflow_name="validator_test",
            work_item_type="task",
            actor_id="agent-1",
        )

        with pytest.raises(Exception, match="VALIDATOR_TIMEOUT"):
            substrate.transition(
                work_item_id=wi.work_item_id,
                transition_name="finish",
                actor_id="agent-1",
            )

        refreshed = substrate.get_work_item(wi.work_item_id)
        assert refreshed is not None
        assert refreshed.current_state == "new"

    def test_validator_failure_rolls_back_with_statement_timeout(self, substrate):
        def fail_validator(ctx):
            raise ValueError("boom")

        substrate.register_validator("check_finish", fail_validator)

        wi, _ = substrate.create_work_item(
            workflow_name="validator_test",
            work_item_type="task",
            actor_id="agent-1",
        )

        with pytest.raises(Exception, match="VALIDATOR_FAILED"):
            substrate.transition(
                work_item_id=wi.work_item_id,
                transition_name="finish",
                actor_id="agent-1",
            )

        refreshed = substrate.get_work_item(wi.work_item_id)
        assert refreshed is not None
        assert refreshed.current_state == "new"


class TestRegistrationIOSafetyIntegration:
    def test_register_rejects_io_handler_via_substrate_api(self, substrate):
        def uses_socket(ctx):
            socket.gethostname()

        with pytest.raises(SubstrateError) as exc_info:
            substrate.register_validator("bad", uses_socket)
        assert exc_info.value.code == ErrorCode.VALIDATOR_IO_UNSAFE

    def test_register_allows_clean_handler_via_substrate_api(self, substrate):
        substrate.register_validator("check_finish", lambda ctx: None)
