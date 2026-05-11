---
number: "076"
title: "JSON-typed custom fields bypass validate_json_safe_value"
severity: high
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_workflow.py:385-391` — The `"json"` branch checks isinstance but never calls
`validate_json_safe_value`. Compare with the `"string"` branch at line 356-363
which does. A JSON field containing `\\u0000` or surrogates passes validation
but crashes at Postgres JSONB storage.

## Fix

Add `validate_json_safe_value(value, ...)` call in the json branch.
