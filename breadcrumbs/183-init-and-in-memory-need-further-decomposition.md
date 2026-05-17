---
number: "183"
title: __init__.py and _in_memory.py still exceed 1300 lines — need further decomposition
severity: medium
status: proposed
kind: improvement
author: session-agent
date: "2026-05-17"
tags: [refactoring, maintainability, code-health]
related: []
---

## Observation

Even after extracting `transition()` to `_transition.py` (BC-128) and recurrence to `_recurrence_api.py` (Plan 003), the two primary entry-point files remain too large:

- `src/substrate/__init__.py` — 1,389 lines (down from ~1,580, target ~800)
- `src/substrate/_in_memory.py` — 1,619 lines (up from ~1,500, target ~800)

Both files still contain:

1. Claim lifecycle (`acquire_claim`, `heartbeat_claim`, `release_claim`, `sweep_expired_claims`) — recently extracted to `_claims_api.py` for Postgres, but **the InMemory versions remain inline**.
2. Link operations (`create_link`, `remove_link`) — similarly extracted to `_links_api.py` for Postgres only.
3. Hook primitives — `poll_hooks`, `claim_hooks`, `complete_hook`, `fail_hook`, `sweep_expired_hook_leases` (Postgres), and the full async consumer lifecycle (`start/stop_hook_consumer`, `_move_to_dead_letter`).
4. Workflow I/O — `register_workflow`, `register_workflow_file`, `get_workflow`.
5. Event store I/O — `read_events`, `read_events_since`, `append_event`.
6. Work-item primitives — `create_work_item`, `get_work_item`, `query_work_items`.
7. Replay — `replay()` (Postgres) / `replay()` (InMemory).
8. Recurrence — rules registration, listing, firing, cancellation.
9. Dead-letter hooks — `requeue_dead_lettered_hook`, `list_dead_lettered_hooks`.
10. Actor roles — CRUD + gating (partially delegated to `_actor_roles.py`).
11. Static lint helpers — `validate_actor_metadata`, `actor_metadata_complete`.

The asymmetry is notable: Postgres backend delegates to modules (`_transition.py`, `_recurrence_api.py`, `_claims_api.py`, `_links_api.py`), whereas InMemory still embeds most of the same logic inline. Keeping them inline risks future drift and makes code review hard.

## Proposed decomposition

### Phase A — align InMemory with existing extraction modules

1. **InMemory claims** → move body of `acquire_claim`, `heartbeat_claim`, `release_claim`, `sweep_expired_claims` to a new `src/substrate/_in_memory_claims.py` module matching the shape of `_claims_api.py` (pure functions, no timer/metrics inline).
2. **InMemory links** → move body of `create_link`, `remove_link` to `src/substrate/_in_memory_links.py`.
3. **InMemory hooks** → extract hook queue logic (`poll_hooks`, `_move_to_dead_letter`, etc.) to `src/substrate/_in_memory_hooks.py`.
4. **InMemory recurrence** → wrap existing `_recurrence` functions similarly to `_recurrence_api.py`.

### Phase B — extract common work-item / event I/O helpers

5. **Postgres + InMemory create_work_item** → extract orchestration to `_work_items_api.py` and `_in_memory_work_items.py`. Both already have `_work_items.py` for the DB side; the InMemory `_create_work_item` helper is ~80 lines.
6. **Postgres + InMemory append_event / read_events** → a shared `src/substrate/_events_api.py` for orchestration (validation → store call → metric increment). InMemory stays separate, but the boilerplate (timer, metrics) is identical.

### Phase C — shared facade layer

7. **Unified facade idea rejected** — Postgres and InMemory backends intentionally diverge on connection management (`mgr.transaction()` vs dict manipulation). A fully shared "API orchestration" class would hide these differences unhelpfully. Phase A+B is the right granularity.

## Risks

- Extraction must preserve the existing `copy-on-write` and event ordering invariants in InMemory (especially claim state update order).
- Moving code out of `_in_memory.py` will break any direct imports from that file. The test suite reaches internals via `substrate._testing` and `InMemorySubstrate` public methods only, so risk is low.
- Metrics/timing: `_claims_api.py` and `_links_api.py` currently own `OpTimer` + `_metrics.inc`. InMemory decomposition can follow the same model, or alternatively keep metrics in the top-level method and pass the inner logic down. Need to pick one.

## Acceptance criteria

- `__init__.py` ≤ 900 lines.
- `_in_memory.py` ≤ 900 lines.
- All existing tests pass without changes.
- No new imports of private extracted modules from outside `src/substrate/`.
