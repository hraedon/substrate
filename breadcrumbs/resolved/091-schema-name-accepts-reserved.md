---
number: "091"
title: Schema name validation accepts reserved / system schema names
severity: high
status: open
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [connection, security, schema, naming]
related: []
---

## Observation

`validate_project_name` uses `^[a-z_][a-z0-9_]{0,62}$`. This accepts `public`, `pg_temp_1`, `information_schema`, `pg_catalog`, etc. `Substrate.create_project("public", ...)` would run migrations against the `public` schema, potentially clobbering existing objects. `drop_project_schema` would then `DROP SCHEMA public CASCADE`.

## Impact

Data loss in shared schemas, privilege escalation (writing to `information_schema`), or accidental destruction of system schemas.

## Proposed Fix

Reject reserved schema names (`public`, `pg_*`, `information_schema`) in `validate_project_name`.

## Acceptance Criteria

- [ ] `validate_project_name("public")` raises `ValueError`.
- [ ] `validate_project_name("pg_catalog")` raises `ValueError`.
- [ ] `validate_project_name("information_schema")` raises `ValueError`.
- [ ] Random generated names still pass.
