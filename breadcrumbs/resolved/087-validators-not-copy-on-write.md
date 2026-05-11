---
number: "087"
title: "_validators dict not copy-on-write (thread safety)"
severity: medium
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`__init__.py:125,224` — `register_validator` mutates `self._validators` directly.
`register_hook_handler` (line 233) uses copy-on-write. Inconsistent thread
safety between the two registration methods.

## Fix

Use copy-on-write pattern for `_validators`, matching `_hook_handlers`.
