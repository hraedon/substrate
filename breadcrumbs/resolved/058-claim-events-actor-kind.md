---
number: "058"
title: Claim lifecycle events misattribute actor_kind as "system" for actor-triggered operations
severity: low
status: implemented
kind: bug
author: adversarial-reviewer
date: "2026-05-08"
tags: [fr-03, fr-06, fr-08, audit, actor-kind]
---

## Resolution

Added `actor_kind` parameter (default `"agent"`) to `acquire_claim` and `release_claim` in both backends and the public `Substrate` API. Claim events (`claim_acquired`, `claim_stolen`, `claim_released`) now correctly record the caller's `actor_kind` instead of hardcoded `"system"`. The `sweep_expired_claims` path retains `actor_kind="system"` since it is genuinely system-triggered.

This is a backward-compatible API change: existing callers that don't pass `actor_kind` get the default `"agent"`, matching the most common case.