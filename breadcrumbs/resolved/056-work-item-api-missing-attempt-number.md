---
number: "056"
title: WorkItem dataclass excludes attempt_number despite query fetching it
severity: low
status: implemented
kind: bug
author: adversarial-reviewer
date: "2026-05-08"
tags: [fr-07, fr-05b, api-ergonomics, consumer]
---

## Resolution

Added `attempt_number: int = 0` field to the `WorkItem` frozen dataclass, wired through `_row_to_work_item` (Postgres) and `_wi_to_work_item` (InMemory). Also updated `to_dict` and `from_dict` methods for round-trip serialization. Backward-compatible additive change — consumers that don't use the field are unaffected.