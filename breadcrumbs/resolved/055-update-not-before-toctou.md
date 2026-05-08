---
number: "055"
title: update_not_before projection mutation precedes idempotency check — TOCTOU projection corruption
severity: high
status: implemented
kind: bug
author: adversarial-reviewer
date: "2026-05-08"
tags: [fr-26, br-11, §18.3, idempotency, projection]
---

## Resolution

Moved the idempotency check (`check_idempotency`) before the projection mutation in both `Substrate.update_not_before` (Postgres) and `InMemorySubstrate.update_not_before`. If the `event_id` is already present, the early return now happens before any state is mutated, preserving projection/log consistency.

Both backends now check `event_id` against existing events first. Only after confirming the event is new do they proceed to update `not_before` on the work item and append the event.