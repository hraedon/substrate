# Substrate — Agent Guide

## Project Overview

Substrate is a Python library providing coordination and durable state for agent pipelines over Postgres. It implements an event-sourced model with a transactionally-consistent denormalized projection.

**Spec:** `spec.md` is authoritative. `spec.yaml` is a machine-readable sidecar.

## Architecture

### Isolation: Schema-per-project

One Postgres database, one schema per project. The `Substrate` handle owns one logical project namespace. Connection pool is shared; `SET LOCAL search_path` scopes each transaction.

### Core data model

- **Events** (`events` table): immutable append-only log. Gap-free `event_seq` per work-item, allocated under canonical row lock.
- **Projection** (`work_items_current`): denormalized, transactionally-consistent with events. Fully derivable from event log via replay.
- **Claims** (`claims` table): durable leases with TTL, attempt tracking, auto-steal on expiry.
- **Workflow registry** (`workflow_registry`): append-only, versioned workflow definitions. Work-items pin their version at creation.

### Key invariants

- Events are the authoritative source. `work_items_current` is a projection, never edited directly.
- Every mutation acquires `SELECT FOR UPDATE` on the work-item's row in `work_items_current`.
- Library is the sole signer (HMAC-SHA256 over RFC 8785 canonical JSON). API rejects pre-signed events.
- `synchronous_commit = on` on all connections.

## Source Layout

```
src/substrate/
  __init__.py       # Public API: Substrate class
  _connection.py    # Connection pool, schema-per-project
  _migrations.py    # Migration runner
  _events.py        # Event append, idempotency, seq allocation
  _work_items.py    # Create, query (FR-05b)
  _claims.py        # Claim lifecycle
  _links.py         # Typed directed links
  _transitions.py   # (merged into __init__.py transition method)
  _replay.py        # Rebuild projection from event log
  _integrity.py     # Startup version compatibility checks
  _workflow.py      # YAML parse, JSON Schema validate, semantic checks
  _signing.py       # HMAC-SHA256 signing/verification
  _jcs.py           # RFC 8785 JSON Canonicalization Scheme
  _keys.py          # Key set management, hot-reload
  _observability.py # Structured logging + Prometheus metrics
  _errors.py        # ErrorCode enum + SubstrateError
  _types.py         # Frozen dataclasses for domain types
  _workflow_schema.json  # JSON Schema for workflow YAML files
```

## Testing

```bash
# Start Postgres
docker compose -f docker-compose.test.yml up -d

# Run tests
.venv/bin/python -m pytest tests/ -v

# Lint
.venv/bin/ruff check src/
```

Test DSN: `postgresql://substrate_test:substrate_test@localhost:5432/substrate_test`
Test keys: `tests/test_keys.json`
Sample workflow: `tests/test_workflow.yaml`

## Public API (§19)

The `Substrate` class is the sole entry point. No Postgres internals leak across the boundary.

```python
from substrate import Substrate

# Create a new project
sub = Substrate.create_project(dsn, "my_project", hmac_key_path="/path/to/keys.json")

# Connect to existing
sub = Substrate(dsn, "my_project", hmac_key_path="/path/to/keys.json")

# Operations
sub.register_workflow(yaml_content)
sub.create_work_item(workflow_name, work_item_type, actor_id, ...)
sub.transition(work_item_id, transition_name, actor_id, ...)
sub.append_event(work_item_id, actor_id, *, transition=..., payload=...)
sub.acquire_claim(work_item_id, actor_id, ttl_seconds=300)
sub.heartbeat_claim(work_item_id, actor_id, ttl_seconds, *, expected_attempt_number=...)
sub.release_claim(work_item_id, actor_id)
sub.sweep_expired_claims()
sub.query_work_items(workflow_name=..., current_states=[...], claimable_now=True)
sub.read_events(work_item_id=...)
sub.create_link(from_id, to_id, link_type, actor_id)
sub.remove_link(from_id, to_id, link_type, actor_id)
sub.replay()  # -> ReplayReport with drift detection
sub.close()
```

**API constraints:**
- `append_event` rejects transitions that match a workflow-defined transition name — use `transition()` for state changes
- `heartbeat_claim` accepts optional `expected_attempt_number` to detect stale sessions after claim theft
- Claim mutations (acquire, release, sweep) emit events for audit trail; heartbeats do not

## Key Design Decisions

1. **Schema-per-project** not DB-per-project. One pool, one backup target, engine-enforced isolation via `GRANT ON SCHEMA`. Migration path to `tenant_id`-in-shared-DB documented but not needed at homelab scale.
2. **Library, not daemon.** Runs in-process. No HTTP server. Exposes `prometheus_client.CollectorRegistry` for host app to mount.
3. **Hybrid persistence.** Events authoritative; projection updated in same transaction. Not pure event-sourcing (no per-read replay cost).
4. **Signing is internal.** RFC 8785 canonicalization + HMAC-SHA256 computed inside the library. Callers submit unsigned field tuples.

## MVP Status

All MVP FRs implemented: FR-01 through FR-04, FR-05, FR-05b, FR-06 through FR-09b, FR-11, FR-12, FR-15 through FR-17, FR-19 through FR-23. 20 smoke tests passing.

**Deferred to Phase 2:** FR-10 (escalation), FR-13 (hooks/validators), FR-14 (dead-letter requeue), FR-18 (lint helper).

## Conventions

- Python 3.11+, `from __future__ import annotations` in all files
- No comments in code (style rule)
- Frozen dataclasses for all domain types
- `dict_row` factory on all psycopg connections
- All mutations go through `mgr.transaction()` which sets `SET LOCAL search_path`
- Error codes are part of the API contract (§19.5)
