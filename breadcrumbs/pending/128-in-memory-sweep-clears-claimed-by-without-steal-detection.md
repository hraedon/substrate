---
number: "128"
title: InMemory sweep_expired_claims unconditionally clears claimed_by without steal detection
severity: high
status: proposed
kind: bug
author: claude-opus
date: "2026-05-12"
tags: [in-memory, claims, conformance]
related: ["114"]
---

## Problem

`InMemorySubstrate.sweep_expired_claims` (`_in_memory.py:857-874`) deletes expired claims from `self._claims`, then unconditionally sets `wi["claimed_by"] = None` and `wi["claim_expires_at"] = None`. In Postgres, the sweep uses a guarded `UPDATE ... WHERE claimed_by = %s` — if a claim was stolen between the DELETE and the UPDATE, the UPDATE affects zero rows and the projection correctly keeps the new claim owner.

The InMemory version has no such guard. If a new claim was acquired between the expired-claim scan and the dict mutation, the new owner's claim is silently overwritten to `None` with no event recorded. This is a distinct failure mode from BC-114 (which is about spurious events in Postgres); here, InMemory loses claim state entirely.

## Impact

InMemory tests exercising claim expiry + steal sequences can silently corrupt projection state. The property-based conformance tests don't exercise sweep timing, so this gap isn't caught.

## Fix

After deleting the expired claim, re-check `wi["claimed_by"]` before clearing it. Only clear and emit `claim_expired` if the work item is still claimed by the expired actor.