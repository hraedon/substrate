from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from substrate._errors import ErrorCode, SubstrateError
from substrate._testing import drop_project_schema, raw_transaction

TESTS_DIR = Path(__file__).parent
DSN = "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test"
KEY_PATH = str(TESTS_DIR / "test_keys.json")
WORKFLOW_PATH = str(TESTS_DIR / "test_workflow.yaml")

WF_V1 = (
    "name: versioned_wf\n"
    "version: 1\n"
    "substrate_version: '0.1.0'\n"
    "\n"
    "states:\n"
    "  - name: new\n"
    "    initial: true\n"
    "  - name: done\n"
    "    terminal: true\n"
    "\n"
    "transitions:\n"
    "  - name: finish\n"
    "    from: new\n"
    "    to: done\n"
    "    allowed_roles: [agent]\n"
    "\n"
    "roles:\n"
    "  - name: agent\n"
    "\n"
    "work_item_types:\n"
    "  - name: task\n"
    "    custom_fields: []\n"
)

WF_V2 = (
    "name: versioned_wf\n"
    "version: 2\n"
    "substrate_version: '0.1.0'\n"
    "\n"
    "states:\n"
    "  - name: new\n"
    "    initial: true\n"
    "  - name: in_progress\n"
    "  - name: done\n"
    "    terminal: true\n"
    "\n"
    "transitions:\n"
    "  - name: start\n"
    "    from: new\n"
    "    to: in_progress\n"
    "    allowed_roles: [agent]\n"
    "  - name: finish\n"
    "    from: in_progress\n"
    "    to: done\n"
    "    allowed_roles: [agent]\n"
    "  - name: shortcut\n"
    "    from: new\n"
    "    to: done\n"
    "    allowed_roles: [agent]\n"
    "\n"
    "roles:\n"
    "  - name: agent\n"
    "\n"
    "work_item_types:\n"
    "  - name: task\n"
    "    custom_fields: []\n"
)


@pytest.fixture
def substrate():
    from substrate import Substrate

    project = f"test_ac12_{uuid.uuid4().hex[:8]}"
    sub = Substrate.create_project(DSN, project, KEY_PATH)
    sub.register_workflow(WF_V1)
    yield sub
    sub.close()
    drop_project_schema(DSN, project)


class TestAC12PinnedVersionIsolation:
    def test_v1_work_item_rejects_v2_only_transition(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="versioned_wf",
            work_item_type="task",
            actor_id="agent-1",
        )

        with raw_transaction(substrate) as conn:
            row = conn.execute(
                "SELECT workflow_version FROM work_items_current WHERE work_item_id = %s",
                [wi.work_item_id],
            ).fetchone()
        assert row["workflow_version"] == 1

        substrate.register_workflow(WF_V2)

        with pytest.raises(SubstrateError) as exc_info:
            substrate.transition(
                work_item_id=wi.work_item_id,
                transition_name="shortcut",
                actor_id="agent-1",
                actor_metadata={"role": "agent"},
            )
        assert exc_info.value.code == ErrorCode.INVALID_TRANSITION
        assert "v1" in exc_info.value.message

    def test_v2_work_item_accepts_shortcut(self, substrate):
        substrate.register_workflow(WF_V2)

        wi, _ = substrate.create_work_item(
            workflow_name="versioned_wf",
            work_item_type="task",
            actor_id="agent-1",
        )

        with raw_transaction(substrate) as conn:
            row = conn.execute(
                "SELECT workflow_version FROM work_items_current WHERE work_item_id = %s",
                [wi.work_item_id],
            ).fetchone()
        assert row["workflow_version"] == 2

        evt = substrate.transition(
            work_item_id=wi.work_item_id,
            transition_name="shortcut",
            actor_id="agent-1",
            actor_metadata={"role": "agent"},
        )
        assert evt.transition == "shortcut"

        refreshed = substrate.get_work_item(wi.work_item_id)
        assert refreshed.current_state == "done"

    def test_v1_work_item_uses_v1_transitions(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="versioned_wf",
            work_item_type="task",
            actor_id="agent-1",
        )

        substrate.register_workflow(WF_V2)

        evt = substrate.transition(
            work_item_id=wi.work_item_id,
            transition_name="finish",
            actor_id="agent-1",
            actor_metadata={"role": "agent"},
        )
        assert evt.transition == "finish"

        refreshed = substrate.get_work_item(wi.work_item_id)
        assert refreshed.current_state == "done"
