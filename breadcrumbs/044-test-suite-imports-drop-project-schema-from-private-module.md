---
number: "044"
title: Test suite still imports drop_project_schema from substrate._testing
severity: low
status: proposed
kind: improvement
author: assistant
date: "2026-05-07"
tags: [testing, api-ergonomics]
related: []
---

## Observation

`drop_project_schema` was promoted to the public `substrate.testing` module in session 14. However, all 23 test files still import it from the private `substrate._testing` path. This means the internal test suite does not dogfood the public API. If `_testing.py` is reorganized or renamed in the future, all tests break despite the public path being stable.

## Proposed

Migrate all test imports from `substrate._testing` to `substrate.testing` for `drop_project_schema` (and any other public re-exported symbols like `InMemorySubstrate`). Keep only truly internal-only imports (e.g. `raw_transaction`, `KeySet`) in `_testing`.
