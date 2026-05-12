---
number: "126"
title: Dead-letter requeue loses original max_retries
severity: medium
status: implemented
kind: bug
author: adversarial-review
---

## Problem

The `hook_dead_letter` table has no `max_retries` column. When `requeue_dead_lettered_hook` inserts back into `hook_queue`, it hardcodes `max_retries=3`, ignoring whatever the workflow `hook_defaults` or original queue entry declared.

## Impact

Requeued hooks may retry more or fewer times than intended. A workflow that sets `max_retries: 5` will have its requeued hooks capped at 3, reducing resilience. Conversely, a workflow that sets `max_retries: 1` will have its requeued hooks retried up to 3 times, potentially causing unwanted side effects.

## Fix

Add `max_retries` to `hook_dead_letter` table and propagate it on requeue. Alternatively, store the original `max_retries` in the `payload` JSONB.

## Related

- `_hooks.py` `requeue_dead_lettered_hook`
- `_hooks.py` `_move_to_dead_letter`
- Migration `007_hook_queue.sql` or equivalent
