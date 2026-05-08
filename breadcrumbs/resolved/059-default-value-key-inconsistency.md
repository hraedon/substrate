---
number: "059"
title: validate_field_update uses "default_value" while YAML/schema uses "default"
severity: low
status: implemented
kind: improvement
author: adversarial-reviewer
date: "2026-05-08"
tags: [fr-27, fr-17, custom-fields, schema]
---

## Resolution

Made `validate_field_update`, `_rebuild_wf`, and `CustomFieldDef.from_dict` accept both `"default_value"` and `"default"` keys by falling back with `field_def.get("default_value", field_def.get("default"))`. The canonical storage key remains `"default_value"` (matching the dataclass attribute and `to_dict()` serialization), but both YAML-origin (`"default"`) and DB-origin (`"default_value"`) dicts are now handled correctly.