---
number: "041"
title: Conformance tests missing coverage for claim event actor_id, dead-letter, replay drift, hook consumer
severity: medium
status: resolved
kind: improvement
author: glm-5.1
date: "2026-05-07"
origin: validation scan of Deepseek session 10 work
tags: [in-memory, conformance, test-coverage]
related: ["038"]
---

## Observation

The `test_in_memory_conformance.py` suite has 50 parameterized tests but is missing coverage for several behavioral differences:

1. Claim event `actor_id` — no conformance test checks event-level `actor_id` on claim events.
2. `requeue_dead_lettered_hook` and `list_dead_lettered_hooks` — not covered by conformance tests.
3. `read_events` sort order — no test verifies ordering semantics.
4. Replay drift for `needs_review` / `not_before`.
5. `start_hook_consumer` / `stop_hook_consumer` — never called in any test.
6. Event_id idempotency on claims and links (AC-24).

## Resolution

Fixed in session 12. Added `test_hook_consumer.py` (4 tests: lifecycle, idempotent start/stop, poll-based delivery). Added `test_claim_link_idempotency.py` (4 tests: claim acquire/release and link create/remove event_id dedup). Fixed `poll_hooks` to pass `HookContext` instead of raw dict. Fixed `requeue_dead_lettered_hook` to preserve `work_item_id`. Fixed InMemorySubstrate `read_events` to use priority-based matching. Fixed InMemorySubstrate transition key divergence (`from`/`to` vs `from_state`/`to_state`). Fixed `_claims.py` return type annotation.
