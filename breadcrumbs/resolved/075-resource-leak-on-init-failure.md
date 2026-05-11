---
number: "075"
title: "create_project and __init__ leak connection pool on failure"
severity: high
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`__init__.py:165-169` — If `run_migrations` raises, `mgr.close()` is never
called. Same at lines 119-138 — if `check_integrity` raises, the pool on
`self._mgr` is leaked (caller has no `Substrate` to call `close()` on).

## Fix

Wrap in try/finally: `create_project` wraps mgr ops in try/finally. `__init__`
wraps post-open setup in try/except that closes mgr on failure.
