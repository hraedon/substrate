---
number: "022"
title: Workflow re-registration is idempotent but spec says reject
severity: medium
status: resolved
kind: design
author: glm-5.1
date: "2026-05-05"
tags: [spec, workflow]
related: []
---

## Problem

The spec error table states: "Concurrent workflow version registration — Two registrations of same (name, version) — First wins; second rejects with 'version already registered.'"

The error code `WORKFLOW_VERSION_ALREADY_REGISTERED` exists in `_errors.py` but is never used. The implementation (`__init__.py:171-183`) returns the existing row without error (idempotent behavior). The test `test_register_idempotent` confirms idempotency.

## Decision

Content-based idempotency (BC-022 option B sharpened): same (name, version, content_hash) returns existing row; same (name, version) with different content raises `WORKFLOW_VERSION_CONFLICT`. Follows BC-007 precedent (compare payloads on collision rather than blanket-accept). Spec §8 amended with BC-022 rationale.

## Resolution

- Added `content_hash BYTEA` column to `workflow_registry` via migration `004_workflow_content_hash.sql`.
- `register_workflow()` computes SHA-256 of JCS-canonicalized `wf.to_dict()` and stores it.
- Same content → idempotent return; different content → `WORKFLOW_VERSION_CONFLICT`.
- Renamed `WORKFLOW_VERSION_ALREADY_REGISTERED` → `WORKFLOW_VERSION_CONFLICT` (unused, no API break).
- Lazy backfill: legacy rows with NULL content_hash get hashed from stored definition on first access.
- Spec §8 and error table amended with BC-022 rationale.
- Tests: `test_register_idempotent` (same content) + `test_register_version_conflict` (different content).
