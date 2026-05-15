---
number: "154"
title: "examples/telemetry_via_hooks.py uses f-string SQL interpolation for schema/table names"
severity: medium
status: implemented
resolution: "Replaced all f-string SQL with `psycopg.sql.Identifier` and `psycopg.sql.SQL` composition for schema/table identifiers."
kind: security
author: agent
date: "2026-05-15"
tags: [examples, security, sql-injection]
related: []
---

## Problem

The telemetry example uses f-string interpolation:

```python
f'CREATE SCHEMA IF NOT EXISTS "{REPORTING_SCHEMA}"'
f'INSERT INTO "{REPORTING_SCHEMA}".transitions_by_role ...'
```

While `REPORTING_SCHEMA` is currently a hardcoded constant, this pattern is copy-paste bait.
An operator adapting this to accept user input will create an SQL injection vector.

## Impact

Examples are copy-paste artifacts in production codebases. The pattern normalizes unsafe
SQL construction and contradicts the secure-by-example principle.

## Files / Lines

- `examples/telemetry_via_hooks.py` (~28-49, ~65-74)

## Fix

Use `psycopg.sql.Identifier(REPORTING_SCHEMA)` and `psycopg.sql.SQL(...)` for dynamic
identifier composition, or add a prominent comment warning against f-string SQL.
