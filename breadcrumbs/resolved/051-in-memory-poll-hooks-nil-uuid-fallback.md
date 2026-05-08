---
number: "051"
title: InMemorySubstrate poll_hooks fabricates nil UUID for missing work_item_id
severity: low
status: implemented
kind: bug
author: assistant
date: "2026-05-07"
tags: [in-memory, hooks, test-fidelity]
related: ["048", "050", "052"]
---

## Resolution

`InMemorySubstrate.poll_hooks` now checks for missing `work_item_id` before building `HookContext`. If absent, it calls the same `_move_to_dead_letter` helper with error "work_item_id missing from payload", matching real backend behavior. The nil UUID fallback (`uuid.UUID(int=0)`) was removed.
