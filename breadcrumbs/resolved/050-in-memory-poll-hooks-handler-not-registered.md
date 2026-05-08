---
number: "050"
title: InMemorySubstrate poll_hooks does not dead-letter unregistered handlers
severity: low
status: implemented
kind: bug
author: assistant
date: "2026-05-07"
tags: [in-memory, hooks, test-fidelity]
related: ["048", "051", "052"]
---

## Resolution

`_in_memory.py` now dead-letters entries whose `hook_name` has no registered handler. A `_move_to_dead_letter` helper centralizes the logic: marks status `dead_lettered`, adds to `_dead_letter` dict, and emits `hook_dead_lettered` event (with nil UUID guard matching BC-051). The real backend already did this in `poll_and_process_hooks`.
