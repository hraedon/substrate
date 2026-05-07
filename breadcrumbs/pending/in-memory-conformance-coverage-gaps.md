---
number: "pending"
title: Conformance tests missing coverage for claim event actor_id, dead-letter, and replay drift scenarios
severity: medium
status: draft
kind: improvement
author: glm-5.1
date: "2026-05-07"
origin: validation scan of Deepseek session 10 work
tags: [in-memory, conformance, test-coverage]
related: ["038"]
---

## Observation

The `test_in_memory_conformance.py` suite has 50 parameterized tests but is missing coverage for several behavioral differences that the Deepseek reflection and this session's scan identified:

1. **Claim event `actor_id`**: The real Substrate uses the claiming/releasing actor's `actor_id` in claim events; the in-memory backend was hardcoding `"system"` (fixed in this session). No conformance test checks event-level `actor_id` on claim events.

2. **`requeue_dead_lettered_hook` and `list_dead_lettered_hooks`**: Not covered by conformance tests at all.

3. **`read_events` sort order**: No test verifies that events come back in the documented order (DESC for `work_item_id`, DESC for `actor_id`/`transition`, ASC for `read_events_since`).

4. **Replay drift for `needs_review` / `not_before`**: The conformance `test_replay_no_drift` only checks that replay returns zero drift after normal operations. It doesn't test that escalation-induced `needs_review=True` or `update_not_before`-induced `not_before` changes are correctly derived by replay.

## Proposed

Add test cases to `test_in_memory_conformance.py` for each gap. The parameterized pattern already exists — these are additive test methods.

## Why medium severity

Medium because the conformance suite is the primary guard against InMemorySubstrate drift from the real backend. Without these tests, regressions like the claim-actor-id bug (which lived in the codebase) are invisible until a downstream consumer hits them in production.