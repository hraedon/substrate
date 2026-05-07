from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from substrate._errors import ErrorCode, SubstrateError
from substrate._testing import drop_project_schema
from substrate.testing import InMemorySubstrate

TESTS_DIR = Path(__file__).parent
DSN = "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test"
KEY_PATH = str(TESTS_DIR / "test_keys.json")
WORKFLOW_PATH = str(TESTS_DIR / "test_workflow.yaml")
WORKFLOW_YAML = Path(WORKFLOW_PATH).read_text()


@pytest.fixture(params=["real", "in_memory"])
def sub(request):
    if request.param == "real":
        from substrate import Substrate

        project = f"test_conf_{uuid.uuid4().hex[:8]}"
        s = Substrate.create_project(DSN, project, KEY_PATH)
        s.register_workflow_file(WORKFLOW_PATH)
        yield s
        s.close()
        drop_project_schema(DSN, project)
    else:
        s = InMemorySubstrate(project="test")
        s.register_workflow_file(WORKFLOW_PATH)
        yield s
        s.close()


class TestConformanceWorkflow:
    def test_register_and_idempotent(self, sub):
        v = sub.register_workflow(WORKFLOW_YAML)
        assert v.name == "test_workflow"
        assert v.version == 1
        v2 = sub.register_workflow(WORKFLOW_YAML)
        assert v2.version == v.version

    def test_register_version_conflict(self, sub):
        sub.register_workflow(WORKFLOW_YAML)
        modified = WORKFLOW_YAML.replace("attempt_threshold: 3", "attempt_threshold: 99")
        with pytest.raises(SubstrateError) as exc_info:
            sub.register_workflow(modified)
        assert exc_info.value.code == ErrorCode.WORKFLOW_VERSION_CONFLICT


class TestConformanceWorkItem:
    def test_create_and_get(self, sub):
        wi, evt = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        assert wi.work_item_type == "feature"
        assert wi.current_state == "new"
        assert evt.transition == "created"

        fetched = sub.get_work_item(wi.work_item_id)
        assert fetched is not None
        assert fetched.work_item_id == wi.work_item_id

    def test_create_missing_required_field(self, sub):
        with pytest.raises(SubstrateError) as exc_info:
            sub.create_work_item(
                workflow_name="test_workflow",
                work_item_type="feature",
                actor_id="agent-1",
                custom_fields={},
            )
        assert exc_info.value.code == ErrorCode.CUSTOM_FIELD_VIOLATION

    def test_create_unknown_type(self, sub):
        with pytest.raises(SubstrateError) as exc_info:
            sub.create_work_item(
                workflow_name="test_workflow",
                work_item_type="nonexistent",
                actor_id="agent-1",
            )
        assert exc_info.value.code == ErrorCode.WORK_ITEM_TYPE_NOT_DECLARED


class TestConformanceTransition:
    def test_valid_transition(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        evt = sub.transition(
            wi.work_item_id, "start", "agent-1",
            actor_metadata={"role": "agent"},
        )
        assert evt.transition == "start"
        updated = sub.get_work_item(wi.work_item_id)
        assert updated.current_state == "in_progress"

    def test_invalid_transition(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        with pytest.raises(SubstrateError) as exc_info:
            sub.transition(wi.work_item_id, "approve", "agent-1")
        assert exc_info.value.code == ErrorCode.INVALID_TRANSITION

    def test_role_not_permitted(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        sub.transition(wi.work_item_id, "start", "agent-1", actor_metadata={"role": "agent"})
        sub.transition(
            wi.work_item_id, "submit_review", "agent-1",
            actor_metadata={"role": "agent"},
        )
        with pytest.raises(SubstrateError) as exc_info:
            sub.transition(
                wi.work_item_id, "approve", "agent-1",
                actor_metadata={"role": "agent"},
            )
        assert exc_info.value.code == ErrorCode.ROLE_NOT_PERMITTED

    def test_transition_via_append_blocked(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        with pytest.raises(SubstrateError) as exc_info:
            sub.append_event(wi.work_item_id, "agent-1", transition="start")
        assert exc_info.value.code == ErrorCode.TRANSITION_VIA_APPEND_BLOCKED

    def test_custom_fields_update_on_transition(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        sub.transition(
            wi.work_item_id, "start", "agent-1",
            actor_metadata={"role": "agent"},
            custom_fields={"priority": "high"},
        )
        updated = sub.get_work_item(wi.work_item_id)
        assert updated.custom_fields["priority"] == "high"
        assert updated.custom_fields["title"] == "test"


class TestConformanceEvents:
    def test_read_events_by_work_item(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        evts = sub.read_events(work_item_id=wi.work_item_id)
        assert len(evts) >= 1
        assert evts[0].transition == "created"

    def test_read_events_by_actor(self, sub):
        sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="unique-agent-x",
            custom_fields={"title": "test"},
        )
        evts = sub.read_events(actor_id="unique-agent-x")
        assert len(evts) >= 1

    def test_event_idempotency(self, sub):
        eid = uuid.uuid4()
        wi1, evt1 = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
            event_id=eid,
        )
        assert evt1.event_id == eid


class TestConformanceClaims:
    def test_acquire_and_release(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        claim = sub.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=300)
        assert claim.actor_id == "agent-1"
        assert claim.attempt_number == 1

        updated = sub.get_work_item(wi.work_item_id)
        assert updated.claimed_by == "agent-1"

        sub.release_claim(wi.work_item_id, "agent-1")
        updated = sub.get_work_item(wi.work_item_id)
        assert updated.claimed_by is None

    def test_claim_contested(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        sub.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=300)
        with pytest.raises(SubstrateError) as exc_info:
            sub.acquire_claim(wi.work_item_id, "agent-2", ttl_seconds=300)
        assert exc_info.value.code == ErrorCode.CLAIM_CONTESTED

    def test_heartbeat(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        claim1 = sub.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=60)
        claim2 = sub.heartbeat_claim(wi.work_item_id, "agent-1", ttl_seconds=120)
        assert claim2.expires_at > claim1.expires_at

    def test_claim_releases_on_transition(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        sub.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=300)
        sub.transition(
            wi.work_item_id, "start", "agent-1",
            actor_metadata={"role": "agent"},
        )
        updated = sub.get_work_item(wi.work_item_id)
        assert updated.claimed_by is None


class TestConformanceLinks:
    def test_create_and_query(self, sub):
        wi1, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "a"},
        )
        wi2, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "b"},
        )
        link = sub.create_link(
            wi1.work_item_id, wi2.work_item_id, "blocks",
            actor_id="agent-1",
        )
        assert link.link_type == "blocks"

        page = sub.query_work_items(has_link_type="blocks")
        ids = [wi.work_item_id for wi in page.items]
        assert wi1.work_item_id in ids


class TestConformanceActorRoles:
    def test_register_and_enforce(self, sub):
        sub.register_actor_role("agent-1", "agent")
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        sub.transition(
            wi.work_item_id, "start", "agent-1",
            actor_metadata={"role": "agent"},
        )
        updated = sub.get_work_item(wi.work_item_id)
        assert updated.current_state == "in_progress"

    def test_role_rejects_unauthorized(self, sub):
        sub.register_actor_role("agent-1", "reviewer")
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        with pytest.raises(SubstrateError) as exc_info:
            sub.transition(
                wi.work_item_id, "start", "agent-1",
                actor_metadata={"role": "agent"},
            )
        assert exc_info.value.code == ErrorCode.ACTOR_ROLE_NOT_AUTHORIZED


class TestConformanceQuery:
    def test_query_by_state(self, sub):
        sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "a"},
        )
        page = sub.query_work_items(current_states=["new"])
        assert len(page.items) >= 1

    def test_query_by_workflow(self, sub):
        sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "a"},
        )
        page = sub.query_work_items(workflow_name="test_workflow")
        assert len(page.items) >= 1

    def test_query_with_cursor(self, sub):
        for i in range(5):
            sub.create_work_item(
                workflow_name="test_workflow",
                work_item_type="feature",
                actor_id="agent-1",
                custom_fields={"title": f"item-{i}"},
            )
        page1 = sub.query_work_items(page_size=2)
        assert len(page1.items) == 2
        assert page1.has_more
        page2 = sub.query_work_items(cursor=page1.cursor, page_size=2)
        assert len(page2.items) == 2


class TestConformanceReplay:
    def test_replay_no_drift(self, sub):
        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        sub.transition(
            wi.work_item_id, "start", "agent-1",
            actor_metadata={"role": "agent"},
        )
        report = sub.replay()
        assert report.replayed_drift == 0
        assert report.replayed_ok >= 1


class TestConformanceUpdateNotBefore:
    def test_set_and_clear(self, sub):
        from datetime import UTC, datetime, timedelta

        wi, _ = sub.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "test"},
        )
        future = datetime.now(UTC) + timedelta(hours=1)
        sub.update_not_before(wi.work_item_id, future, "agent-1")
        updated = sub.get_work_item(wi.work_item_id)
        assert updated.not_before is not None

        sub.update_not_before(wi.work_item_id, None, "agent-1")
        updated = sub.get_work_item(wi.work_item_id)
        assert updated.not_before is None
