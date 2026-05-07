---
number: "051"
title: InMemorySubstrate poll_hooks fabricates nil UUID for missing work_item_id
severity: low
status: proposed
kind: bug
author: assistant
date: "2026-05-07"
tags: [in-memory, hooks, test-fidelity]
related: ["050"]
---

## Observation

The real backend's `poll_and_process_hooks` dead-letters hooks with missing `work_item_id` (`_hooks.py:124-129`). BC-046 fixed this for the real backend. However, InMemorySubstrate's `poll_hooks` still uses `entry.get("work_item_id", uuid.UUID(int=0))`, fabricating a nil UUID rather than dead-lettering.

This creates a test fidelity gap: a bug where `work_item_id` is missing from a hook payload would pass in-memory tests but fail against real Postgres.

## Proposed

Check for missing `work_item_id` before building `HookContext`. If missing, dead-letter the entry and emit `hook_dead_lettered`, matching the real backend.
