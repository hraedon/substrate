---
number: "166"
title: "Recurrence `count_remaining` exhaustion sets `None` instead of stopping — rules fire forever"
severity: critical
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-16"
tags: [recurrence, plan-003, correctness]
related: []
---

## Problem

In `_recurrence.py:fire_recurrence` and `_in_memory.py`, when `count_remaining` reaches 0 after decrement, it was set to `None`. The downstream check `if new_count is not None and new_count <= 0` could never fire, so `new_status` was always `"active"`. The `NULL` stored in the DB for `count_remaining` is interpreted as "no limit" on subsequent fires.

Any recurrence rule with a finite `count` would fire once more than intended, then continue firing indefinitely.

## Fix

Reordered the exhaustion check to test `new_count <= 0` before setting it to `None`. When count reaches 0, the rule is immediately marked `"exhausted"`. Fixed in both Postgres (`_recurrence.py`) and InMemory (`_in_memory.py`) backends.
