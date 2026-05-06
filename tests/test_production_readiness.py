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


@pytest.fixture(scope="module")
def substrate():
    from substrate import Substrate

    project = f"test_prodready_{uuid.uuid4().hex[:8]}"
    sub = Substrate.create_project(DSN, project, KEY_PATH)
    sub.register_workflow_file(WORKFLOW_PATH)
    yield sub
    sub.close()
    drop_project_schema(DSN, project)


class TestActorKindValidation:
    def test_invalid_actor_kind_on_create(self, substrate):
        with pytest.raises(SubstrateError) as exc_info:
            substrate.create_work_item(
                workflow_name="test_workflow",
                work_item_type="feature",
                actor_id="agent-1",
                actor_kind="robot",
                custom_fields={"title": "bad kind"},
            )
        assert "actor_kind" in exc_info.value.message

    def test_invalid_actor_kind_on_append(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "AC kind"},
        )
        with pytest.raises(SubstrateError) as exc_info:
            substrate.append_event(
                work_item_id=wi.work_item_id,
                actor_id="agent-1",
                actor_kind="alien",
                transition="note",
            )
        assert "actor_kind" in exc_info.value.message

    def test_invalid_actor_kind_on_transition(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "AC trans kind"},
        )
        with pytest.raises(SubstrateError) as exc_info:
            substrate.transition(
                work_item_id=wi.work_item_id,
                transition_name="start",
                actor_id="agent-1",
                actor_kind="robot",
                actor_metadata={"role": "agent"},
            )
        assert "actor_kind" in exc_info.value.message

    def test_invalid_actor_kind_on_create_link(self, substrate):
        wi1, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "A"},
        )
        wi2, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="bug",
            actor_id="agent-1",
            custom_fields={"severity": "major"},
        )
        with pytest.raises(SubstrateError) as exc_info:
            substrate.create_link(
                from_work_item_id=wi1.work_item_id,
                to_work_item_id=wi2.work_item_id,
                link_type="fixes",
                actor_id="agent-1",
                actor_kind="robot",
            )
        assert "actor_kind" in exc_info.value.message

    def test_invalid_actor_kind_on_remove_link(self, substrate):
        wi1, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "A"},
        )
        wi2, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="bug",
            actor_id="agent-1",
            custom_fields={"severity": "major"},
        )
        substrate.create_link(
            from_work_item_id=wi1.work_item_id,
            to_work_item_id=wi2.work_item_id,
            link_type="fixes",
            actor_id="agent-1",
        )
        with pytest.raises(SubstrateError) as exc_info:
            substrate.remove_link(
                from_work_item_id=wi1.work_item_id,
                to_work_item_id=wi2.work_item_id,
                link_type="fixes",
                actor_id="agent-1",
                actor_kind="robot",
            )
        assert "actor_kind" in exc_info.value.message

    def test_invalid_actor_kind_on_update_not_before(self, substrate):
        from datetime import UTC, datetime, timedelta

        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "AC nb kind"},
        )
        with pytest.raises(SubstrateError) as exc_info:
            substrate.update_not_before(
                work_item_id=wi.work_item_id,
                not_before=datetime.now(UTC) + timedelta(hours=1),
                actor_id="agent-1",
                actor_kind="robot",
            )
        assert "actor_kind" in exc_info.value.message

    def test_valid_actor_kinds_accepted(self, substrate):
        for kind in ("agent", "human", "system"):
            wi, _ = substrate.create_work_item(
                workflow_name="test_workflow",
                work_item_type="feature",
                actor_id=f"actor-{kind}",
                actor_kind=kind,
                custom_fields={"title": f"kind {kind}"},
            )
            assert wi is not None

            events = substrate.read_events(work_item_id=wi.work_item_id)
            created_events = [e for e in events if e.transition == "created"]
            assert len(created_events) >= 1
            assert created_events[0].actor_kind == kind


class TestTransitionEventIdCollision:
    def test_same_event_id_different_transition_rejected(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            actor_metadata={"role": "agent"},
            custom_fields={"title": "trans collision"},
        )

        eid = uuid.uuid4()
        substrate.transition(
            work_item_id=wi.work_item_id,
            transition_name="start",
            actor_id="agent-1",
            actor_metadata={"role": "agent"},
            event_id=eid,
        )

        with pytest.raises(SubstrateError) as exc_info:
            substrate.append_event(
                work_item_id=wi.work_item_id,
                actor_id="agent-1",
                transition="custom_event_b",
                event_id=eid,
            )
        assert exc_info.value.code == ErrorCode.IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD


class TestClaimStolenMetric:
    def test_stolen_claim_emits_event_and_metric(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "stolen metric"},
        )
        substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=300)

        with raw_transaction(substrate) as conn:
            conn.execute(
                "UPDATE claims SET expires_at = now() - interval '1 second' "
                "WHERE work_item_id = %s",
                [wi.work_item_id],
            )

        substrate.acquire_claim(wi.work_item_id, "agent-2", ttl_seconds=300)

        events = substrate.read_events(work_item_id=wi.work_item_id)
        stolen_events = [e for e in events if e.transition == "claim_stolen"]
        assert len(stolen_events) >= 1
        assert stolen_events[-1].payload["prior_actor_id"] == "agent-1"
        assert stolen_events[-1].payload["new_actor_id"] == "agent-2"

    def test_same_actor_reacquire_does_not_count_as_stolen(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "reacquire not stolen"},
        )
        substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=300)
        substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=600)

        events = substrate.read_events(work_item_id=wi.work_item_id)
        stolen_events = [e for e in events if e.transition == "claim_stolen"]
        assert len(stolen_events) == 0
