from __future__ import annotations

import time
import uuid
from pathlib import Path

import pytest

from substrate._testing import drop_project_schema

TESTS_DIR = Path(__file__).parent
DSN = "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test"
KEY_PATH = str(TESTS_DIR / "test_keys.json")
WORKFLOW_PATH = str(TESTS_DIR / "test_workflow.yaml")

WORKFLOW_WITH_HOOKS = """\
name: hook_test
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
    hooks: [on_finish]

roles:
  - name: agent

work_item_types:
  - name: task
    custom_fields:
      - name: title
        type: string
        required: true

link_types: []

attempt_threshold: 99
"""


@pytest.fixture(scope="module")
def substrate():
    from substrate import Substrate

    project = f"test_hookcons_{uuid.uuid4().hex[:8]}"
    sub = Substrate.create_project(DSN, project, KEY_PATH)
    sub.register_workflow(WORKFLOW_WITH_HOOKS)
    yield sub
    sub.close()
    drop_project_schema(DSN, project)


class TestHookConsumerLifecycle:
    def test_start_and_stop_hook_consumer(self, substrate):
        substrate.start_hook_consumer()
        assert substrate._hook_consumer.is_running
        substrate.stop_hook_consumer()
        assert not substrate._hook_consumer.is_running

    def test_start_idempotent(self, substrate):
        substrate.start_hook_consumer()
        substrate.start_hook_consumer()
        assert substrate._hook_consumer.is_running
        substrate.stop_hook_consumer()

    def test_stop_idempotent(self, substrate):
        substrate.stop_hook_consumer()
        substrate.stop_hook_consumer()
        assert not substrate._hook_consumer.is_running


class TestHookConsumerDelivery:
    def test_consumer_polls_hooks_after_start(self, substrate):
        received: list = []

        def handler(ctx):
            received.append(ctx)

        substrate.register_hook_handler("on_finish", handler)
        substrate.start_hook_consumer()
        time.sleep(0.3)

        wi, _ = substrate.create_work_item(
            workflow_name="hook_test",
            work_item_type="task",
            actor_id="agent-1",
            custom_fields={"title": "consumer test"},
        )
        substrate.transition(
            work_item_id=wi.work_item_id,
            transition_name="finish",
            actor_id="agent-1",
        )

        deadline = time.time() + 15
        while not received and time.time() < deadline:
            substrate.poll_hooks()
            time.sleep(0.5)

        substrate.stop_hook_consumer()

        assert len(received) >= 1
        ctx = received[0]
        assert ctx.hook_name == "on_finish"
        assert ctx.work_item_id == wi.work_item_id
        assert ctx.transition == "finish"
