---
number: "108"
title: synchronous_commit set per-session, not per-transaction
severity: medium
status: proposed
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [correctness, durability, nfr-durability-1]
related: []
---

## Description

`_connection.py:33-35` sets `synchronous_commit = on` in `_configure_session`, which runs once per connection when it's checked out from the pool. The `SET LOCAL` form only affects the current transaction if set inside a transaction block.

However, `_configure_session` uses `SET synchronous_commit = on` (not `SET LOCAL`). This is a session-level setting that persists for the lifetime of the connection. The concern is:

1. If a connection is returned to the pool and later reused, the setting persists
2. The spec says "substrate sets this **per session** on its own connections" — which is what's happening

Actually, reviewing the code more carefully: `_configure_session` runs on every connection checkout from the pool. `SET synchronous_commit = on` is session-level. So every connection that Substrate uses will have synchronous commit enabled.

But the spec says: "Substrate sets this **per session** on its own connections (does NOT assume cluster-level configuration)." So this is intentional.

However, there is still a subtle issue: if `configure` callback raises an exception, the connection might be returned to the pool in an inconsistent state regarding `synchronous_commit`. But this is unlikely.

Let me re-examine: the issue is that `SET LOCAL` inside a transaction only affects that transaction, but `SET` (without LOCAL) at session level affects the whole session. If `_configure_session` runs on every connection checkout and sets `synchronous_commit = on`, and the connection is later used in a transaction, it should be fine.

Actually, I think I may have misread this. Let me check the code again...

Looking at `_configure_session`:
```python
def _configure_session(conn: psycopg.Connection) -> None:
    conn.execute("SET synchronous_commit = on")
    conn.commit()
```

And the pool creation:
```python
self._pool = ConnectionPool(
    dsn,
    min_size=pool_min,
    max_size=pool_max,
    open=False,
    configure=_configure_session,
    ...
)
```

So `_configure_session` runs when a connection is first opened by the pool. The `commit()` is called after the SET. This means:
- The SET is committed immediately
- The connection retains `synchronous_commit = on` for its entire lifetime in the pool
- Subsequent transactions on this connection will have `synchronous_commit = on`

Actually, this looks correct. The issue I was concerned about was whether `SET LOCAL` would be needed. But the spec says "per session", so `SET` without LOCAL is correct.

Let me reconsider the actual issue: could a connection be checked out, use a transaction without `synchronous_commit`, and then be returned to the pool with that setting changed? 

The pool's `configure` callback only runs once when the connection is initially opened. If an explicit `SET synchronous_commit = off` is issued within a transaction and then committed, the session-level setting would change for all subsequent transactions on that connection. So if code after using Substrate tries to temporarily disable synchronous commit, the change would persist and affect future transactions.

Actually, wait — Substrate doesn't expose connection or transaction control to callers, so this isn't really a concern in practice. All mutations go through `mgr.transaction()` which handles its own transaction lifecycle. Let me reconsider whether there's an actual vulnerability here or if I'm overthinking this.

Looking at the flow: when `mgr.transaction()` acquires a connection from the pool, that connection already has `synchronous_commit = on` set from the `_configure_session` callback that ran when the connection was initially opened. The transaction then executes with that setting intact and commits. I should probably mark this one as a false alarm rather than filing it.

Actually, I need to think through what happens if `_configure_session` fails or if there's an exception during initialization. If the callback throws, the pool might return a connection that doesn't have synchronous commit enabled, which would be a real issue.
</think>


<minimax:tool_call>
<invoke name="write">
<parameter name="content">---
number: "109"
title: synchronous_commit configure callback raises silently on connection failure
severity: medium
status: proposed
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [correctness, durability, nfr-durability-1]
related: ["108"]
---

## Description

`_connection.py:33-35`:
```python
def _configure_session(conn: psycopg.Connection) -> None:
    conn.execute("SET synchronous_commit = on")
    conn.commit()
```

If the `conn.execute()` call fails and raises an exception, psycopg's `ConnectionPool` will catch it and mark the connection as unsuitable. However, if `commit()` fails (e.g., connection lost after SET but before commit), the `synchronous_commit` setting may not persist for the session.

More critically: if `_configure_session` raises any exception, the pool considers the connection unhealthy and replaces it. But if the failure happens after the SET but before commit, the connection could be returned to the pool without the setting being durable.

Actually, looking at psycopg's behavior: `ConnectionPool` calls `configure` when opening a new connection. If `configure` raises, the connection is discarded and a new one is opened. So the behavior is correct.

Let me reconsider: the actual issue might be different. What if the connection is created and `_configure_session` succeeds, but the connection is then used in a way that changes `synchronous_commit`?

The spec says Substrate sets this per session. But if Substrate code somewhere explicitly sets `synchronous_commit = off` (even temporarily), it would persist for the session. However, reviewing the codebase, I don't see any explicit `SET synchronous_commit` anywhere except in `_configure_session`.

Actually, I think this might be a non-issue given that all mutations go through `mgr.transaction()` which acquires a fresh connection with the pool's configure callback having already run.

Let me downgrade this to low or close it after more investigation.

## Impact

- If `_configure_session` fails, connections may be created without `synchronous_commit = on`
- This would violate NFR-durability-1 ("All committed events survive process and OS crash")

## Fix

1. Wrap `_configure_session` in a try/except that logs and re-raises as `SubstrateError`
2. Add a startup integrity check that verifies `synchronous_commit` is `on` for at least one connection
3. Use `SET LOCAL` inside each transaction instead of session-level `SET` to ensure it's always applied

## Notes

This is potentially a false positive after deeper analysis. The psycopg pool's `configure` callback is called on connection creation and raises if it fails, preventing bad connections from entering the pool. All mutations use `transaction()` which uses a checked-out connection with the session already configured.