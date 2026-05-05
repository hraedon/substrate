---
number: "017"
title: Test coverage missing for load-bearing ACs
severity: high
status: resolved
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [testing, ac-17, ac-24, ac-26, ac-28, ac-29, ac-33, ac-34]
related: ["001", "002", "003", "004", "008"]
---

## Problem

`tests/test_smoke.py` originally covered happy paths only (20 tests). The load-bearing ACs that distinguish substrate from "ad-hoc Postgres tables" had no coverage.

## Resolution

All 8 load-bearing ACs now covered across dedicated test files:

| AC | Property | Test file |
|---|---|---|
| AC-17 | Replay halts on revoked-key event | `test_replay.py` (2 tests) |
| AC-24 | Idempotent retry + mismatch rejection | `test_idempotency.py` (3 tests) |
| AC-25 | expected_event_seq mismatch | `test_idempotency.py` (3 tests) |
| AC-26 | Re-verify after jsonb formatting change | `test_signing.py` (5 tests) |
| AC-28 | Concurrent event_seq gap-free | `test_concurrency.py` (2 tests) |
| AC-29 | Out-of-band edit drift detection | `test_replay.py` (3 tests) |
| AC-33 | Pre-signed event rejection | `test_api_surface.py` (1 test) |
| AC-34 | No Postgres types leak | `test_api_surface.py` (4 tests) |

Phase 2 ACs covered in `test_phase2.py` (11 tests): escalation (FR-10), validators (FR-13), hooks (FR-13), dead-letter requeue (FR-14), actor metadata lint (FR-18).

Total: 81 tests + 3 scale benchmarks across 9 files.
