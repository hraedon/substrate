---
number: "194-MEASUREMENT"
title: "Event-volume measurement for BC-194 (heartbeat-event proposal)"
severity: medium
status: decision-pending
kind: design
author: claude
date: "2026-05-18"
related: ["194", "189"]
---

# BC-194 Measurement Memo — what does emitting a heartbeat event actually cost?

The BC offers two options without grounding: (1) emit a `claim_heartbeat` event each heartbeat, (2) coalesce on a delta threshold. This memo measures the cost of each option in the two real consumers today and recommends.

## Today's baseline: zero heartbeats in the wild

`grep heartbeat_claim` across both `/projects/software-factory-2/src/` and `/projects/watchpost/src/`:

- **sf2:** zero call sites.
- **watchpost:** zero call sites.

Neither current consumer calls `heartbeat_claim`. The cost analysis below is therefore hypothetical — modeling what would happen *if and when* consumers adopt heartbeats. **There is no live cost today.** That makes this a good time to design the contract, before downstream code accumulates around a wrong default.

## Modeling option 1 (event per heartbeat)

Assume the substrate default heartbeat cadence is **30 s** (matches the hook-consumer poll interval in `_hooks.py`, the closest precedent for "how often does substrate tick").

### sf2 shape

GR-038 produced ~50 work items. Worker claims are typically short — review, jury, integration are usually ≤5 minutes. Inner-gate retries can extend to ~15 minutes for hard cases.

- Assume mean claim duration **5 minutes** = 10 heartbeats at 30 s cadence.
- 50 work items × ~3 stages with worker claims = 150 active-claim windows.
- 150 × 10 heartbeats = **1,500 extra events per GR-038-sized run.**
- Baseline event volume per run: **300–800** (from `RFC-001-DECISION-MEMO.md`).
- **Cost ratio: 2–5× event volume increase.** Tolerable; doubles to quintuples storage and replay cost. The single largest event-volume driver, dominating actual transitions.

### Watchpost shape

The whole point of watchpost's lifecycle is long-lived states. `awaiting_human` can sit for hours-to-days. If a human-ack workflow heartbeats the claim the whole time:

- 1 incident in `awaiting_human` for 24 h with 30 s heartbeats = **2,880 heartbeat events**.
- At 100 incidents/day in a real deployment: **288,000 heartbeat events/day** just from one state.
- Baseline incident event volume: ~5 events/incident × 100 = 500 events/day from non-heartbeat sources.
- **Cost ratio: 576× event volume increase.** Catastrophic.

The two consumers want fundamentally different things. sf2's heartbeat cost is acceptable; watchpost's is not.

## Modeling option 2 (coalesced heartbeat event)

Emit a `claim_heartbeat` event only when `(new_expires_at - last_emitted_expires_at) >= threshold`. Threshold becomes a tunable.

### Threshold options

| Threshold | sf2 cost | watchpost cost | Replay precision |
|---|---|---|---|
| Per-heartbeat (no coalescing) | 1500 events/run | 288K events/day | exact |
| 60 s | ≈1500 events/run | 144K events/day | within 60 s |
| 5 min | 300 events/run | 28.8K events/day | within 5 min |
| 1 h | 25 events/run | 2.4K events/day | within 1 h |
| `ttl/2` (whichever is shorter) | low | depends on ttl | within ttl/2 |

`ttl/2` (or any fraction-of-ttl) has a nice property: the replay never disagrees with the live value by more than `ttl/2`, which is exactly the precision needed for downstream consumers to make TTL-based decisions correctly. Below that, more precision is wasted; above that, the consumer might prematurely declare a claim expired.

## Recommendation

**Option 2 with `coalesce_threshold = max(60s, ttl/2)`.**

Rationale:

1. Replay precision is bounded to `ttl/2` — meaningful, not arbitrary.
2. sf2 cost stays ≤ ~1500 events/run worst case (5 min × 30 s heartbeats = 10 heartbeats, ttl/2 will coalesce most to 1–2 emissions per claim → ~300 events/run). Same as baseline event volume; 2× total. Acceptable.
3. Watchpost long-lived states emit at most one heartbeat event every ttl/2; with a typical 5 min ttl that's one heartbeat event every 2.5 min = 576/day per long-lived incident = ~57.6K events/day at 100 incidents. Still high, but 5× cheaper than per-heartbeat. Borderline acceptable, manageable with retention policy.
4. The threshold is part of the public `heartbeat_claim` API, so consumers can override it (`coalesce_threshold=3600` for watchpost-style use cases).
5. Replay derivation: on each `claim_heartbeat` event, update `derived_claim_expires_at`. The drift comparison BC-189 reverted can be re-enabled — but with the relaxed predicate `abs(derived - live) <= coalesce_threshold`, since the live value can be up to `coalesce_threshold` ahead of the last event.

## What to file

If you accept this recommendation, BC-194 becomes implementable:

1. Add `coalesce_threshold: float | None = None` to `heartbeat_claim` signature (None → use `max(60.0, ttl_seconds/2)`).
2. Track `last_emitted_expires_at` on the `claims` row (new column: `last_emitted_expires_at TIMESTAMPTZ`).
3. In `heartbeat_claim`, append a `claim_heartbeat` event only when `new_expires_at - last_emitted_expires_at >= threshold`; update column either way.
4. Replay derivation updates `derived_claim_expires_at` from `claim_heartbeat` payload (`{"expires_at": ...}`).
5. Re-add `claim_expires_at` to `_states_match` / `_diff_fields` with the relaxed predicate `abs(...) <= threshold + epsilon` to account for between-heartbeat drift.

## If you'd rather defer

The honest alternative is "do nothing for now." Cost: BC-189's `claim_expires_at` comparison stays out of replay drift detection; the field stays live-only; consumers that need to reconstruct claim TTL from events cannot. Acceptable while no consumer is actually heartbeating, painful the moment one starts.

## Decision needed

A) Implement Option 2 with `max(60s, ttl/2)` default coalescing.
B) Implement Option 1 (per-heartbeat, no coalescing) and let consumers eat the cost.
C) Defer until a consumer actually adopts heartbeats.

**My pick: A.** Sets the contract now while it's free; encodes the coalescing default so a watchpost-style consumer doesn't immediately hit a wall.
