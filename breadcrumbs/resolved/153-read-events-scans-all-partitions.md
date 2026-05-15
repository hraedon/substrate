---
number: "153"
title: "read_events_by_work_item scans all partitions because timestamp partition key is unbounded"
severity: high
status: implemented
resolution: "Added `timestamp <= last_event_at` upper bound to `read_events_by_work_item` queries using `work_items_current.last_event_at`, enabling Postgres to prune future partitions."
kind: performance
author: agent
date: "2026-05-15"
tags: [events, partition, performance, fr-05]
related: ["148", "145"]
---

## Problem

The `events` table is partitioned by `timestamp` range. Queries in `read_events_by_work_item`:

```sql
SELECT ... FROM events WHERE work_item_id = %s ORDER BY event_seq
```

do not filter on `timestamp`. Postgres cannot prune partitions because `work_item_id` is
not the partition key. Every query must scan all partitions. Over time, as months accumulate,
every event read for a work item pays the cost of all partitions.

The spec FR-05 requires efficient event reads. At the stated homelab scale this may be
acceptable, but at the 1M-event trigger threshold mentioned in the spec, per-read partition
scanning becomes a serious latency regression.

## Impact

Event-read latency grows linearly with the number of historical partitions, even for work
items with only a few events. Replay and `read_events` become increasingly expensive over
time.

## Files / Lines

- `src/substrate/_events.py` (~335-371)
- `migrations/010_events_partition.sql`

## Fix

Add a `timestamp` lower bound to event-read queries using `work_items_current.last_event_at`
or `created_at`, or introduce `read_events_since(work_item_id, since)` as the preferred API
for old work items. Alternatively, document that `read_events_by_work_item` is unbounded
and recommend partitioning-aware callers to use time-bounded reads.
