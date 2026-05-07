---
number: "036"
title: External Postgres deployment guide
severity: n/a
status: accepted
kind: deployment
author: opus
date: "2026-05-06"
tags: [ops, postgres, deployment]
related: ["033"]
---

# External Postgres deployment guide

This guide assumes you already manage a Postgres server (bare metal, VM, or managed service) and want to point Substrate at it. It is a follow-the-steps recipe, not an architecture decision record.

## 1. Postgres version and extensions

Postgres **14 or newer** is required. Substrate uses JSONB, `TIMESTAMPTZ`, and standard DDL only. No extensions (e.g. `pgcrypto`, `uuid-ossp`) are needed; all UUIDs are generated client-side.

Verify by running `SELECT version();` on your target server.

## 2. Role and privileges

Run these **once** as a superuser on the target database:

```sql
CREATE ROLE substrate WITH LOGIN PASSWORD 'replace-me';
GRANT CREATE ON DATABASE your_database TO substrate;
```

`CREATE ON DATABASE` is required because `Substrate.create_project()` creates a new schema. The role automatically owns the objects it creates inside that schema, so no further grants are needed for normal operation.

## 3. DSN and TLS

Pass a standard libpq DSN to Substrate:

```
postgresql://substrate:replace-me@host:5432/your_database?sslmode=require
```

For certificate verification against a custom CA, use `verify-full` and point to the CA bundle:

```
postgresql://substrate:replace-me@host:5432/your_database?sslmode=verify-full&sslrootcert=/etc/ssl/certs/my_ca.crt
```

## 4. Server connection settings

Tune these in `postgresql.conf` (or via your managed-service parameter group):

| Parameter | Recommended value | Why |
|---|---|---|
| `max_connections` | 200 | Substrate pools 10 connections per instance by default; leave headroom for replays and ad-hoc queries. |
| `idle_in_transaction_session_timeout` | 5min | Catches leaked transactions from application bugs or interactive sessions. |
| `statement_timeout` | 30s | Normal Substrate operations are sub-second; replay is multi-query and still fits comfortably. |

## 5. PgBouncer

Substrate **requires session-mode pooling or a direct connection**. Transaction-mode poolers (including PgBouncer transaction mode) are incompatible because Substrate scopes every mutation with `SET LOCAL search_path`, which is transaction-scoped and must stay on the same physical backend for the life of the transaction.

See RFC-033 for the full analysis.

## 6. Bootstrap recipe

Install the library and prepare a key file:

```bash
pip install substrate
```

Create a JSON key file (e.g. `/etc/substrate/keys.json`):

```json
{
  "keys": [
    {
      "key_id": "prod-001",
      "secret": "base64-encoded-secret",
      "status": "active"
    }
  ]
}
```

Bootstrap the project and smoke-test:

```python
from substrate import Substrate

dsn = "postgresql://substrate:replace-me@host:5432/your_database?sslmode=require"

sub = Substrate.create_project(dsn, "my_project", hmac_key_path="/etc/substrate/keys.json")

# Fresh project sanity check: replay should report zero drift
report = sub.replay()
assert report.replayed_drift == 0

# One-event round-trip
sub.register_workflow(open("workflow.yaml").read())
wi, _ = sub.create_work_item("my_wf", "ticket", "agent_1")
wi = sub.transition(wi.work_item_id, "start", "agent_1")
print(wi.current_state)

sub.close()
```

## 7. Backup and restore

Substrate is event-sourced; the schema is fully derivable from the event log. A logical backup of the project schema is therefore sufficient:

```bash
pg_dump -Fc -n my_project your_database > my_project.dump
```

Restore:

```bash
pg_restore -d your_database --clean my_project.dump
```

After any restore, run `replay()` and confirm drift is zero before accepting the instance:

```python
report = sub.replay()
assert report.replayed_drift == 0
```

## 8. Multi-project sizing

One database can host many projects. Each project is an isolated schema; Postgres handles thousands of schemas without issue.

The practical ceiling is `max_connections` multiplied by the number of running Substrate instances, because every instance holds an open pool. If you run 5 application pods with `pool_max=10`, you need at least 50 connections plus headroom for replays and backups.
