---
number: "049"
title: check_actor_role_authorized silently allows actors with zero registered roles
severity: low
status: proposed
kind: design
author: glm-5.1
date: "2026-05-07"
tags: [rbac, fr-24]
related: []
---

## Observation

`check_actor_role_authorized` at `_actor_roles.py:81-82` returns without raising if the actor has no entries in `actor_roles`. This means an actor who was never registered for any role can pass the role check. This is by design per FR-24 (enforcement only applies to actors with at least one registered role), but could be surprising to consumers who expect the check to be authoritative.

## Proposed

Document this behavior explicitly in the method's docstring and/or the spec. Consider adding an optional `strict=True` mode that rejects actors with zero registered roles.
