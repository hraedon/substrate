# Substrate — Agent Guide

## Project Overview

Substrate is a Python library providing coordination and durable state for agent pipelines over Postgres. It implements an event-sourced model with a transactionally-consistent denormalized projection.

**Spec:** `spec.md` is authoritative. `spec.yaml` is a machine-readable sidecar. The spec is amendable when implementation reveals it cannot deliver a stated guarantee — see BC-008/FR-15 for precedent. Amendments are made deliberately, with a breadcrumb resolution note explaining the change; do not silently diverge from the spec.

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
  _replay.py        # Rebuild projection from event log
  _integrity.py     # Startup version compatibility checks
  _workflow.py      # YAML parse, JSON Schema validate, semantic checks
  _hooks.py         # Sync validators + async hook consumer (FR-13)
  _lint.py          # Actor metadata lint helper (FR-18)
  _signing.py       # HMAC-SHA256 signing/verification
  _jcs.py           # RFC 8785 JSON Canonicalization Scheme (rfc8785 lib)
  _keys.py          # Key set management, hot-reload
  _observability.py # Structured logging + Prometheus metrics
  _errors.py        # ErrorCode enum + SubstrateError
  _types.py         # Frozen dataclasses for domain types
  _testing.py       # Test-only helpers (centralizes _mgr coupling)
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
sub.create_link(from_id, to_id, link_type, actor_id, payload=...)
sub.remove_link(from_id, to_id, link_type, actor_id)
sub.replay()  # -> ReplayReport with drift detection
sub.close()

# Phase 2 — hooks, validators, escalation, lint
sub.register_validator(transition_name, fn)        # sync, 5s timeout, blocks transition on failure
sub.register_hook_handler(event_type, fn)          # async dispatch via hook_queue
sub.start_hook_consumer()                          # background thread: LISTEN + 30s poll
sub.stop_hook_consumer()
sub.poll_hooks()                                   # manual drain (in lieu of consumer thread)
sub.list_dead_lettered_hooks()
sub.requeue_dead_lettered_hook(hook_id)
sub.validate_actor_metadata(metadata, schema=None)  # lint helper (FR-18)
```

**API constraints:**
- `append_event` rejects transitions that match a workflow-defined transition name — use `transition()` for state changes
- `heartbeat_claim` accepts optional `expected_attempt_number` to detect stale sessions after claim theft
- Claim mutations (acquire, release, sweep) emit events for audit trail; heartbeats do not
- Escalation (FR-10) fires automatically inside `acquire_claim` when `attempt_number >= attempt_threshold`; sets `needs_review`, emits `escalated`, idempotent
- Hooks dead-letter after max retries and emit `hook_dead_lettered`; replay handles both `escalated` and `hook_dead_lettered`

## Key Design Decisions

1. **Schema-per-project** not DB-per-project. One pool, one backup target, engine-enforced isolation via `GRANT ON SCHEMA`. Migration path to `tenant_id`-in-shared-DB documented but not needed at homelab scale.
2. **Library, not daemon.** Runs in-process. No HTTP server. Exposes `prometheus_client.CollectorRegistry` for host app to mount.
3. **Hybrid persistence.** Events authoritative; projection updated in same transaction. Not pure event-sourcing (no per-read replay cost).
4. **Signing is internal.** RFC 8785 canonicalization + HMAC-SHA256 computed inside the library. Callers submit unsigned field tuples.

## Status

MVP + Phase 2 implemented. All FRs FR-01 through FR-23 are now in tree. 81 tests + 3 scale benchmarks passing across 9 files (smoke, signing, replay, idempotency, concurrency, api_surface, phase2, jcs, scale). All breadcrumbs resolved.

Phase 2 additions: FR-10 (escalation), FR-13 (hooks/validators), FR-14 (dead-letter requeue), FR-18 (lint helper). Migration `003_escalation_idempotency.sql` adds the partial unique index that backstops escalation idempotency.

## Conventions

- Python 3.11+, `from __future__ import annotations` in all files
- No comments in code (style rule)
- Frozen dataclasses for all domain types
- `dict_row` factory on all psycopg connections
- All mutations go through `mgr.transaction()` which sets `SET LOCAL search_path`
- Error codes are part of the API contract (§19.5)
- Tests reach internal state via `substrate._testing` only — never import `_mgr` directly

## Agent Workflow

This project tracks work outside the code. New agents should orient to these conventions before making changes.

### Breadcrumbs (`breadcrumbs/`)

Defects, design questions, and improvements live one-file-per-item under `breadcrumbs/`, with resolved items moved to `breadcrumbs/resolved/`. Schema and severity definitions are in `breadcrumbs/README.md`. Open the index before starting work — it's the canonical "what's known to be wrong" list.

When you notice an issue you're not fixing in this session, file a breadcrumb. When you fix one, move it to `resolved/` and update the README index. The `/end` skill automates both.

### Worklog (`.substrate/worklog.md`)

Reverse-chronological session log. Each entry: focus, context, what was delivered (with file references), breadcrumbs resolved, test/lint results. Read the most recent entry on session start; prepend a new entry on session end.

### Reflections (`.substrate/reflections/`)

Per-session subjective notes from the agent. Useful signal for the next agent — read the latest before starting. Written via the `/reflect` skill.

### Session commands

Substrate-specific wrappers in `.substrate/commands/`:
- `/start` — orient to current state (worklog tail, open breadcrumbs, git status)
- `/end` — run tests, reconcile breadcrumbs, update worklog, write reflection, commit
- `/reflection` — write a reflection only

System-wide skills (`/reflect`, `/end`) provide portable equivalents; the substrate-specific versions add test runs and worklog updates.

## Patterns

### Telemetry via hooks

Substrate's `actor_metadata` is JSONB — free-form structured metadata for downstream consumers. To produce indexed aggregates (e.g., per-role pass rates), register a hook handler on the relevant event types that writes denormalized rows to a consumer-maintained reporting table. The reporting table lives outside substrate's schema; substrate's contract is the authoritative event log, and the reporting table is a derived view that can be rebuilt by replaying events through the same handler.

Recommended shape:

1. **Reporting table** in a separate schema (or external store) with indexed columns for the dimensions you query by.
2. **Hook handler** that reads `actor_metadata`, extracts dimensions, and upserts the reporting row.
3. **Rebuild path**: drain the events table through the same handler in `event_seq` order to reconstruct from scratch.

Do not add denormalized columns to substrate's `events` table for consumer-specific dimensions. Substrate stays general; the consumer maintains its own reporting layer.
