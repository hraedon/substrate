---
number: "082"
title: "Default values not type-checked at workflow registration"
severity: medium
status: accepted
kind: improvement
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
resolution_date: "2026-05-11"
---

## Resolution

Accepted — late validation is sufficient. A mismatched default surfaces as `CUSTOM_FIELD_VIOLATION` at work item creation time, which is the correct enforcement point. Adding validation at registration would require duplicating the coercion logic or restructuring the validation pipeline for marginal benefit.
