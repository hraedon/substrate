---
number: "107"
title: validate_work_item_refs propagates unhandled ValueError from uuid.UUID()
severity: medium
status: implemented
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [correctness, custom-fields, fr-27]
resolution_date: "2026-05-11"
---

## Resolution

Fixed. Wrapped `uuid.UUID(value)` in try/except ValueError in `validate_work_item_refs` (`_workflow.py:325`), raising `SubstrateError(CUSTOM_FIELD_VIOLATION)` with field name and value detail. Now consistent with `_coerce_field` which already handled this correctly.
