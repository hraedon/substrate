---
number: "077"
title: "Missing validate_ttl in resolve_claim_acquire"
severity: high
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_contract.py:198-268` — `resolve_heartbeat` (line 286) calls `validate_ttl`,
but `resolve_claim_acquire` does not. The public API validates before calling,
but the contract function is inconsistent.

## Fix

Add `validate_ttl(ttl_seconds)` at the top of `resolve_claim_acquire`.
