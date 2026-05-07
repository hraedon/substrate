---
number: "037"
title: "work_item_ref fields accept any UUID — no existence or type enforcement at runtime"
severity: high
status: proposed
kind: bug
author: glm-5.1
date: "2026-05-07"
origin: software-factory-2 Phase 2 prerequisite verification
tags: [custom-fields, validation, sf2-phase2-blocker]
related: ["027"]
---

## Problem

`work_item_ref` custom fields with `target_work_item_type` constraints are validated at **workflow-registration time** only (the target type name must exist in the workflow's `work_item_types`). At **runtime**, `_coerce_field` (`_workflow.py:332-338`) only checks that the value is a UUID string. It does NOT verify:

1. The referenced work-item exists in the project.
2. The referenced work-item is of the declared `target_work_item_type`.

This means `test_suite_ref: <uuid-of-an-interface-spec>` passes validation silently. The existing SF2 roundtrip test (`test_sf2_workflows.py:173`) demonstrates exactly this — it sets `test_suite_ref` to an `interface_spec` work-item's ID and substrate accepts it.

## Why this blocks SF2 Phase 2

Phase 2's `phase2.yaml` declares `interface_ref` (target: `interface_spec`) and `test_suite_ref` (target: `test_suite`) as required fields on `test_suite` and `implementation` work-items. The runner's context derivation resolves these refs to load artifacts from disk. If a bad ref is accepted silently, the runner will:

- Fail with a confusing "artifact not found" error at invocation time, not at creation time.
- Or worse, load the wrong artifact and produce an incoherent result that passes gates.

The Phase 2 plan explicitly calls this out: "If substrate does not enforce that `target_work_item_type: interface_spec` references actually point at an `interface_spec` work-item, Wave 1 must add validators. Verify before Wave 1; file a substrate breadcrumb if missing."

## Proposed fix

Add runtime validation in `_coerce_field` for `work_item_ref` type:

1. Resolve the UUID to a work-item via the project DB.
2. If the work-item does not exist, raise `CUSTOM_FIELD_VIOLATION` with a clear message.
3. If the work-item exists but its `work_item_type` does not match the field's `target_work_item_type`, raise `CUSTOM_FIELD_VIOLATION`.

This requires passing the substrate manager/connection context into `_coerce_field`, which currently operates as a pure type-coercion function. Two approaches:

- **(a) Pass context down:** `_coerce_field` gains an optional `context` parameter with a DB connection + workflow definition. Minimal change; keeps validation at the same call sites.
- **(b) Post-hoist validator:** A separate `_validate_work_item_refs()` function called after `_coerce_field` in the creation and transition paths. Cleaner separation; easier to test.

Recommend (b) for testability. The validation function can be a sync validator registered per-workflow, but it's more naturally a built-in check since the field definition already carries the constraint.

## Acceptance criteria

- AC-1: Setting `interface_ref` to a nonexistent UUID raises `CUSTOM_FIELD_VIOLATION`.
- AC-2: Setting `interface_ref` to a UUID of a `test_suite` work-item (when the field declares `target_work_item_type: interface_spec`) raises `CUSTOM_FIELD_VIOLATION`.
- AC-3: Setting `interface_ref` to a valid UUID of the correct type succeeds (existing behavior preserved).
- AC-4: The `test_sf2_workflows.py:173` test is updated to use correct type references (or the `test_suite_ref` there is removed if it was just a placeholder).
- AC-5: Validation runs at both `create_work_item` and `transition(custom_fields_update=...)` time.
