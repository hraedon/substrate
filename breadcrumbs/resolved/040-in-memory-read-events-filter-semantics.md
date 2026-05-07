---
number: "040"
title: InMemorySubstrate read_events composited filters; real Substrate is mutually exclusive
severity: medium
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-07"
origin: validation scan of Deepseek session 10 work
tags: [in-memory, conformance, api-contract]
related: ["038"]
---

## Observation

The real `Substrate.read_events` documents and enforces "exactly one filter dimension" — calling with `work_item_id` ignores `transition`, `actor_id`, etc. The `InMemorySubstrate.read_events` composited all provided filters (e.g., `read_events(work_item_id=X, transition="fail")` narrows by both). This divergence means the in-memory backend is more capable than the real one, which is a foot-gun: code tested against InMemorySubstrate that uses composite filters will silently break against Postgres.

## Resolution

Fixed in session 12. InMemorySubstrate `read_events` now uses priority-based matching (work_item_id > actor_id > start/end > transition) matching the real Substrate. Also fixed InMemorySubstrate to store `wf.to_dict()` instead of raw YAML dict, eliminating the `from`/`to` vs `from_state`/`to_state` key divergence in transition lookups, state assignment, and replay.
