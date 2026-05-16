---
number: "163"
title: "Sidecar hook lifecycle tests are stubs — Plan 005 §10 not fully exercised"
severity: medium
status: resolved
kind: improvement
author: opus-4-7
date: "2026-05-16"
tags: [sidecar, plan-005, test-coverage, hook]
related: ["161"]
---

## Problem

Per Session 28 reflection (`2026-05-16-glm-5-1.md`), the sidecar test suite does not exercise the hook claim/complete/fail lifecycle end-to-end. `test_claim_complete_round_trip` and `test_hook_lease_expiry_requeues` are stubs (pass/skip) because the test workflow doesn't declare hooks on its transitions, so no hooks get enqueued for the sidecar to claim.

Plan 005 §10 specifies 13 sidecar test cases; ~10 are meaningfully exercised. The missing 3 are the hook-lifecycle paths — exactly the surface area that BC-161 (the `update_recurrence_rule` body/query bug) hides behind.

## Impact

- The hook routes (`/v1/claim_hooks`, `/v1/heartbeat_hook`, `/v1/complete_hook`, `/v1/fail_hook`) have no end-to-end coverage through HTTP.
- Future regressions in hook payload shape, lease semantics, or error mapping will not be caught by CI.
- The sidecar is presented as feature-complete for Plan 005 but has a coverage gap in its load-bearing operational path (hook consumers are how external workers integrate with substrate).

## Files / Lines

- `tests/sidecar/test_sidecar.py` — `test_claim_complete_round_trip`, `test_hook_lease_expiry_requeues`, and one other hook test
- `plans/005-http-sidecar.md` §10

## Fix

1. Add a fixture workflow to `tests/sidecar/` that declares hooks on at least one transition.
2. Implement the three test cases against that workflow:
   - claim → complete round trip (happy path, asserts hook event recorded)
   - lease expiry causes hook to requeue (sweep-driven)
   - heartbeat extends lease (no requeue during active work)
3. If `tests/sidecar/` grows past one file, move shared fixtures to `tests/sidecar/conftest.py`.

## Lesson

Stubbed tests are honest about gaps but easy to forget. A `pytest.mark.xfail(reason="...")` or `@pytest.mark.skip(reason="...")` with a tracking BC number would have made the gap impossible to lose track of.
