---
number: "065"
title: HookConsumer nested transaction risk with append_event under savepoints
severity: low
status: deferred
kind: design
author: deepseek-v4-pro
date: "2026-05-11"
tags: [hooks, transactions, deadlock]
related: []
---

## Context

`HookConsumer._run` (`_hooks.py:410-417`) wraps `poll_and_process_hooks` in
`conn.transaction()`. Inside `poll_and_process_hooks`, the handler is called
inside another `conn.transaction()` (line 155), which creates a psycopg
savepoint. If the handler or dead-letter path calls `append_event`, that
acquires `SELECT ... FOR UPDATE` on a work item — inside a savepoint, inside
the outer transaction.

## Risk

If a concurrent mutation holds a conflicting row lock, this could deadlock
instead of waiting cleanly. Low probability in practice — requires hook
handler to touch the same work item as a concurrent mutation — but structurally
worth noting.

## Options

- Run handlers outside the outer transaction (autocommit mode)
- Use advisory locks per hook instead of row locks for dead-letter
- Accept the risk (nested savepoints are Postgres-standard behavior)
