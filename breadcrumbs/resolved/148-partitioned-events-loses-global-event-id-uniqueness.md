---
number: "148"
title: "Partitioned events table loses global event_id uniqueness; cross-work-item collisions possible"
severity: critical
status: implemented
resolution: "Added `pg_advisory_xact_lock` on SHA-256 hash of event_id before INSERT in both `append_event` and `append_transition_event`. Prevents cross-work-item event_id collisions under partitioned unique constraint."
kind: bug
author: agent
date: "2026-05-15"
tags: [partition, data-integrity, fr-03, br-12]
related: ["145"]
---

## Problem

Migration 010 recreates `events` with declarative partitioning by `timestamp` range.
Postgres requires the partition key to be part of unique indexes, so a global unique
constraint on `event_id` alone is impossible. The partitioned index is `UNIQUE (event_id, timestamp)`.

The application-level idempotency check in `_events.py` (`check_idempotency`) only queries
per-work-item. Two concurrent `append_event` calls on **different** work items with the same
`event_id` can both pass the idempotency check because they lock different
`work_items_current` rows. Both then insert rows with the same `event_id` but different
`timestamp`s, and the partitioned unique index allows both.

This violates the spec's guarantee that `event_id` is unique within a project DB (FR-03 / BR-12).

## Impact

An attacker or bug could reuse an `event_id` across work items, creating audit-trail
ambiguity and breaking idempotency semantics. The event log is no longer a globally
unique append-only log.

## Files / Lines

- `migrations/010_events_partition.sql` (~12-30)
- `src/substrate/_events.py` (~66-74)

## Fix

Add an application-level global uniqueness guard — e.g., an advisory lock on the event_id
hash, or a small `event_ids_seen` table with `ON CONFLICT DO NOTHING` consulted before
every event insert. Alternatively, amend the spec to state that `event_id` uniqueness is
only guaranteed per-work-item, with a breadcrumb resolution note.
