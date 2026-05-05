---
number: "019"
title: Session-scoped smoke test fixture accumulates state across tests
severity: low
status: resolved
kind: improvement
author: opencode
date: "2026-05-05"
tags: [testing, test-isolation]
related: ["017"]
---

## Problem

`tests/test_smoke.py` uses a single `session`-scoped fixture that creates one project and shares it across all 20 tests. Tests that create work items or claims accumulate in the same project, so any test asserting on global counts (e.g., "query returns exactly N items") would be fragile.

The newer test files (`test_idempotency`, `test_concurrency`, `test_signing`, `test_replay`) use per-test or per-module fixtures with fresh projects and proper teardown. The smoke test doesn't need that level of isolation for its current happy-path assertions, but it should be noted as a deliberate trade-off.

## Spec reference

N/A — test quality, not spec compliance.

## Location

`tests/test_smoke.py` — `substrate` fixture (line 14-21)

## Suggested fix

Low priority. If the smoke test suite grows to include count-based assertions, switch to per-test or per-module fixtures with `DROP SCHEMA` teardown, matching the pattern in the newer test files. Until then, document the session scope as intentional.
