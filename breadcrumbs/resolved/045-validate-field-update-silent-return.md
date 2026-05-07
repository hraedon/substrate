---
number: "045"
title: validate_field_update silently returns on unknown work_item_type
severity: medium
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-07"
tags: [workflow, validation]
related: []
---

## Problem

`validate_field_update` in `_workflow.py` returned silently when the `work_item_type` was not found in the workflow definition. This meant invalid `custom_fields_update` values would pass validation without any checks. `validate_field_values` correctly raises `WORK_ITEM_TYPE_NOT_DECLARED` for the same case.

## Resolution

Changed `validate_field_update` to raise `WORK_ITEM_TYPE_NOT_DECLARED` when the type is not found, matching `validate_field_values` behavior. Test in `tests/test_session13_regression.py::TestValidateFieldUpdateRejectsUnknownType`.
