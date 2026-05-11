---
number: "094"
title: Hook queue table lacks a composite index for the polling query
severity: high
status: open
kind: performance
author: adversarial-reviewer
date: "2026-05-11"
tags: [hooks, performance, index, migration]
related: [088]
---

## Observation

`poll_and_process_hooks` filters on `(status = 'pending' AND (next_retry_at IS NULL OR next_retry_at <= now()))` and orders by `id`. Without a composite index on `(status, next_retry_at, id)`, the planner will seq-scan `hook_queue` as it grows.

## Impact

Hook polling latency increases linearly with queue depth. At high throughput, poll intervals exceed 30s and hooks become effectively undelivered.

## Proposed Fix

Add a partial composite index:
```sql
CREATE INDEX idx_hook_queue_poll ON hook_queue (status, next_retry_at, id)
WHERE status = 'pending';
```

## Acceptance Criteria

- [ ] Migration adds the index.
- [ ] `EXPLAIN` shows index usage for the poll SELECT.
- [ ] Scale benchmark confirms improvement.
