---
number: "071"
title: "Heartbeat revives expired claims (zombie revival)"
severity: critical
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_contract.py:278-315` — `resolve_heartbeat` checks actor_id and attempt_number
but never checks `claim_state["expires_at"] >= now`. An actor whose claim
expired can heartbeat it back to life, defeating TTL-based expiry and blocking
claim theft/escalation.

## Fix

Add expiry check to `resolve_heartbeat` after the None check, before the actor
check. Raise CLAIM_LOST if the claim has expired.
