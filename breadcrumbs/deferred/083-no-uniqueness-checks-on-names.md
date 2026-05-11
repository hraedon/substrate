---
number: "083"
title: "No uniqueness checks on state/transition/type names"
severity: medium
status: deferred
kind: improvement
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_workflow.py:63-152` — Duplicate names silently deduplicated via dict/set
construction. Two transitions named "approve" from the same state: only the
first is reachable. No error at registration.

## Options

- Add uniqueness checks in `_validate_semantics`
- Accept as documented limitation
