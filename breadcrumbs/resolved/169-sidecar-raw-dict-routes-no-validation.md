---
number: "169"
title: "Sidecar `fire_recurrence`/`cancel_recurrence_rule`/`requeue_dead_lettered_hook` use raw `dict` body — no input validation"
severity: high
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-16"
tags: [sidecar, plan-005, validation]
related: ["161"]
---

## Problem

Three sidecar routes used `body: dict` instead of typed Pydantic models, producing unhandled `KeyError`/`ValueError` (500) on malformed input instead of clean 422 validation errors.

- `requeue_dead_lettered_hook` — `body["dead_letter_id"]` / `int(...)`
- `fire_recurrence` — `body["rule_id"]`
- `cancel_recurrence_rule` — `body["rule_id"]`

## Fix

Created typed Pydantic models (`FireRecurrenceRequest`, `RequeueDeadLetteredHookRequest`) and added `rule_id` to `CancelRecurrenceRuleRequest`. Updated all three routes to use the models.
