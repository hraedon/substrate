---
number: "068"
title: validate_field_values takes WorkflowDefinition but validate_field_update takes raw dict
severity: low
status: deferred
kind: improvement
author: deepseek-v4-pro
date: "2026-05-11"
tags: [workflow, design, consistency]
related: []
---

## Context

`_workflow.py:226` (`validate_field_values`) takes a typed `WorkflowDefinition`
and uses structured attribute access. `_workflow.py:265` (`validate_field_update`)
takes a raw `dict`, requiring `wf_def.get("work_item_types", [])` access.

This is because `validate_field_update` is called from `__init__.py:603` where
only the raw `definition` dict is available (fetched from `workflow_registry`
by `_load_workflow_definition` at `_work_items.py:87`, which returns the raw dict).

## Options

- Have `_load_workflow_definition` return a typed `WorkflowDefinition` (via
  `_rebuild_wf()`) instead of the raw dict
- Accept the inconsistency as pragmatic — the raw dict path avoids the
  `_rebuild_wf` allocation in the hot transition path
