---
number: "156"
title: "drop_project_schema leaks an open database connection if DROP raises"
severity: medium
status: implemented
resolution: "Replaced manual `connect/close` with `with psycopg.connect(...) as conn:` context manager."
kind: bug
author: agent
date: "2026-05-15"
tags: [testing, resource-leak]
related: []
---

## Problem

`drop_project_schema` in `src/substrate/_testing.py` (~33-47):

```python
conn = psycopg.connect(dsn, autocommit=True)
conn.execute(SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(Identifier(project)))
conn.close()
```

If `conn.execute` raises, `conn.close()` is never called.

## Impact

Test helpers accumulate leaked connections under failure scenarios. In large test suites
with many schema drops, this can exhaust local ports or connection limits.

## Files / Lines

- `src/substrate/_testing.py` (~33-47)

## Fix

Wrap in `try/finally` or use a context manager: `with psycopg.connect(...) as conn:`.
