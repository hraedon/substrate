---
number: "101"
title: actor_metadata role claim is self-attested without independent verification
severity: critical
status: accepted
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, auth, fr-12, fr-24, br-09]
related: ["100", "102"]
resolution_date: "2026-05-11"
---

## Resolution

Accepted — by design per BR-09 and trust tier definitions. The spec explicitly classifies actor_metadata as "actor-claimed" (signed by actor, not validated against a registry). FR-24 enforcement checks registered roles, not external authority. Operators control who can register roles. This is a trust delegation, not a bug.
