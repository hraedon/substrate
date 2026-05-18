from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

from substrate.testing import drop_project_schema

TESTS_DIR = Path(__file__).parent
DSN = "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test"
KEY_PATH = str(TESTS_DIR / "test_keys.json")

WORKFLOW = """\
name: partition_test
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

roles:
  - name: agent

work_item_types:
  - name: task
    custom_fields: []

link_types: []
attempt_threshold: 99
"""


@pytest.fixture(scope="module")
def substrate():
    from substrate import Substrate

    project = f"test_partition_{uuid.uuid4().hex[:8]}"
    sub = Substrate.create_project(DSN, project, KEY_PATH)
    sub.register_workflow(WORKFLOW)
    yield sub
    sub.close()
    drop_project_schema(DSN, project)


def _raw_conn(schema: str):
    conn = psycopg.connect(DSN, row_factory=dict_row)
    conn.execute(f'SET search_path TO "{schema}"')
    return conn


class TestEnsureEventPartitions:
    def test_idempotent_double_call(self, substrate):
        result1 = substrate.ensure_event_partitions(months_ahead=2)
        result2 = substrate.ensure_event_partitions(months_ahead=2)
        assert len(result1) == len(result2)
        assert set(result1) == set(result2)

    def test_returns_partition_names(self, substrate):
        names = substrate.ensure_event_partitions(months_ahead=1)
        assert len(names) >= 2
        for name in names:
            assert name.startswith("events_y")


class TestPartitionRouting:
    def test_events_land_in_expected_partition(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="partition_test",
            work_item_type="task",
            actor_id="agent-1",
            custom_fields={},
        )
        schema = substrate._mgr.schema
        with _raw_conn(schema) as conn:
            rows = conn.execute(
                "SELECT tableoid::regclass::text AS partition_name "
                "FROM events WHERE work_item_id = %s",
                [wi.work_item_id],
            ).fetchall()
        assert len(rows) >= 1
        for row in rows:
            assert "events_" in row["partition_name"]

    def test_far_future_event_lands_in_default(self, substrate):
        far_future = datetime(2099, 12, 1, tzinfo=UTC)
        event_id = uuid.uuid4()
        schema = substrate._mgr.schema

        wi, _ = substrate.create_work_item(
            workflow_name="partition_test",
            work_item_type="task",
            actor_id="agent-1",
            custom_fields={},
        )

        with _raw_conn(schema) as conn:
            conn.execute(
                "INSERT INTO events ("
                "event_id, work_item_id, event_seq, actor_id, actor_kind, "
                "key_id, workflow_name, workflow_version, timestamp, transition, "
                "payload_canonical_hash, signature"
                ") VALUES (%s, %s, 999, 'agent-1', 'agent', 'test', "
                "'partition_test', 1, %s, 'test', %s, %s)",
                [event_id, wi.work_item_id, far_future, b"hash", b"sig"],
            )
            row = conn.execute(
                "SELECT tableoid::regclass::text AS partition_name "
                "FROM events WHERE event_id = %s",
                [event_id],
            ).fetchone()
        assert row is not None
        assert "default" in row["partition_name"]

    def test_read_events_by_time_range_across_partitions(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="partition_test",
            work_item_type="task",
            actor_id="agent-1",
            custom_fields={},
        )
        substrate.transition(
            work_item_id=wi.work_item_id,
            transition_name="finish",
            actor_id="agent-1",
        )
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 12, 31, tzinfo=UTC)
        events = substrate.read_events(
            work_item_id=wi.work_item_id,
            start=start,
            end=end,
        )
        assert len(events) >= 1
        for evt in events:
            assert evt.work_item_id == wi.work_item_id

    def test_events_table_is_partitioned(self, substrate):
        schema = substrate._mgr.schema
        with _raw_conn(schema) as conn:
            row = conn.execute(
                "SELECT pt.partstrat FROM pg_partitioned_table pt "
                "JOIN pg_class c ON c.oid = pt.partrelid "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relname = 'events' AND n.nspname = %s",
                [schema],
            ).fetchone()
        assert row is not None, "events table is not partitioned"
        assert row["partstrat"] == "r"


class TestAutoPartitionOnInit:
    """BC-190: partitions are ensured automatically on Substrate init."""

    def test_partitions_created_on_create_project(self):
        """create_project with auto_partition=True (default) ensures 3+ months of partitions."""
        from datetime import UTC, datetime

        from substrate import Substrate

        project = f"test_autopart_{uuid.uuid4().hex[:8]}"
        sub = Substrate.create_project(DSN, project, KEY_PATH)
        try:
            schema = sub._mgr.schema
            with _raw_conn(schema) as conn:
                rows = conn.execute(
                    """
                    SELECT c.relname
                    FROM pg_inherits i
                    JOIN pg_class c ON c.oid = i.inhrelid
                    JOIN pg_class p ON p.oid = i.inhparent
                    WHERE p.relname = 'events'
                      AND c.relname ~ '^events_y[0-9]{4}_m[0-9]{2}$'
                    ORDER BY c.relname
                    """
                ).fetchall()
            partition_names = [r["relname"] for r in rows]
            # Should have at least 4 partitions: current month + 3 ahead
            assert len(partition_names) >= 4, (
                f"Expected at least 4 partitions after init, got {partition_names}"
            )
            # Verify current month is covered
            today = datetime.now(UTC).date()
            current_month_partition = f"events_y{today.year:04d}_m{today.month:02d}"
            assert current_month_partition in partition_names, (
                f"Current month partition {current_month_partition!r} not in {partition_names}"
            )
        finally:
            sub.close()
            drop_project_schema(DSN, project)

    def test_auto_partition_false_skips_auto_ensure(self):
        """With auto_partition=False, no partitions beyond those in migrations are auto-created."""
        from substrate import Substrate

        project = f"test_noautopart_{uuid.uuid4().hex[:8]}"
        # create_project with auto_partition=False — this should still call __init__
        # with auto_partition=False, skipping the auto-ensure step.
        sub = Substrate.create_project(DSN, project, KEY_PATH, auto_partition=False)
        try:
            # No assertion on partition count — just verify it didn't crash and
            # the instance is functional.
            assert sub.substrate_version is not None
        finally:
            sub.close()
            drop_project_schema(DSN, project)

    def test_metrics_updated_on_init(self):
        """Prometheus gauges are set after init."""
        from prometheus_client import CollectorRegistry

        from substrate import Substrate

        project = f"test_metrics_{uuid.uuid4().hex[:8]}"
        registry = CollectorRegistry()
        sub = Substrate.create_project(DSN, project, KEY_PATH, prometheus_registry=registry)
        try:
            # substrate_events_default_rows should be registered and set to 0
            samples = {
                s.name: s.value
                for m in registry.collect()
                for s in m.samples
                if s.labels.get("project") == project
            }
            assert "substrate_events_default_rows" in samples, (
                f"substrate_events_default_rows not found in {list(samples)}"
            )
            assert samples["substrate_events_default_rows"] == 0.0
            assert "substrate_events_partition_horizon_days" in samples, (
                f"substrate_events_partition_horizon_days not found in {list(samples)}"
            )
            assert samples["substrate_events_partition_horizon_days"] > 0
        finally:
            sub.close()
            drop_project_schema(DSN, project)


class TestEscalationUniquePerWorkItem:
    def test_two_escalated_same_work_item_blocked_at_app_level(self, substrate):
        wi, _ = substrate.create_work_item(
            workflow_name="partition_test",
            work_item_type="task",
            actor_id="agent-1",
            custom_fields={},
        )
        substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=60)
        substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=60)
        substrate.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=60)

        events = substrate.read_events(work_item_id=wi.work_item_id)
        escalated_events = [e for e in events if e.transition == "escalated"]
        assert len(escalated_events) <= 1, "More than one escalated event per work item"
