---
number: "134"
title: Postgres event INSERT can raise raw UniqueViolation on concurrent event_id collision
severity: medium
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-12"
resolved_date: "2026-05-12"
tags: [postgres, idempotency]
related: ["004"]
---

## Problem

`_events.py` `append_event()` and `append_transition_event()` check idempotency via `check_idempotency()` before INSERT. However, two concurrent transactions on different work items could both pass the idempotency check (neither finds the event yet) and both attempt INSERT. The second commits with a raw `psycopg.errors.UniqueViolation` instead of a clean `SubstrateError(IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD)`.

## Resolution

Wrapped both INSERT statements in try/except `psycopg.errors.UniqueViolation`, converting to `SubstrateError(IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD)`.
