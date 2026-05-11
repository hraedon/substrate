---
number: "111"
title: JSON Schema permits additionalProperties:true everywhere — workflow isolation unclear
severity: medium
status: rejected
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, workflow, fr-17]
resolution_date: "2026-05-11"
---

## Resolution

Rejected — false alarm. `_workflow_schema.json` already has `additionalProperties: false` at every level: root (line 14), states items (line 49), transitions items (line 75), roles items (line 116), work_item_types items (line 133), custom_fields items (line 147), link_types items (line 218). The schema is well-constrained. No extra fields are permitted anywhere.
