---
number: "116"
title: InMemory claim/link operations bypass idempotency checks
severity: critical
status: implemented
kind: bug
author: adversarial-review
---

## Problem

`InMemorySubstrate.acquire_claim`, `release_claim`, `create_link`, and `remove_link` accept an explicit `event_id` parameter but never check `self._event_id_index` before emitting events. Calling any of them twice with the same `event_id` appends two events with the **same `event_id` but different `event_seq`**, violating the "unique within project" guarantee that the Postgres backend enforces.

## Impact

Tests using explicit `event_id` on these paths can silently create corrupt event logs that replay cannot reconcile. Duplicate `event_id`s break idempotency, the audit trail, and downstream deduplication.

## Fix

Add `check_idempotency(self._event_id_index.get(event_id), ...)` before event creation in these four methods, matching the Postgres backend behavior.

## Related

- `_in_memory.py` `acquire_claim`, `release_claim`, `create_link`, `remove_link`
- `_events.py` `check_idempotency`
- Spec FR-03: event_id uniqueness
