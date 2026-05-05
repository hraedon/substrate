from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from substrate._testing import drop_project_schema

TESTS_DIR = Path(__file__).parent
DSN = "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test"
KEY_PATH = str(TESTS_DIR / "test_keys.json")
WORKFLOW_PATH = str(TESTS_DIR / "test_workflow.yaml")


@pytest.fixture(scope="module")
def substrate():
    from substrate import Substrate

    project = f"test_smoke_{uuid.uuid4().hex[:8]}"
    sub = Substrate.create_project(DSN, project, KEY_PATH)
    yield sub
    sub.close()
    drop_project_schema(DSN, project)


class TestWorkflow:
    def test_register_workflow(self, substrate):
        result = substrate.register_workflow_file(WORKFLOW_PATH)
        assert result.name == "test_workflow"
        assert result.version == 1

    def test_register_idempotent(self, substrate):
        yaml_content = Path(WORKFLOW_PATH).read_text()
        r1 = substrate.register_workflow(yaml_content)
        r2 = substrate.register_workflow(yaml_content)
        assert r1.name == r2.name
        assert r1.version == r2.version

    def test_register_version_conflict(self, substrate):
        yaml_content = Path(WORKFLOW_PATH).read_text()
        substrate.register_workflow(yaml_content)
        modified = yaml_content.replace("attempt_threshold: 3", "attempt_threshold: 5")
        with pytest.raises(Exception, match="WORKFLOW_VERSION_CONFLICT"):
            substrate.register_workflow(modified)

    def test_register_invalid_yaml(self, substrate):
        with pytest.raises(Exception, match="Schema validation"):
            substrate.register_workflow(":::invalid yaml:::")


class TestWorkItem:
    def test_create_work_item(self, substrate):
        wi, evt = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            actor_metadata={"role": "agent", "model": "gpt-4"},
            custom_fields={"title": "Test feature", "priority": "high"},
        )
        assert wi.current_state == "new"
        assert wi.work_item_type == "feature"
        assert wi.custom_fields["title"] == "Test feature"
        assert evt.transition == "created"
        assert evt.event_seq == 1

    def test_create_with_invalid_type(self, substrate):
        with pytest.raises(Exception, match="not declared"):
            substrate.create_work_item(
                workflow_name="test_workflow",
                work_item_type="nonexistent",
                actor_id="agent-1",
            )

    def test_create_with_invalid_field(self, substrate):
        with pytest.raises(Exception, match="Required"):
            substrate.create_work_item(
                workflow_name="test_workflow",
                work_item_type="bug",
                actor_id="agent-1",
            )


class TestTransition:
    def _create_feature(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            actor_metadata={"role": "agent"},
            custom_fields={"title": "Test"},
        )
        return wi

    def test_valid_transition(self, substrate):
        wi = self._create_feature(substrate)
        evt = substrate.transition(
            work_item_id=wi.work_item_id,
            transition_name="start",
            actor_id="agent-1",
            actor_metadata={"role": "agent"},
        )
        assert evt.transition == "start"
        assert evt.event_seq == 2

        refreshed = substrate.get_work_item(wi.work_item_id)
        assert refreshed is not None
        assert refreshed.current_state == "in_progress"

    def test_invalid_transition(self, substrate):
        wi = self._create_feature(substrate)
        with pytest.raises(Exception, match="not valid"):
            substrate.transition(
                work_item_id=wi.work_item_id,
                transition_name="approve",
                actor_id="agent-1",
                actor_metadata={"role": "agent"},
            )

    def test_role_not_permitted(self, substrate):
        wi = self._create_feature(substrate)
        substrate.transition(
            work_item_id=wi.work_item_id,
            transition_name="start",
            actor_id="agent-1",
            actor_metadata={"role": "agent"},
        )
        with pytest.raises(Exception, match="not permitted"):
            substrate.transition(
                work_item_id=wi.work_item_id,
                transition_name="submit_review",
                actor_id="agent-1",
                actor_metadata={"role": "reviewer"},
            )

    def test_full_lifecycle(self, substrate):
        wi = self._create_feature(substrate)
        substrate.transition(wi.work_item_id, "start", "agent-1",
                             actor_metadata={"role": "agent"})
        substrate.transition(wi.work_item_id, "submit_review", "agent-1",
                             actor_metadata={"role": "agent"})
        substrate.transition(wi.work_item_id, "approve", "reviewer-1",
                             actor_metadata={"role": "reviewer"})

        refreshed = substrate.get_work_item(wi.work_item_id)
        assert refreshed.current_state == "done"


class TestEvents:
    def test_read_by_work_item(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Events test"},
        )
        substrate.transition(wi.work_item_id, "start", "agent-1", actor_metadata={"role": "agent"})

        events = substrate.read_events(work_item_id=wi.work_item_id)
        assert len(events) == 2
        assert events[0].transition == "created"
        assert events[1].transition == "start"


class TestClaims:
    def test_acquire_and_release(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Claim test"},
        )

        claim = substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=300)
        assert claim.actor_id == "agent-1"
        assert claim.attempt_number == 1

        refreshed = substrate.get_work_item(wi.work_item_id)
        assert refreshed.claimed_by == "agent-1"

        substrate.release_claim(wi.work_item_id, "agent-1")
        refreshed = substrate.get_work_item(wi.work_item_id)
        assert refreshed.claimed_by is None

    def test_claim_contested(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Contested"},
        )

        substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=300)

        with pytest.raises(Exception, match="CLAIM_CONTESTED"):
            substrate.acquire_claim(wi.work_item_id, "agent-2", ttl_seconds=300)

    def test_heartbeat(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Heartbeat"},
        )

        substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=60)
        claim = substrate.heartbeat_claim(wi.work_item_id, "agent-1", ttl_seconds=300)
        assert claim.expires_at is not None


class TestQuery:
    def test_query_by_workflow(self, substrate):
        substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Query test"},
        )

        page = substrate.query_work_items(workflow_name="test_workflow", page_size=10)
        assert len(page.items) >= 1
        assert all(wi.workflow_name == "test_workflow" for wi in page.items)

    def test_query_by_state(self, substrate):
        page = substrate.query_work_items(
            workflow_name="test_workflow",
            current_states=["new"],
        )
        assert all(wi.current_state == "new" for wi in page.items)

    def test_query_claimable_now(self, substrate):
        page = substrate.query_work_items(
            workflow_name="test_workflow",
            claimable_now=True,
        )
        for wi in page.items:
            assert wi.claimed_by is None or wi.claim_expires_at is not None

    def test_pagination_stable_no_duplicates(self, substrate):
        for i in range(5):
            substrate.create_work_item(
                workflow_name="test_workflow",
                work_item_type="feature",
                actor_id="agent-1",
                custom_fields={"title": f"Page test {i}"},
            )

        seen_ids = set()
        cursor = None
        while True:
            page = substrate.query_work_items(
                workflow_name="test_workflow",
                current_states=["new"],
                cursor=cursor,
                page_size=2,
            )
            for wi in page.items:
                assert wi.work_item_id not in seen_ids
                seen_ids.add(wi.work_item_id)
            if not page.has_more:
                break
            cursor = page.cursor
        assert len(seen_ids) >= 5


class TestLinks:
    def test_create_and_remove_link(self, substrate):
        wi1, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Feature 1"},
        )
        wi2, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="bug",
            actor_id="agent-1",
            custom_fields={"severity": "major"},
        )

        link = substrate.create_link(
            from_work_item_id=wi1.work_item_id,
            to_work_item_id=wi2.work_item_id,
            link_type="fixes",
            actor_id="agent-1",
        )
        assert link.link_type == "fixes"

        substrate.remove_link(
            from_work_item_id=wi1.work_item_id,
            to_work_item_id=wi2.work_item_id,
            link_type="fixes",
            actor_id="agent-1",
        )

    def test_create_link_with_payload(self, substrate):
        wi1, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Feature 1"},
        )
        wi2, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="bug",
            actor_id="agent-1",
            custom_fields={"severity": "major"},
        )

        link = substrate.create_link(
            from_work_item_id=wi1.work_item_id,
            to_work_item_id=wi2.work_item_id,
            link_type="fixes",
            actor_id="agent-1",
            payload={"rationale": "Bug caused by missing null check", "priority": "high"},
        )
        assert link.payload == {"rationale": "Bug caused by missing null check", "priority": "high"}


class TestIdempotency:
    def test_event_idempotency(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Idempotency"},
        )

        eid = uuid.uuid4()
        e1 = substrate.append_event(
            work_item_id=wi.work_item_id,
            actor_id="agent-1",
            transition="custom_event",
            event_id=eid,
        )
        e2 = substrate.append_event(
            work_item_id=wi.work_item_id,
            actor_id="agent-1",
            transition="custom_event",
            event_id=eid,
        )
        assert e1.event_id == e2.event_id
        assert e1.event_seq == e2.event_seq


class TestReplay:
    def test_replay_no_drift(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="test_workflow",
            work_item_type="feature",
            actor_id="agent-1",
            custom_fields={"title": "Replay test"},
        )
        substrate.transition(wi.work_item_id, "start", "agent-1", actor_metadata={"role": "agent"})

        report = substrate.replay()
        assert report.replayed_drift == 0
        assert report.halted == 0
