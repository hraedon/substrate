---
number: "164"
title: "`_find_next_future_slot` 10000-iter cap silently loses slots on sub-minute schedules"
severity: medium
status: resolved
kind: bug
author: opus-4-7
date: "2026-05-16"
tags: [recurrence, catch-up, plan-003]
related: []
---

## Problem

`src/substrate/_recurrence.py:_find_next_future_slot` uses a 10000-iteration guard to advance through missed slots during catch-up. At a 5-minute interval this covers ~34 days; at a 1-second interval it covers ~2.7 hours.

When the iteration cap is hit, the function returns whatever slot it reached — which may still be in the past — without raising or signaling truncation to the caller. For `fire_once` and `skip` catch-up policies, this means the rule effectively "loses" the slots that fell between the iteration cap and now, and re-anchors to a still-stale `next_fire_at`.

Per the Session 28 (early) reflection (`2026-05-16-glm-5-1-2.md`), this is documented but not surfaced. The original author considered it acceptable for typical schedules; it becomes a real bug for sub-minute schedules or long downtime windows.

## Impact

- Sub-minute recurrence schedules (every-second polling, every-10-second heartbeats) silently lose fire events after any downtime longer than the cap-coverage window.
- The `fire_once` policy, which should "skip stale slots and fire once at the next future slot," instead fires at a slot that may still be in the past, then the consumer loop has to catch up again — defeating the policy.
- No metric, log, or error indicates truncation occurred.

## Files / Lines

- `src/substrate/_recurrence.py` — `_find_next_future_slot`

## Fix

Two coordinated changes:

1. **Replace iteration cap with elapsed-time math.** Instead of iterating slot-by-slot, compute `slots_missed = (now - last_fire_at) // interval` directly (where the schedule has a constant interval). For cron-style or irregular schedules, fall back to iteration but raise a structured `SubstrateError(RECURRENCE_CATCH_UP_OVERFLOW)` if the cap is hit, rather than returning a stale slot.
2. **Emit a metric** (`recurrence_catch_up_truncated_total` with rule_id label) when the fallback iteration hits the cap, so operators can see when schedules are too dense for the cap.

If §1 is too invasive, the minimum fix is §2 plus raising on cap-hit so the caller cannot silently consume a stale slot.

## Lesson

Iteration caps that silently return a partial result are a common source of "works in dev, fails at scale" bugs. The cap is fine; the silent partial return is what makes it dangerous. Either compute the answer in closed form, or fail loudly when the cap is reached.
