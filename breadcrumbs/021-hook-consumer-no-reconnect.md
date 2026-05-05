---
number: "021"
title: Hook consumer swallows all exceptions from NOTIFY listen loop
severity: medium
status: proposed
kind: design
author: glm-5.1
date: "2026-05-05"
tags: [fr-13, hooks, error-handling]
related: []
---

## Problem

In `_hooks.py` `HookConsumer._run()`, the NOTIFY listen loop wraps `conn.notifies()` in a bare `except Exception: pass`. If the database connection drops or the Postgres server restarts, the consumer silently enters an infinite loop where it polls on a dead connection, processes no hooks, and logs no error. The only observable signal is that hooks stop being delivered.

## Spec reference

§8 Error table: "LISTEN/NOTIFY connection drop — Network blip in hook consumer — Polling fallback drains queue at 30s interval; consumer reconnects opportunistically — Structured log." The current implementation does NOT reconnect.

## Location

`src/substrate/_hooks.py` `HookConsumer._run()` — the `except Exception: pass` blocks.

## Suggested fix

1. Catch specific exceptions (psycopg.OperationalError) for the NOTIFY listen
2. On connection loss: log the error, close the connection, sleep briefly, reconnect with a new connection (re-issue SET search_path + LISTEN)
3. Add a max-reconnect-attempts counter with structured logging on exhaustion
4. For the poll_and_process_hooks exception, log the error but continue (current behavior is acceptable for the poll path)

This is the single biggest reliability gap in the Phase 2 implementation. Without reconnection, any Postgres restart kills the hook consumer permanently (until the host app restarts).
