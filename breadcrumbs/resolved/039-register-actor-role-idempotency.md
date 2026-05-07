---
number: "039"
title: register_actor_role should be idempotent by default
severity: low
status: implemented
kind: improvement
author: claude-opus-4-7
date: "2026-05-07"
tags: [api-ergonomics, idempotency, sf2-phase2]
---

## Observation

`register_actor_role` raises if the role is already registered. Software-factory-2 wraps every call in try/except (Session 4 bug fix in `runner.py`) because runner restarts naturally re-enter the registration code path. Every consumer that wants restart-safe startup will hit this and patch around it the same way.

## Proposed

Make `register_actor_role` idempotent by default — repeated calls with the same role definition are no-ops. Add `strict=True` for the rare caller that wants the existing error semantics.

Alternative (smaller change): add `idempotent=True` flag that callers opt into.

## Why low severity

Workaround is one-line try/except. But it's a foot-gun every consumer hits, and the canonical pattern (a runner that restarts) makes the strict-by-default behavior actively hostile.
