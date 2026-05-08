---
number: "052"
title: InMemorySubstrate _hook_queue grows unboundedly
severity: low
status: implemented
kind: improvement
author: assistant
date: "2026-05-07"
tags: [in-memory, hooks, memory]
related: ["048", "050", "051"]
---

## Resolution

After `poll_hooks` finishes processing the pending batch, it prunes `_hook_queue` in-place to retain only entries whose status is not `completed` or `dead_lettered`. This prevents unbounded memory growth in long-running tests or benchmarks, analogous to the real backend's `WHERE status = 'pending'` filter.
