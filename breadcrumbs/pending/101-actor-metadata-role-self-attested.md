---
number: "101"
title: actor_metadata role claim is self-attested without independent verification
severity: critical
status: proposed
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, auth, fr-12, fr-24, br-09]
related: ["100", "102"]
---

## Description

The spec explicitly classifies `actor_metadata` as "actor-claimed" (signed by actor but not validated against any registry). The `role` field within `actor_metadata` is used for transition role-gating (FR-12) and FR-24 enforcement.

However, `check_actor_role_authorized` in `_actor_roles.py:71-83` only checks that the *claimed* role is in the actor's registered set. It does not verify that the actor is actually authorized to claim that role by any out-of-band mechanism.

An actor can:
1. Call `register_actor_role(actor_id, "admin")` for themselves
2. Set `actor_metadata: {"role": "admin"}` on any event
3. Pass FR-24 enforcement (the claimed role IS in the registered set)

The substrate provides a signed audit trail of role claims but does not verify the legitimacy of those claims.

## Evidence

- `_actor_roles.py:76-82`: Queries `actor_roles` table, gets registered roles as a set, then calls `_check_roles(registered, actor_id, claimed_role)` which only checks membership
- `_contract.py:76-89`: `check_role_gating` reads `role` from `(actor_metadata or {}).get("role")` — unvalidated input
- Spec BR-09: "Authorization is enforced when actor roles are registered; audit-only when not"

## Impact

- If actors can register their own roles (via `register_actor_role`), they can escalate to any role defined in the workflow
- The FR-24 enforcement is only as strong as the registration process for `actor_roles`
- A compromised actor can claim any role and the system will enforce it against their registered set

## Fix

1. Require an external authority (admin API, OIDC claims, separate role approval workflow) to populate `actor_roles` — actors cannot register themselves
2. Separate the concept of "role registration" (admin-controlled) from "role claim" (actor-attested, used for audit)
3. Document the trust model clearly: actors who can register their own roles effectively own the authorization system

## Notes

This is acknowledged in spec BR-09 and the trust tier definition — but the implications may not be obvious to operators. The current design is intentional per the spec, but it's a significant trust assumption.