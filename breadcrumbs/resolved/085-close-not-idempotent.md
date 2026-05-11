---
number: "085"
title: "close() is not idempotent"
severity: medium
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`__init__.py:180-185` — Second call hits `self._mgr.close()` on an already-closed
pool. The hook consumer has a guard but the pool does not.

## Fix

Add `_closed` flag or check `self._mgr` before closing.
