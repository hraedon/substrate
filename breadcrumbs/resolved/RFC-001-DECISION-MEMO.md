---
number: "RFC-001-DECISION-MEMO"
title: "Event-volume measurements and recommendation for RFC-001"
severity: high
status: decision-pending
kind: design
author: claude
date: "2026-05-18"
related: ["RFC-001", "148", "190", "193"]
---

# RFC-001 Decision Memo — event_id uniqueness vs. partitioning

The original RFC presents three options without quantitative grounding. This memo grounds them in measured event volumes and recommends one.

## Measured event volumes

**sf2 golden runs (the only real consumer today).** GR-038 — the most recent and largest single run — produced these work-item counts across the cert-watch full DAG:

| Stage | Items locked |
|---|---|
| interface_spec | 8 |
| implementation | 13 (12 locked, 1 cannot_proceed) |
| cross_family_review | 11 invocations against ~13 impls |
| jury | 4 locked, 2 cannot_proceed |
| integration | 4 |
| outcome_verification | 4 |
| upstream revisions | 6 |
| **Estimated total work items** | **~50** |

Each work item emits roughly 5–10 events (created, claim_acquired, ≥1 transitions, claim_released, terminal). Per-run event count is therefore on the order of **300–800 events**.

At a generous **10 golden runs/day**, sf2 produces **3K–8K events/day ≈ 90K–240K events/month**.

**Watchpost (the second consumer scaffold).** 3 incidents × 4–5 events/incident = 14 events per demo run. Even scaled to a hundred incidents per day in a real deployment: 500 events/day ≈ 15K events/month.

**Order of magnitude where partitioning starts to pay for itself in practice.** With Postgres 16 and reasonable hardware, monthly-partitioning of an `events` table starts to matter for query latency and vacuum cost at roughly **10M events/month** and above. Index size at that volume begins to push past RAM and partition-pruning saves meaningful I/O.

**sf2 today is 1.5–2 orders of magnitude below that threshold.** Watchpost is 2.5–3 orders below.

## Cost of the partitioned design as currently implemented

Migration 010 (the partitioned events table) is presently load-bearing for four open problems:

1. **BC-148** — global `event_id` uniqueness spec violation. Only enforced by `pg_advisory_xact_lock(_advisory_lock_id(event_id))`, which serializes but does not enforce. The error code on cross-work-item collision (`IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD`) is misleading.
2. **BC-190 (now resolved)** — partition maintenance lifecycle; required adding `auto_partition=True` to `Substrate.__init__` plus startup spill checks and two new gauges. Net new operator surface.
3. **BC-193** — `read_events_by_work_item` uses `last_event_at` as a partition-pruning ceiling, with undocumented snapshot semantics and a NULL fallback that scans all partitions.
4. **RFC-001 itself** — the spec/implementation contract is open, and `IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD` lies to callers.

Roughly **300 lines of code, three open BCs, one new public kwarg, and two new operator-visible metrics** exist because of the partitioning decision. None of that complexity is producing a measurable benefit at current scale.

## Option-by-option assessment (recosted)

### Option A — `event_ids` lookup table for true global uniqueness
- Adds one INSERT per `append_event` against a monotonically growing unindexed-by-time table.
- At 240K events/month worst case today: 8 GB/year of `event_id` UUIDs alone, plus index. Manageable, but the lookup table is not itself partitioned — so the new table grows without bound.
- Fixes BC-148, makes the idempotency error honest, doesn't fix BC-190/BC-193.
- **Verdict:** restores the spec, but inherits the partitioning costs without paying them back.

### Option B — amend spec to per-work-item uniqueness
- Cheapest; every external caller that holds an `event_id` and wants a lookup now needs `(work_item_id, event_id)`.
- Watchpost was scaffolded against the current API. The migration cost on a second consumer is real but bounded (~10–20 LoC).
- **Verdict:** honest about what the table enforces, but doesn't simplify any of the partitioning costs.

### Option C — revert migration 010
- Restores single-table `events` with a global unique index on `event_id`.
- Closes BC-148 trivially (the index enforces uniqueness).
- Makes BC-190's `auto_partition` mechanism unnecessary; the kwarg becomes a no-op (keep for back-compat).
- Closes BC-193's NULL-fallback bug; no partition ceiling needed.
- Cost: a down-migration to fold `events_*` partitions back into a flat table. Doable; needs a one-shot maintenance window.
- Risk: if sf2 scale 10×s in the next 12 months, partitioning was a good bet retired prematurely. At 8K events/day × 10 = 80K/day = 2.4M/month — still 4× below the threshold where partitioning matters.
- **Verdict:** the simplest, the cheapest to operate, and structurally retires three of the four open problems above. Re-introducing partitioning later if sf2 or another consumer crosses ~10M events/month is a focused 1–2 week project, not an architectural emergency.

## Recommendation

**Option C** — revert migration 010 and restore single-table `events` with a global `event_id` unique index.

This is the option I lean toward for these reasons:

1. **Quantitatively, sf2 + watchpost are not within 1.5 orders of magnitude of needing partitioning.** Carrying the cost today is paying for an unmeasured future.
2. **It closes BC-148, BC-190's complexity, and BC-193 in one move**, instead of point-fixing each. Three open problems become zero.
3. **Re-introducing partitioning is a known recipe** if scale demands it — `pg_partman` and similar are mature. The reverse direction (un-partitioning a live prod) is harder, and you don't know yet whether the consumer mix will need monthly, weekly, or per-tenant partitioning. Don't lock that in now.
4. **The honest error semantics around idempotency become possible.** Today the `IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD` story is wrong; under Option C the unique index gives an honest `EVENT_ID_GLOBAL_COLLISION`.

## What I need from you to proceed

A clear "go" on Option C (or override). On "go," next steps are:

1. Write migration 014: drop partitions, recreate `events` flat, add `UNIQUE INDEX ON events (event_id)`, copy data, drop legacy partition tables. Test on a synthetic dataset of 100K events for correctness; measure cutover time.
2. Remove `pg_advisory_xact_lock` from `append_event` and `check_idempotency`; the unique index does the work.
3. Update `_contract.check_idempotency` to raise `EVENT_ID_GLOBAL_COLLISION` for cross-work-item collisions instead of `IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD`.
4. Mark `Substrate.__init__(auto_partition=...)` as deprecated (no-op), remove `events_default` row gauge, remove `partition_horizon_days` gauge.
5. Close BC-148, BC-190 follow-ups, BC-193 with pointers to this RFC.
6. Document in spec.md the volume threshold at which partitioning would be revisited.

Total: a focused 1–2 day implementation. Lower-risk than continuing to point-fix the current scheme.

## If you prefer Option B

The work is smaller (just spec + error code + a few docstrings), but you do not retire the cost of partitioning — you accept it for the foreseeable future and just stop pretending the table enforces a global property it doesn't. Honest, but each future consumer pays the partitioning tax in lifecycle ops and read-path complexity.

## If you prefer Option A

Implementable. Adds ~150 LoC, one new table, one new error code. Retires BC-148. Doesn't retire BC-190 or BC-193. Most expensive long-term option.
