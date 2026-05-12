---
number: "136"
title: InMemory read_events sort order diverges from Postgres for time-range queries
severity: medium
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-12"
resolved_date: "2026-05-12"
tags: [in-memory, read-events, conformance]
related: []
---

## Problem

InMemory `read_events()` returned descending order for actor_id + time-range queries and was missing event_seq tiebreaker for time-range-only queries. Postgres uses ascending ORDER BY for time-range queries and descending for all others.

## Resolution

Fixed actor_id branch to use ascending sort when start/end is provided, matching Postgres. Added event_seq tiebreaker to time-range-only sort.
