---
number: "123"
title: Workflow semantics do not reject duplicate transition/state/type names
severity: high
status: implemented
kind: bug
author: adversarial-review
---

## Problem

States, transitions, work-item types, custom fields, and link types are collected into dicts/sets that silently deduplicate duplicates. A workflow with two transitions named `approve` from the same state will validate, but `resolve_transition` will match the first one arbitrarily.

## Impact

Silent load-bearing behavior divergence between registration-time validation and runtime resolution. The workflow YAML is accepted but its runtime behavior is ambiguous and dependent on dict insertion order. This is a spec violation: workflows should have deterministic, unambiguous semantics.

## Fix

Add explicit duplicate-name checks during `_validate_semantics` and raise `WORKFLOW_SEMANTIC_ERROR` for any duplicate names within a category.

## Related

- `_workflow.py` `_validate_semantics`
- `_workflow.py` `resolve_transition`
