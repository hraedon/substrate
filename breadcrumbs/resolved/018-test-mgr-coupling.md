---
number: "018"
title: Tests reach into private _mgr attribute for out-of-band SQL
severity: low
status: resolved
kind: improvement
author: opencode
date: "2026-05-05"
tags: [testing, api-surface, ac-29, ac-17]
related: ["017"]
---

## Problem

`test_replay.py` and `test_signing.py` access `substrate._mgr` directly to run raw SQL for simulating out-of-band edits (AC-29 drift detection) and calling internal replay with a revoked key set (AC-17). This couples tests to the internal `ConnectionManager` and its `transaction()` method signature.

If `_mgr` is renamed, restructured, or its transaction API changes, these tests break silently. The underscore prefix signals "private" — the test suite shouldn't depend on it.

## Spec reference

- AC-29 (out-of-band edit drift detection)
- AC-17 (replay halts on revoked key)
- §19 (public API boundary)

## Location

- `tests/test_replay.py` — `substrate._mgr.transaction()` for out-of-band UPDATE and internal replay call
- `tests/test_signing.py` — `substrate._mgr.transaction()` for out-of-band UPDATE

## Suggested fix

Add a `_test_helper` module or a `Substrate._debug_connection()` context manager that exposes a raw connection for testing purposes. Not part of the public API — ship it in a separate `substrate.testing` module or gate it behind an env var. Alternately, add a `Substrate.raw_sql(sql, params)` method that's documented as testing-only.
