---
number: "165"
title: "Sidecar `heartbeat_claim` uses `AcquireClaimRequest` instead of `HeartbeatClaimRequest` — `expected_attempt_number` dropped"
severity: critical
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-16"
tags: [sidecar, plan-005, claims]
related: ["161"]
---

## Problem

`src/substrate/sidecar/routes.py:198` used `AcquireClaimRequest` as the body model for the `heartbeat_claim` route. This model lacks the `expected_attempt_number` field. The `HeartbeatClaimRequest` model exists in `models.py` but was never imported.

The core API `heartbeat_claim` accepts `expected_attempt_number` to detect stale sessions after claim theft. The sidecar silently dropped it, and sending it would cause a 422 due to `extra="forbid"`.

## Fix

Changed the route to use `HeartbeatClaimRequest`, added import, and wired `expected_attempt_number=body.expected_attempt_number` through to the core API call.
