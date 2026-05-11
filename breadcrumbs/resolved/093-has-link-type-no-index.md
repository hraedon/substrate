---
number: "093"
title: query_work_items has_link_type filter performs correlated sequential scan without index
severity: high
status: open
kind: performance
author: adversarial-reviewer
date: "2026-05-11"
tags: [query, links, performance, index]
related: []
---

## Observation

The `has_link_type` predicate in `query_work_items` is a correlated subquery against `events` with JSONB path operators:

```sql
EXISTS (SELECT 1 FROM events e_c
WHERE e_c.work_item_id = work_items_current.work_item_id
  AND e_c.transition = 'link_created'
  AND e_c.payload->>'link_type' = %s
  AND NOT EXISTS (...))
```

There is no GIN index on `events(payload)` or partial index on link transitions. For every row in `work_items_current`, Postgres must scan `events`.

## Impact

O(n·m) query time. Degrades badly as events table grows.

## Proposed Fix

Add a GIN index on `events(payload)` or a partial composite index:
```sql
CREATE INDEX idx_events_link_type ON events (work_item_id, (payload->>'link_type'))
WHERE transition IN ('link_created', 'link_removed');
```

## Acceptance Criteria

- [ ] Migration adds the index.
- [ ] `EXPLAIN` shows index usage for `has_link_type` queries.
- [ ] Scale benchmark confirms improvement.
