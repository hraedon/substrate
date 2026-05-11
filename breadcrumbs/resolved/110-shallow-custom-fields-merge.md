---
number: "110"
title: custom_fields merge in append_transition_event is shallow, not deep
severity: medium
status: accepted
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [correctness, custom-fields, fr-27]
resolution_date: "2026-05-11"
---

## Resolution

Accepted — shallow merge by design. Deep merge introduces ambiguous semantics (how to merge lists? type conflicts? partial nested updates?). Shallow merge is simple, predictable, and consumers can include full nested structures in updates if needed. This is the standard approach for key-value field stores.
