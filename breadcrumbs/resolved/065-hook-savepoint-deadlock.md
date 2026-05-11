---
number: "065"
title: "HookConsumer nested transaction risk with append_event under savepoints"
severity: low
status: accepted
kind: design
author: deepseek-v4-pro
date: "2026-05-11"
tags: [hooks, transactions, deadlock]
related: []
resolution_date: "2026-05-11"
---

## Resolution

Accepted — nested savepoints are standard Postgres behavior. psycopg's `conn.transaction()` inside an outer `conn.transaction()` creates a savepoint, which is the intended pattern. A deadlock would only occur if a hook handler touches the same work item as a concurrent mutation — an unusual pattern. Running handlers outside transactions would sacrifice atomicity, which is worse.
