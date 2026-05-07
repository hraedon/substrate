---
number: "052"
title: InMemorySubstrate _hook_queue grows unboundedly
severity: low
status: proposed
kind: improvement
author: assistant
date: "2026-05-07"
tags: [in-memory, hooks, memory]
related: ["048"]
---

## Observation

After BC-048 added status tracking, `poll_hooks` marks entries as `completed` or `dead_lettered` in-place. However, the `_hook_queue` list is never pruned — completed and dead-lettered entries accumulate forever. In long-running tests or benchmarks, this causes unbounded memory growth.

The real backend uses separate tables (`hook_queue` vs `hook_dead_letter`) and dead-lettered entries are moved (DELETE + INSERT). Completed entries remain in `hook_queue` but are excluded by the `WHERE status = 'pending'` filter. The in-memory backend lacks any equivalent cleanup.

## Proposed

Either prune `completed` and `dead_lettered` entries from `_hook_queue` after processing, or periodically compact the list. A simple approach: after each `poll_hooks` call, remove entries with terminal statuses.
