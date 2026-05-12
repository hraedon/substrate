---
number: "131"
title: InMemory sweep_expired_claims unconditionally clears claimed_by without steal detection
severity: high
status: resolved
kind: bug
author: claude-opus
date: "2026-05-12"
resolved_date: "2026-05-12"
tags: [in-memory, claims, conformance]
related: ["114"]
---

## Problem

`InMemorySubstrate.sweep_expired_claims` deletes expired claims from `self._claims`, then unconditionally sets `wi["claimed_by"] = None` and `wi["claim_expires_at"] = None`. In Postgres, the sweep uses a guarded `UPDATE ... WHERE claimed_by = %s` — if a claim was stolen between the DELETE and the UPDATE, the UPDATE affects zero rows and the projection correctly keeps the new claim owner.

The InMemory version has no such guard. If a new claim was acquired between the expired-claim scan and the dict mutation, the new owner's claim is silently overwritten to `None` with no event recorded.

## Resolution

Already fixed by BC-114 in Session 24. The InMemory sweep now checks `wi.get("claimed_by") == claim["actor_id"]` and `wi.get("claim_expires_at") == claim["expires_at"]` before clearing, matching the Postgres `WHERE claimed_by = %s` guard. This breadcrumb was filed before the fix was applied. Renumbered from BC-128 to BC-131 to resolve conflict with EventStore protocol BC-128.
