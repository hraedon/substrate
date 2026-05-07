---
number: "044"
title: ttl_seconds not validated — zero or negative values create immediately-expired claims
severity: medium
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-07"
tags: [claims, api-safety]
related: []
---

## Problem

`acquire_claim` and `heartbeat_claim` accepted any integer for `ttl_seconds`, including 0 and negative values. This creates claims whose `expires_at` is in the past, making them immediately sweepable. Almost certainly a caller error with no useful use case.

## Resolution

Added `INVALID_ARGUMENT` error code. Both `Substrate.acquire_claim` and `Substrate.heartbeat_claim` (and their InMemorySubstrate equivalents) now raise `INVALID_ARGUMENT` for `ttl_seconds <= 0`. Regression tests in `tests/test_session13_regression.py::TestTtlSecondsValidation`.
