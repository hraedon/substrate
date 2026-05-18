---
number: "193"
title: "read_events_by_work_item uses last_event_at as a partition-pruning hack — undocumented semantics, NULL fallback scans all partitions"
severity: medium
status: proposed
kind: bug
author: claude
date: "2026-05-18"
tags: [reads, partitions, semantics, performance]
related: ["190"]
---

# BC-193 — `read_events_by_work_item` partition-pruning is silent and degrades on NULL

## Problem

`src/substrate/_events.py:362-414` reads `last_event_at` for the work item, then queries events with `WHERE timestamp <= %s` using that ceiling. The clear (but undocumented) intent is partition pruning. Two issues:

1. **Hidden semantics.** Without the comment, a maintainer reasonably assumes the read is current. In fact the result is consistent with `last_event_at` at the moment of the read, not the moment of the surrounding transaction. A consumer that interleaves append and read in one transaction will not see its own writes via `read_events_by_work_item` until `last_event_at` is updated — which happens in the same `append_event` tx, so usually OK, but the ordering is non-obvious.
2. **NULL fallback.** A newly-created work item with no transitions has `last_event_at = NULL`. The `timestamp <=` filter is dropped (or set to a sentinel), and the query degrades to a full-partition scan — including `events_default`. Combined with BC-190 (spill into `events_default` when partitions aren't maintained), this is a worst-case path.

## Proposed fix

1. Document the partition-pruning intent inline (block comment in `_events.py` next to the SELECT).
2. Seed `last_event_at` at work-item creation (e.g., to `now()` at insert) so the ceiling is always present; or branch the query to skip the SELECT entirely when `last_event_at IS NULL` (faster than scanning all partitions).
3. Decide and document the read-consistency contract: "snapshot at the moment of the work-item read" vs "transaction-current" — and write a test that nails down the chosen semantics.

## Acceptance criteria

1. Code comment on the SELECT explains the partition-pruning intent and the consistency model.
2. Newly-created work items do not trigger an all-partition scan on `read_events_by_work_item`.
3. Test asserts the chosen consistency model under interleaved append/read.

## Resolution

_(pending)_
