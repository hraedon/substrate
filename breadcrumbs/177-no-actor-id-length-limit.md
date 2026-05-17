---
number: "177"
title: No actor_id length limit — Postgres TEXT column permits ~1GB values
severity: low
status: proposed
kind: improvement
author: security-audit
date: "2026-05-17"
tags: [validation, input-sanitization, api-boundary]
related: []
---

## Observation

`actor_id` is a free-form string passed through the public API to Postgres TEXT columns (which can hold up to ~1GB). No explicit length validation exists in the library or sidecar API boundary. Practical impact is bounded:
- Sidecar: HTTP request size limits prevent abuse.
- Library: in-process call limits provide implicit bounds.
- Postgres indexes on `actor_id` (e.g., `idx_claims_actor_id`) are B-tree indexes that degrade with extremely long values.

No existing breadcrumb covers this — BC-103 covered UUID validation for `event_id`, but no equivalent check exists for `actor_id`.

## Proposed

- Add `MAX_ACTOR_ID_LENGTH` constant (e.g., 255 characters) to `_contract.py`.
- Validate in `validate_mutation_params()` alongside existing `validate_actor_kind()`.
- Add Pydantic `max_length=255` constraint to `actor_id` fields in sidecar models.
