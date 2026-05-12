---
number: "128"
title: Extract shared EventStore protocol to prevent backend divergence
severity: high
status: proposed
kind: design
author: adversarial-review
---

## Problem

`_contract.py` (RFC-062) centralised validation and decision logic (the "what should happen" layer), but the sequencing, persistence, and side-effect layer (the "how it gets recorded" layer) is still implemented independently in each backend.

Every InMemory bug in the recent adversarial review — off-by-one seq, missing idempotency, missing input validation, broken filter defaults, in-place mutation — lived in that second layer. The InMemory backend reinvents what `_events.py` does for Postgres:

- `_events` dict ≈ `events` table
- `_event_id_index` ≈ `event_id` unique constraint
- `_append_claim_event` / `_append_simple_event` ≈ `append_event()` / `append_transition_event()`
- Manual `next_event_seq` bookkeeping ≈ `SELECT FOR UPDATE` + `next_event_seq` column

## Proposal

Extract a backend-agnostic `EventStore` protocol (or ABC) that both backends implement:

```python
class EventStore(Protocol):
    def allocate_seq(self, work_item_id: UUID) -> int: ...
    def check_idempotency(self, event_id: UUID) -> Event | None: ...
    def append(self, event: Event) -> None: ...
    def read(self, filters) -> list[Event]: ...
```

Both backends use the same `EventStore` implementation for sequencing. The InMemory version wraps dict-based storage but delegates seq allocation, idempotency checking, and event construction to shared code — exactly what `_events.py` already does for Postgres. The only backend-specific part is the actual storage primitive (SQL INSERT vs dict append).

## Impact

- Kills the entire class of seq/idempotency/filter divergence bugs in one structural change.
- Any future backend (SQLite, etc.) gets the same guarantees for free.
- InMemorySubstrate shrinks significantly, becoming a thin wrapper over shared logic.

## Risks / Blockers

- InMemorySubstrate is used by downstream tests; internal dict names (`_events`, `_work_items`) may be reached by external code despite being private. The public API must not change.
- The Postgres backend currently bundles event append with projection update in the same transaction. The protocol must preserve this atomicity guarantee.
- This is a larger refactor than the recent fixes; should be planned carefully and rolled out incrementally, not in a single session.

## Acceptance Criteria

1. `EventStore` protocol defined in `_contract.py` or new `_event_store.py`.
2. Postgres backend refactored to use `PostgresEventStore` implementing the protocol.
3. InMemory backend refactored to use `InMemoryEventStore` implementing the protocol.
4. All 400+ tests pass without modification (public API unchanged).
5. Property-based conformance tests continue to pass.

## Related

- RFC-062 (single-source-of-truth backend contract)
- BC-114 through BC-127 (all recent divergence bugs)
- GLM feedback on structural prevention, 2026-05-12
