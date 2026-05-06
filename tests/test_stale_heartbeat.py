from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from substrate._errors import SubstrateError
from substrate._testing import drop_project_schema, raw_transaction

TESTS_DIR = Path(__file__).parent
DSN = "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test"
KEY_PATH = str(TESTS_DIR / "test_keys.json")
WORKFLOW_PATH = str(TESTS_DIR / "test_workflow.yaml")


@pytest.fixture
def substrate():
    from substrate import Substrate

    project = f"test_ac07_{uuid.uuid4().hex[:8]}"
    sub = Substrate.create_project(DSN, project, KEY_PATH)
    sub.register_workflow_file(WORKFLOW_PATH)
    yield sub
    sub.close()
    drop_project_schema(DSN, project)


class TestAC07StaleHeartbeat:
    def test_heartbeat_rejects_different_actor(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Stale heartbeat"},
        )
        substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=300)

        with pytest.raises(SubstrateError) as exc_info:
            substrate.heartbeat_claim(wi.work_item_id, "agent-2", ttl_seconds=300)
        assert exc_info.value.code == "CLAIM_LOST"

    def test_heartbeat_rejects_after_auto_steal(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Auto-steal"},
        )

        substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=300)

        with raw_transaction(substrate) as conn:
            conn.execute(
                "UPDATE claims SET expires_at = now() - interval '1 second' "
                "WHERE work_item_id = %s",
                [wi.work_item_id],
            )

        claim2 = substrate.acquire_claim(wi.work_item_id, "agent-2", ttl_seconds=300)
        assert claim2.attempt_number == 2

        with pytest.raises(SubstrateError) as exc_info:
            substrate.heartbeat_claim(wi.work_item_id, "agent-1", ttl_seconds=300)
        assert exc_info.value.code == "CLAIM_LOST"

    def test_valid_heartbeat_succeeds(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Valid heartbeat"},
        )
        claim1 = substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=60)
        claim2 = substrate.heartbeat_claim(wi.work_item_id, "agent-1", ttl_seconds=300)
        assert claim2.actor_id == "agent-1"
        assert claim2.expires_at > claim1.expires_at
