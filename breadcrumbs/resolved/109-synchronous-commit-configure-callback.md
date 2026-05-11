---
number: "109"
title: synchronous_commit configure callback raises silently on connection failure
severity: medium
status: rejected
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [correctness, durability, nfr-durability-1]
resolution_date: "2026-05-11"
---

## Resolution

Rejected — false alarm. The breadcrumb's own analysis concludes this is a non-issue. psycopg's `ConnectionPool.configure` callback runs on connection creation; if it raises, the connection is discarded and replaced. All mutations go through `mgr.transaction()` which uses connections from the pool where `_configure_session` has already succeeded. Session-level `SET synchronous_commit = on` is correct per spec ("per session on its own connections").
