# RFC-033: Schema-per-project and PgBouncer transaction-mode incompatibility

---
number: "033"
title: Schema-per-project and PgBouncer transaction-mode incompatibility
severity: medium
status: proposed
kind: design
author: perplexity-review
related: []
---

## Problem

Substrate uses one Postgres schema per project and scopes each transaction with:

```sql
SET LOCAL search_path TO <schema>
```

`SET LOCAL` is transaction-scoped: it resets at `COMMIT` or `ROLLBACK`. This works correctly with a direct connection pool (psycopg `ConnectionPool`) because the same physical connection is reused across transactions in the same session.

It does **not** work with pooling middleware such as **PgBouncer in transaction mode**, where each SQL statement or transaction may be dispatched to a different backend connection. In that mode:

1. `SET LOCAL search_path` only affects the current transaction.
2. If a connection is returned to the pool and reused for a different "logical session", the `search_path` is already reset.
3. Worse, if a multi-statement transaction is split across backends, the `search_path` set in statement N may not be present in statement N+1.

This means schema-per-project isolation silently breaks under PgBouncer transaction mode, causing queries to land in the wrong schema or fail with "relation does not exist".

## Assessed severity: medium

Not a bug today — the project targets homelab scale with direct pooling. It is a scaling cliff if the deployment ever moves to a managed Postgres with PgBouncer (common on AWS RDS, DigitalOcean, etc.).

## Options

### Option A: Document as known constraint (recommended near-term)

Add an explicit "Known constraints" section to README.md and AGENTS.md stating:

> Substrate's schema-per-project model requires session-scoped `search_path`. It is incompatible with connection pooling middleware that dispatches transactions across different backends (e.g., PgBouncer in transaction mode). Use PgBouncer in session mode, or connect directly to Postgres.

**Pros:** Zero code change, honest about boundary.  
**Cons:** Doesn't remove the cliff, just marks it.

### Option B: Add `options=-c search_path=` to connection DSN

Set `search_path` at connection establishment time via connection parameters:

```
postgresql://user:pass@host/db?options=-c%20search_path%3Dmy_project
```

**Pros:** Works with any pooler because it's connection-level.  
**Cons:** Requires a separate connection string (or connection pool) per project, defeating the "one pool" design. Also leaks schema names into DSNs.

### Option C: Switch to `SET` (session-scoped) instead of `SET LOCAL`

Use `SET search_path = ...` (without `LOCAL`) so it persists for the lifetime of the physical connection.

**Pros:** Works with PgBouncer session mode.  
**Cons:** Dangerous with transaction mode — the `search_path` leaks to the next session that reuses the same backend connection, causing cross-tenant data leakage.

### Option D: Fully-qualified table names

Eliminate `search_path` entirely and prefix every table reference with `schema.table`.

**Pros:** Works with any pooler, any mode.  
**Cons:** Every SQL query in the codebase needs to be rewritten. Schema name must be threaded into every internal function that builds SQL. Loses some of the simplicity of the current design.

### Option E: `tenant_id` in shared tables (documented but not implemented)

AGENTS.md already notes this as a future path: add a `tenant_id` column to all shared tables and drop schema-per-project.

**Pros:** Ultimate compatibility with any pooler, any scale.  
**Cons:** Requires a migration, loses schema-level isolation, needs row-level authorization.

## Recommendation

Implement **Option A** immediately (documentation). Keep **Option D** as the medium-term migration path if PgBouncer transaction mode becomes a hard requirement.

## Questions to resolve

1. Does the target deployment environment actually use PgBouncer transaction mode?
2. Is the added complexity of Option D worth the portability gain?
3. Should we add a runtime check that warns if `server_version` suggests a pooler is in use?
