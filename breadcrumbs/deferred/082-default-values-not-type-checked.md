---
number: "082"
title: "Default values not type-checked at workflow registration"
severity: medium
status: deferred
kind: improvement
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_workflow.py:179` — Defaults are stored without calling `_coerce_field`. A
workflow with `type: integer, default: "high"` registers fine, then every work
item creation fails with CUSTOM_FIELD_VIOLATION.

## Options

- Validate defaults in `_validate_semantics` by calling `_coerce_field`
- Accept as late-validation (error still surfaces, just at creation time)
