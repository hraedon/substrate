---
number: "054"
title: InMemorySubstrate transition() resets attempt_number by clearing _claims entry
severity: high
status: resolved
kind: bug
author: opencode (factory-team)
date: "2026-05-08"
tags: [in-memory, claims, postgres, test-fidelity, dep-substrate-036]
related: ["036", "005", "039"]
---

## Problem

`InMemorySubstrate.transition()` unconditionally calls `self._claims.pop(work_item_id, None)` after appending the transition event. This removes the claim entry entirely, so the next `acquire_claim` for the same work item starts fresh with `attempt_number = 1`.

The real Postgres Substrate had the same bug: `release_claim` and `sweep_expired_claims` both `DELETE FROM claims`, and `transition` also deletes via `release_claim=True`. The next `acquire_claim` finds no existing claim row and starts at `attempt_number = 1`. Both backends needed the same fix.

## Downstream impact

This was discovered by the software-factory-2 team (BC-036). In SF2's pipeline:

1. Worker claims work item, produces artifact, submits → state transitions to `gating`
2. Gate claims work item, evaluates artifact, transitions `gate_fail` → state returns to `new`
3. Worker re-claims the work item to retry

On the real Postgres backend, `attempt_number` increments across this cycle, so after `attempt_threshold` failures the escalation path fires and routes the item to `cannot_proceed_seam`. On InMemorySubstrate, `attempt_number` resets to 1 at step 3, so escalation can never trigger through normal pipeline flow.

## Evidence

SF2's `test_e2e_escalation_through_three_gate_failures` had to inject a `SimpleNamespace(attempt_number=3)` fake claim object on the 3rd gate cycle to trigger escalation. The real pipeline with InMemorySubstrate would never escalate because every `gate_fail` → `new` → `claim` cycle resets to attempt 1.

## Fix

Preserve the attempt counter on the work item state dict (or derive it from `claim_acquired`/`claim_stolen` event count) so that `acquire_claim` increments from the previous value regardless of whether the claim was released or expired.

Two options:

(a) **Store persistent attempt_number on work item state.** Add `attempt_number` to the `_work_items` dict. `acquire_claim` reads the current value, increments, writes back. `transition()` does not clear it. This matches the likely Postgres implementation.

(b) **Derive from event history.** In `acquire_claim`, count `claim_acquired` + `claim_stolen` events for the work item and use that as `attempt_number`. No extra mutable state, but O(n) on event history.

Option (a) is preferred — minimal change, O(1), matches real backend semantics.

## Resolution

Option (a) applied to both backends:

- **InMemory**: Added `attempt_number` (initialized to 0) to the `_work_items` dict. `acquire_claim` reads `wi["attempt_number"] + 1` instead of deriving from the claims entry. `transition()` and `release_claim()` still clear the claim entry but `attempt_number` persists on the work item state.
- **Postgres**: Migration `006_work_item_attempt_number.sql` adds `attempt_number INTEGER NOT NULL DEFAULT 0` to `work_items_current`. `acquire_claim` reads `wi["attempt_number"] + 1` and updates it. `lock_work_item` SELECT includes the new column. Replay tracks `attempt_number` from `claim_acquired`/`claim_stolen` events and drift-detects it. `_WORK_ITEM_FIELDS` includes it for internal queries.
- Tests updated: `test_e2e.py` assertions reflect that attempt_number increments across claim-release cycles (2nd claim = attempt 2, 3rd = attempt 3).

## Acceptance criteria

- [x] InMemorySubstrate `acquire_claim` increments `attempt_number` across transition/claim-release cycles
- [x] Postgres `acquire_claim` increments `attempt_number` across transition/claim-release cycles
- [x] Escalation threshold (`_check_escalation`) fires after the configured number of attempts in both backends
- [x] Replay tracks and drift-detects `attempt_number`
- [x] Existing tests pass (no regressions in claim/heartbeat/escalation semantics)
