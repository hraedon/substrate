---
number: "140"
title: "Property test reuse_eid strategy never fires — idempotency coverage is dead"
severity: medium
status: proposed
kind: bug
author: glm-5.1
date: "2026-05-13"
tags: [testing, idempotency, hypothesis]
related: ["128"]
---

## Problem

The `operation` composite strategy in `tests/test_property_conformance.py` accepts a `seen_event_ids` parameter to enable idempotent retries via `reuse_eid`. However, it is invoked as `st.lists(operation())` — hypothesis generates each element independently and cannot thread the `event_id_pool` list back into the strategy between draws.

The result: `seen_event_ids` is always `None`, `prior_eid` is always `None`, and every operation gets a fresh UUID. The idempotency infrastructure (the `reuse_eid` field, the `event_id_pool` parameter on `_exec_op`) is structurally present but never exercised by the property tests.

## Proposed fix

Replace the `st.lists(operation())` approach with one of:

1. **Iterative loop** — draw one `operation()` at a time inside the test body, maintain `event_id_pool` as a mutable list, and pass it to a stateful wrapper that can feed it back into subsequent draws via `st.data()`.
2. **`RuleBasedStateMachine`** — hypothesis-native stateful testing with a shared state bundle containing `event_id_pool`. Each rule draws an operation and can inspect/modify the pool.

Option 1 is lower-effort and doesn't require restructuring the test class. Option 2 is more idiomatic hypothesis but heavier.

## Acceptance criteria

1. Property tests actually generate idempotent retries (verify by adding a temporary counter or print).
2. Both `test_random_sequences_equivalent` and `test_adversarial_equivalent` exercise reuse.
3. Existing 419 tests still pass.
