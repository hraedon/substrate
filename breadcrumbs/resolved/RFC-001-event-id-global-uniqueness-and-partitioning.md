---
number: "RFC-001"
title: "Reconcile event_id global-uniqueness spec with the partitioned events table"
severity: high
status: proposed
kind: design
author: claude
date: "2026-05-18"
tags: [events, partitioning, spec-drift, idempotency, BC-148, migration-010]
related: ["148", "190", "193"]
---

# RFC-001 — Event ID uniqueness vs. partitioning

## Motivation

`spec.md:93` (BR-12) states: "`event_id` ... Unique within a project DB." Migration 010 (`migrations/010_events_partition.sql:28-29`) partitions `events` by `timestamp` with primary key `(event_id, timestamp)` and unique constraint `(work_item_id, event_seq, timestamp)`. There is **no global unique index on `event_id`**.

BC-148 attempted to close this by adding `pg_advisory_xact_lock(_advisory_lock_id(event_id))` in `_events.append_event` and `check_idempotency` paths (`src/substrate/_events.py:142, 266`). That serializes concurrent inserts but does not enforce uniqueness. It also produces a misleading error code: after a cross-work-item collision, `check_idempotency` finds the existing row (`src/substrate/_events.py:74-80`) and `_contract.check_idempotency` (`src/substrate/_contract.py:168-173`) raises `IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD` — but the collision is structural, not a payload mismatch.

Either the spec is wrong or the implementation is. Both being live in main is the worst state.

## Options

### Option A — Make the implementation match the spec (true global uniqueness)

Add a lookup table `event_ids(event_id UUID PRIMARY KEY, work_item_id UUID, inserted_at TIMESTAMPTZ)`. Inside the same transaction as `append_event`, `INSERT INTO event_ids ... ON CONFLICT DO NOTHING RETURNING event_id`. If RETURNING is empty, the event_id was already used — reject with a proper `EVENT_ID_GLOBAL_COLLISION` error.

- **Pros:** restores the spec contract; idempotency error semantics become accurate; advisory-lock dance can be deleted.
- **Cons:** extra index/row per event; the lookup table itself isn't partitioned, so it grows monotonically. Retention/pruning policy needed (probably aligned with partition drop).

### Option B — Amend the spec to per-work-item uniqueness

Change BR-12 to "`event_id` is unique within a (work_item_id, event_seq) tuple — see the existing unique constraint." Re-document `check_idempotency` and external API to take `(work_item_id, event_id)` rather than `event_id` alone. Remove the advisory-lock workaround.

- **Pros:** minimal code change; honest about what the table actually enforces.
- **Cons:** every external caller that holds an `event_id` and wants to look it up now needs the work_item_id too. Migration churn for consumers (sf2, watchpost-style new consumers).

### Option C — Drop migration 010 partitioning

Revert to non-partitioned `events`. Restore global unique index on `event_id`. Revisit partitioning when actually needed (10M+ events/month at a real consumer).

- **Pros:** simplest; restores all the other invariants the partitioned scheme weakened (BC-190 partition maintenance, BC-193 read pruning hack).
- **Cons:** sacrifices the future scaling story; possibly painful to re-introduce later.

## Recommendation

**Option C if no consumer is at scale today; Option A otherwise.** Option B is the cheapest but encodes a spec retreat that will surprise every future consumer reading `spec.md` first.

Open questions for the principal:

1. Is sf2 (or any in-flight consumer) actually producing events at a rate where partitioning pays for itself?
2. If yes, is the long-term operational story (BC-190 partition lifecycle, BC-193 read semantics, plus this RFC's uniqueness story) acceptable?
3. If no, is reverting migration 010 acceptable, including the migration-down work?

## Decision

_(pending)_
