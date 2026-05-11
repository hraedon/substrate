---
number: "081"
title: "check_idempotency actor_id type annotation is wrong"
severity: medium
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_contract.py:109` — Typed as `str` but `_events.py:61` passes `str | None`.
Line 114 guards `if actor_id is not None`, confirming the function handles None.

## Fix

Change annotation to `actor_id: str | None`.
