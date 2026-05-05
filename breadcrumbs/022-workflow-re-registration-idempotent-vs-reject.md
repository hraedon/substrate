---
number: "022"
title: Workflow re-registration is idempotent but spec says reject
severity: medium
status: proposed
kind: design
author: glm-5.1
date: "2026-05-05"
tags: [spec, workflow]
related: []
---

## Problem

The spec error table states: "Concurrent workflow version registration — Two registrations of same (name, version) — First wins; second rejects with 'version already registered.'"

The error code `WORKFLOW_VERSION_ALREADY_REGISTERED` exists in `_errors.py` but is never used. The implementation (`__init__.py:171-183`) returns the existing row without error (idempotent behavior). The test `test_register_idempotent` confirms idempotency.

## Decision needed

- **Option A (match spec):** Raise `WORKFLOW_VERSION_ALREADY_REGISTERED` on duplicate registration, update the test.
- **Option B (amend spec):** Idempotent behavior is more useful for agent pipelines; amend the spec to allow it and remove the unused error code.

## Location

`src/substrate/__init__.py` `register_workflow()` lines 170-205.
`src/substrate/_errors.py` line 22 (`WORKFLOW_VERSION_ALREADY_REGISTERED`).
`tests/test_smoke.py` `test_register_idempotent`.
