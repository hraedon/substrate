---
number: "160"
title: "ConnectionPool missing configurable max_lifetime and health-check parameters"
severity: low
status: implemented
resolution: "Added `pool_max_lifetime` parameter to `ConnectionManager`, `Substrate.__init__`, and `Substrate.create_project`, passed through to `psycopg_pool.ConnectionPool(max_lifetime=...)`."
kind: improvement
author: agent
date: "2026-05-15"
tags: [connection-pool, ops]
related: []
---

## Problem

`src/substrate/_connection.py` (~49-55) creates `psycopg_pool.ConnectionPool` with only
`min_size` and `max_size`. `max_lifetime`, `check` (health check), and `max_idle` are not
exposed or configured. In long-running processes, connections can be dropped by firewalls
or server-side timeouts, leading to first-query failures.

## Impact

Stale pooled connections produce unpredictable first-query failures that the caller must
retry. This contradicts the substrate design principle of being predictable for callers.

## Files / Lines

- `src/substrate/_connection.py` (~49-55)

## Fix

Expose `pool_max_lifetime` and `pool_check_interval` as constructor args on `Substrate`
and pass them through to `ConnectionPool`.
