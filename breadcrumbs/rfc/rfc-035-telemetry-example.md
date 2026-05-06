# RFC-035: Telemetry-via-hooks pattern — add worked example

---
number: "035"
title: Telemetry-via-hooks pattern needs a concrete worked example
severity: low
status: proposed
kind: improvement
author: perplexity-review
related: ["024"]
---

## Current state

AGENTS.md § Patterns > Telemetry via hooks describes the pattern abstractly:

1. Reporting table in a separate schema with indexed columns.
2. Hook handler that reads `actor_metadata`, extracts dimensions, upserts the reporting row.
3. Rebuild path: drain events table through the handler in `event_seq` order.

This is correct, but it describes *what* to do, not *how* to actually do it. A reader who wants to implement telemetry for their substrate deployment must infer the table schema, the handler signature, the SQL for upsert, and the rebuild loop from first principles.

## Problem

The pattern is an important part of the substrate value proposition (event log as the single source of truth), but the barrier to adoption is unnecessarily high. A minimal, copy-pasteable example would dramatically lower that barrier.

## Assessed severity: low

Not a correctness issue. Documentation polish. Target audience: substrate operators building observability on top of the event log.

## Proposed addition

Add a new file under `examples/` (e.g., `examples/telemetry_via_hooks.py`) with a **complete, runnable minimal example**.

### Suggested shape

```python
"""Minimal telemetry-via-hooks example for substrate.

This example:
1. Creates a reporting table in a non-substrate schema.
2. Registers a hook handler on "created" and "start" events.
3. Rebuilds the reporting table from scratch by replaying events.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import psycopg

from substrate import Substrate

DSN = "postgresql://..."
KEY_PATH = "/path/to/keys.json"
REPORTING_SCHEMA = "substrate_analytics"


# Step 1: Create the reporting table (outside substrate's schema).
# The consumer owns this table; it is a derived view rebuildable from events.
def ensure_reporting_schema(conn: psycopg.Connection, project: str) -> None:
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {REPORTING_SCHEMA}")
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {REPORTING_SCHEMA}.transitions_by_role (
            id SERIAL PRIMARY KEY,
            work_item_id UUID NOT NULL,
            transition TEXT NOT NULL,
            role TEXT,
            model TEXT,
            actor_id TEXT NOT NULL,
            occurred_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_role
        ON {REPORTING_SCHEMA}.transitions_by_role (role, occurred_at)
        """
    )


# Step 2: Hook handler.
# Called asynchronously when a matching event is enqueued.
def record_transition_to_analytics(
    event_id: uuid.UUID,
    work_item_id: uuid.UUID,
    transition: str,
    actor_id: str,
    actor_metadata: dict | None,
    timestamp: datetime,
    **kwargs: object,
) -> None:
    role = (actor_metadata or {}).get("role")
    model = (actor_metadata or {}).get("model")

    # Use a dedicated connection or the shared pool.
    # In production, you might batch-insert and flush periodically.
    with psycopg.connect(DSN) as conn:
        conn.execute(
            f"""
            INSERT INTO {REPORTING_SCHEMA}.transitions_by_role
            (work_item_id, transition, role, model, actor_id, occurred_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            [work_item_id, transition, role, model, actor_id, timestamp],
        )
        conn.commit()


# Step 3: Rebuild path.
# Drain all events in event_seq order through the same handler.
def rebuild_analytics(sub: Substrate) -> None:
    with psycopg.connect(DSN) as conn:
        # Clear derived table
        conn.execute(f"TRUNCATE {REPORTING_SCHEMA}.transitions_by_role")
        conn.commit()

    # Read events in batches.  In production, paginate by work_item_id or
    # event_seq.
    page = sub.read_events(limit=1000)
    for event in page:
        if event.transition in ("created", "start", "submit_review", "approve", "reject"):
            record_transition_to_analytics(
                event_id=event.event_id,
                work_item_id=event.work_item_id,
                transition=event.transition,
                actor_id=event.actor_id,
                actor_metadata=event.actor_metadata,
                timestamp=event.timestamp,
            )


# Example bootstrap
def main() -> None:
    sub = Substrate(DSN, "my_project", KEY_PATH)

    with psycopg.connect(DSN) as conn:
        ensure_reporting_schema(conn, sub.project)

    # Register handler on relevant transitions.
    sub.register_hook_handler("created", record_transition_to_analytics)
    sub.register_hook_handler("start", record_transition_to_analytics)

    # Start background consumer (or use poll_hooks() manually).
    sub.start_hook_consumer()

    # ... application runs ...

    # If migration or corruption requires rebuild:
    # rebuild_analytics(sub)

    sub.stop_hook_consumer()
    sub.close()


if __name__ == "__main__":
    main()
```

## Recommendation

1. Add the example file as `examples/telemetry_via_hooks.py`.
2. Update AGENTS.md § Patterns > Telemetry via hooks to link to the example file.
3. The example should be kept runnable with a `docker compose` Postgres instance if possible (or clearly marked as "requires DSN editing").

## Questions to resolve

1. Should the example use a raw `psycopg` connection or demonstrate using `sub._mgr.connect()` (which already handles `search_path`)? The latter is more substrate-native but leaks internals.
2. Should the example include a `pyproject.toml` snippet for dependencies, or is `import psycopg` sufficient?
3. Should the rebuild path use `sub.read_events_since()` (FR-29) for incremental rebuilds instead of full `TRUNCATE`?
