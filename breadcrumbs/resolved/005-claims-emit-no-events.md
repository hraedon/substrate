---
number: "005"
title: Claim mutations do not emit events
severity: high
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [claims, fr-09b, event-log, audit]
---

## Problem

Claim acquisition, heartbeat, release, and auto-steal mutate the `claims` table and `work_items_current.claimed_by` but emit no events. FR-09b explicitly requires "preserve prior claim history in the event log" — currently when an expired claim is auto-stolen, the prior holder's `actor_id` is overwritten in the `claims` row and lost.

The work-item's event log shows transitions but no leasing history. Questions like "who held this work-item before me," "when did this claim expire," "how many times has this been stolen" cannot be answered from the substrate's authoritative source. The audit trail is incomplete on a load-bearing dimension.

## Spec reference

- FR-09b ("Auto-steal expired claims on next acquire; increment `attempt_number`; preserve prior claim history in the event log")
- §17.7 race interaction matrix (assumes claim mutations are observable through the event log)
- BR-03 (events are immutable; the event log is append-only — implies claim history belongs there)

## Location

`src/substrate/_claims.py` — `acquire_claim`, `heartbeat_claim`, `release_claim`, `sweep_expired_claims`

## Suggested fix

Each claim mutation should emit an event under the canonical lock that's already held:

- `acquire_claim` → `transition="claim_acquired"`, payload `{actor_id, ttl_seconds, attempt_number}`
- Auto-steal path → `transition="claim_stolen"`, payload `{prior_actor_id, new_actor_id, attempt_number}`
- `heartbeat_claim` → optional `transition="claim_heartbeat"` (or skip — heartbeats are high-frequency; only persist via row update). Operator decision: log frequency vs. completeness.
- `release_claim` → `transition="claim_released"`, payload `{actor_id}`
- `sweep_expired_claims` → `transition="claim_expired"` per affected work-item, payload `{actor_id, expired_at}`

Open question for the operator: do heartbeats produce events? Spec is silent. Default: no — they are high-frequency and the row-update gives the durable state. Acquire / steal / release / expire are low-frequency and worth logging.

Replay (BC-001/002/003) should ignore these claim events for projection purposes — they don't affect `current_state` or `custom_fields`. They exist only for the audit trail.
