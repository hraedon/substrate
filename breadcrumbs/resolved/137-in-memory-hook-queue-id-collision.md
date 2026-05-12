---
number: "137"
title: InMemory hook_queue entry IDs can collide after poll_hooks cleanup
severity: medium
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-12"
resolved_date: "2026-05-12"
tags: [in-memory, hooks, conformance]
related: []
---

## Problem

Hook queue entry IDs were generated as `len(self._hook_queue) + 1`. After `poll_hooks()` removes completed/dead-lettered entries, the list shrinks and subsequent entries get IDs that collide with prior entries.

## Resolution

Replaced with a monotonically increasing counter `self._hook_id_counter` that never resets. Both hook creation in `transition()` and `requeue_dead_lettered_hook()` use this counter.
