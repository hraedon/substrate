# RFC-036: External Postgres as a backend — adapter abstraction and portability assessment

---
number: "036"
title: "External Postgres as a backend — adapter abstraction and portability assessment"
severity: medium
status: proposed
kind: design
author: user-request
related: ["033"]
---

## Problem

Substrate is hard-wired to Postgres. Every module makes deep, specific assumptions about the backend:

1. **Schema DDL** — `CREATE SCHEMA`, `GRANT ON SCHEMA`, `information_schema.schemata`.
2. **`SET LOCAL search_path`** — transaction-scoped schema switching.
3. **JSONB** — `payload` and `actor_metadata` use `psycopg.types.json.Jsonb` and operators like `->>`, `#>`, `@>`.
4. **`LISTEN / NOTIFY`** — the hook consumer thread relies on async notification from Postgres.
5. **Row-level locking** — `SELECT ... ORDER BY work_item_id FOR UPDATE` for gap-free `event_seq` allocation.
6. **Sequence semantics** — `next_event_seq` is a column incremented manually under lock, relying on ACID isolation.
7. **Specific SQL features** — `DELETE ... RETURNING`, `ON CONFLICT`, `NOT EXISTS` subqueries, `now()`, `interval` literals.
8. **Connection pooling** — tightly coupled to `psycopg_pool.ConnectionPool`.

If a deployment requires a different backend (SQLite for local testing, CockroachDB for geo-distribution, Spanner for horizontal scaling), these assumptions become blocking.

## Assessed severity: medium

Not blocking today — Postgres is the target deployment. It is an architectural cliff for future portability.

## Goals (if pursued)

1. Allow substrate to run on **SQLite** for zero-setup local development / testing.
2. Allow substrate to run on **CockroachDB** (wire-compatible but not identical) for multi-region deployments.
3. Allow substrate to run on **other backends** (e.g., Spanner, MySQL 8) with an adapter layer.
4. Do so with **zero drift** from the Postgres path — the main CI must continue to run on Postgres.

## Analysis: tight coupling points

| Module | Postgres-specific dependency | Portability blocker level |
|---|---|---|
| `_connection.py` | `psycopg`, `ConnectionPool`, `SET LOCAL search_path` | Critical |
| `_migrations.py` | Raw SQL DDL (schema creation, table creation, GRANT) | Critical |
| `_events.py` | `Jsonb`, `FOR UPDATE`, gap-free seq under lock | Critical |
| `_work_items.py` | `SELECT FOR UPDATE`, `Jsonb`, `now()` | Critical |
| `_claims.py` | `DELETE ... RETURNING`, `now()`, timestamp arithmetic | High |
| `_replay.py` | `CREATE TABLE ... AS SELECT`, `pg_tables`, `Identifier` | High |
| `_hooks.py` | `LISTEN`, `NOTIFY`, thread-per-connection | Critical |
| `_workflow.py` | None (pure Python) | None |
| `_signing.py` | None (pure Python / HMAC) | None |
| `_types.py` | None (frozen dataclasses) | None |
| `_errors.py` | None | None |

The **critical** items cannot be papered over with SQL shims. They require behavioral changes or feature substitution:

- `FOR UPDATE` → SQLite doesn't support it in the same way; CockroachDB does.
- `LISTEN/NOTIFY` → SQLite has no equivalent; CockroachDB has a different mechanism.
- `SET LOCAL search_path` → SQLite has no schema concept; CockroachDB supports schemas.

## Options

### Option A: Postgres-only forever (recommended near-term)

Document explicitly that substrate requires Postgres 15+ and that portability is not on the roadmap. SQLite is not supported. CockroachDB is not tested.

**Pros:** Zero code change, zero complexity drift, the spec stays simple.  
**Cons:** Rules out zero-setup local dev (requires Docker for tests), rules out CockroachDB geo-distribution.

### Option B: SQLite adapter for local dev / tests

Create a `_backend.py` abstract interface and two implementations: `_backend_postgres.py`, `_backend_sqlite.py`.

SQLite differences:
- No `CREATE SCHEMA` → use `ATTACH DATABASE` with table prefixing, or ignore schema entirely.
- No `SET search_path` → fully qualify or use a single database per project.
- `JSON` column type (stores text) instead of `JSONB`.
- No `FOR UPDATE` → rely on SQLite's file-level locking. Gap-free `event_seq` via `MAX(event_seq) + 1` inside the same write lock.
- No `LISTEN/NOTIFY` → poll the `hook_queue` table with a short interval.
- No `DELETE ... RETURNING` → `SELECT * FROM ...; DELETE FROM ...` within the same transaction.
- Timestamps stored as ISO 8601 strings.
- `uuid.UUID` → store as BLOB (16 bytes) or TEXT (36 chars).

**Pros:** Enables `pip install substrate && substrate.create_project("sqlite:///substrate.db", ...)` for quick starts. Fast tests without Docker.  
**Cons:** Huge surface area. Every SQL query needs an abstraction layer. `replay()` creates temp tables — that needs a completely different approach in SQLite. Hook latency switches from push to poll. The test suite would need to run twice (Postgres + SQLite). Risk of Postgres-first drift.

### Option C: CockroachDB compatibility layer

CockroachDB is wire-protocol compatible with Postgres. The delta is smaller than SQLite:
- `SET LOCAL search_path` works.
- `FOR UPDATE` works (with some caveats around ordering).
- `LISTEN/NOTIFY` does **not** work in CockroachDB. Would need to replace with polling or an external message broker.
- `CREATE TABLE ... AS SELECT` works.
- `interval` and `now()` are supported.

**Pros:** Multi-region, survivable, horizontally scalable. Wire-compatibility means most psycopg code works.  
**Cons:** `LISTEN/NOTIFY` is a hard gap. Would need to rearchitect the hook consumer. CI would need a CockroachDB instance.

### Option D: Full backend abstraction

Design an internal `Backend` protocol (as a `typing.Protocol` or abstract base class) with methods like:

```python
class Backend(Protocol):
    def execute(self, sql: str, params: tuple) -> list[dict]: ...
    def transaction(self) -> Generator[Connection, None, None]: ...
    def listen(self, channel: str, callback: Callable) -> None: ...
    def json_type(self) -> str: ...
    def schema_support(self) -> bool: ...
```

Every module calls into the backend instead of raw SQL.

**Pros:** Cleanest architecture. Postgres, SQLite, CockroachDB, even Redis or DynamoDB could plug in.  
**Cons:** Massive refactoring. Every SQL query becomes a method. The abstraction leaks — some features (JSON operators, row locking, temp tables) are hard to express generically. Would take a full rewrite, not an incremental change.

## Recommendation

**Option A for now. Revisit Option B if SQLite local dev becomes a hard requirement.**

The honest assessment is that substrate's value proposition is "coordination and durable state for agent pipelines over Postgres." The "over Postgres" part is load-bearing:
- Event log ordering and gap-free sequences rely on ACID isolation.
- Projection consistency relies on `FOR UPDATE`.
- Hook delivery relies on `LISTEN/NOTIFY` push semantics.

Replacing any of these changes the semantics and the performance model. It is not a "swap the driver" refactor. It is a re-architecture.

If the user wants a zero-setup experience, a Docker Compose file plus a quick-start script is lower complexity and lower risk than a SQLite adapter.

## Concrete minimal step (if we ever revisit)

If Option B is ever approved, the implementation order should be:

1. **JSON type abstraction** — replace `psycopg.types.json.Jsonb` with a `to_json(value)` helper that returns `Jsonb` on Postgres and `json.dumps(value)` on SQLite.
2. **Connection manager abstraction** — replace `_connection.ConnectionManager` with a `Backend` ABC that handles transaction scoping. Postgres uses `SET LOCAL search_path`; SQLite prefixes tables.
3. **Hook delivery abstraction** — Postgres uses `LISTEN/NOTIFY`; SQLite polls `hook_queue`.
4. **Replay temp tables** — replace `CREATE TABLE ... AS SELECT` with in-memory Python or SQLite temp tables.
5. **Test matrix** — CI runs the full suite on Postgres; a fast subset runs on SQLite.

## Questions to resolve

1. Is zero-setup (no Docker) a hard requirement for the target audience?
2. Is CockroachDB geo-distribution a hard requirement, or is Postgres with read replicas sufficient?
3. Would a `docker-compose.quickstart.yml` in the repo eliminate the need for this RFC?
4. If we abstract the backend, should the spec still mandate Postgres semantics (ACID, row locks, push notifications), or should the spec become backend-agnostic?
