---
number: "083"
title: "No uniqueness checks on state/transition/type names"
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

Accepted — duplicate names are silently deduplicated via dict/set construction. The first definition wins, which is deterministic. Adding uniqueness checks at registration is a nice-to-have but the behavior is correct and predictable. Error surfaces at runtime if a consumer relies on a shadowed name.
