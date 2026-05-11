---
number: "079"
title: "Replay skips work items with zero events silently"
severity: medium
status: deferred
kind: design
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_replay.py:86-87` — `if not events: continue`. A work item in
`work_items_current` with no events (worst corruption case) is silently skipped.
No drift report, no halted entry.

## Options

- Treat as halted with a specific error message
- Accept current behavior (replay only validates event-derived state)
