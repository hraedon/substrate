---
number: "102"
title: No rate limiting on any public API endpoint
severity: critical
status: proposed
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, denial-of-service, api]
related: ["103"]
---

## Description

No rate limiting exists on any public API method. `acquire_claim`, `transition`, `append_event`, `create_link`, `register_workflow`, etc. all accept unbounded request rates from any caller.

An adversarial actor can:
- Flood the system with events (exhaust disk, memory, WAL)
- Create millions of work items
- Spam claim/unclaim cycles
- Exhaust the Postgres connection pool (default max 10 connections)

## Evidence

- `_connection.py:49`: `ConnectionPool` with `max_size=10`
- No rate limit middleware anywhere in `__init__.py` public API
- No per-actor request throttling
- No request size limits on payloads

## Impact

- **Connection pool exhaustion**: Rapid fire requests from one actor can hold all 10 connections, starving all other actors
- **Storage exhaustion**: Unlimited event creation fills disk
- **CPU exhaustion**: Validating signatures and processing events consumes CPU per request
- **Denial of service**: Work items can be permanently DOS'd via `not_before` (see #103)

## Fix

1. Add per-actor rate limiting at the API boundary (e.g., token bucket per `actor_id` on mutation methods)
2. Add a maximum payload size (e.g., 64KB on `payload` field)
3. Add a maximum `custom_fields` size
4. Add connection pool circuit breaker that rejects with `SERVICE_UNAVAILABLE` when pool is saturated
5. Consider per-project request quotas

## Notes

This is a production deployment concern. For homelab scale (single operator, few agents), this is low priority. But for any multi-tenant or internet-exposed deployment, this is a critical gap.