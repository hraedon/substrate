---
number: "068"
title: "validate_field_values takes WorkflowDefinition but validate_field_update takes raw dict"
severity: low
status: accepted
kind: improvement
author: deepseek-v4-pro
date: "2026-05-11"
tags: [workflow, design, consistency]
related: []
resolution_date: "2026-05-11"
---

## Resolution

Accepted — pragmatic inconsistency. `validate_field_update` is on the hot transition path where the raw dict is already available from the registry. Converting to a typed `WorkflowDefinition` via `_rebuild_wf()` would add allocation overhead per transition for no functional benefit. Both paths perform the same validation; the type difference is cosmetic.
