---
number: "088"
title: Async hook queue poll lacks row locking — concurrent consumers double-process hooks
severity: critical
status: open
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [hooks, concurrency, correctness, at-least-once]
related: [047]
---

## Observation

`poll_and_process_hooks` at `_hooks.py:109-116` fetches pending hook_queue rows with:

```sql
SELECT id, event_id, hook_name, payload, retry_count, max_retries
FROM hook_queue
WHERE status = 'pending'
  AND (next_retry_at IS NULL OR next_retry_at <= now())
ORDER BY id LIMIT 100
```

There is no `FOR UPDATE SKIP LOCKED`. If two consumers (threads, processes, or separate `Substrate` instances) poll concurrently, they read the same rows, both set `status = 'in_progress'`, and both execute the handler. The nested savepoint prevents DB corruption, but external side effects execute twice, violating at-least-once semantics.

Breadcrumb 047 documents double-processing for *stuck-hook recovery* only; the race exists for normal concurrent dispatch too.

## Impact

Duplicate webhooks, duplicate downstream writes, duplicate billing, or state corruption in consumer systems.

## Proposed Fix

Add `FOR UPDATE SKIP LOCKED` to the SELECT. Alternatively, use a per-hook-queue-ID advisory lock.

## Acceptance Criteria

- [ ] Concurrent `poll_hooks()` calls never process the same hook_queue row.
- [ ] Regression test demonstrates the fix under thread contention.
- [ ] In-memory backend parity: same serialization behavior.
