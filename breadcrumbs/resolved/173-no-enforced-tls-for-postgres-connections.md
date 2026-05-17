---
number: "173"
title: No forced TLS enforcement on Postgres connections — unencrypted credential exposure risk
severity: medium
status: proposed
kind: improvement
author: security-audit
date: "2026-05-17"
tags: [security, tls, connection, deployment]
related: []
---

## Observation

`ConnectionManager.__init__` at `_connection.py:41-60` accepts the DSN string verbatim. If an operator provides a DSN without `sslmode=require` (or `sslmode=verify-full`), the connection to Postgres will be unencrypted. This means HMAC key identifiers, actor IDs, and all data flow in cleartext over the network.

The library does not enforce a minimum TLS level and provides no configuration parameter to require it. The `configure_session` callback at `_connection.py:33-34` sets `synchronous_commit = on` but does not verify the encryption status of the connection.

## Proposed

- Add an `require_ssl: bool = False` parameter to `ConnectionManager.__init__`, `Substrate.__init__`, and `Substrate.create_project` (default `False` for backward compatibility).
- When enabled, verify during connection setup (in `_configure_session`) that `pg_stat_ssl` reports `ssl = true` for the session. Raise a clear error if SSL is not active.
- Alternatively, parse the DSN for `sslmode` and warn if absent when key-based auth is configured.
- Document the TLS requirement in deployment guides.
