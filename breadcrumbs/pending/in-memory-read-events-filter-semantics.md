---
number: "pending"
title: InMemorySubstrate read_events composits filters; real Substrate is mutually exclusive
severity: medium
status: draft
kind: bug
author: glm-5.1
date: "2026-05-07"
origin: validation scan of Deepseek session 10 work
tags: [in-memory, conformance, api-contract]
related: ["038"]
---

## Observation

The real `Substrate.read_events` documents and enforces "exactly one filter dimension" — calling with `work_item_id` ignores `transition`, `actor_id`, etc. The `InMemorySubstrate.read_events` composits all provided filters (e.g., `read_events(work_item_id=X, transition="fail")` narrows by both). This divergence means the in-memory backend is more capable than the real one, which is a foot-gun: code tested against InMemorySubstrate that uses composite filters will silently break against Postgres.

The ordering also differs: real Substrate returns DESC for `work_item_id` (then reverses for the default case), DESC for `actor_id`/`transition`, ASC for time-range; InMemory now matches this after the fix in this session, but it was previously wrong.

## Proposed

Option A (recommended): Make InMemorySubstrate enforce the same mutual-exclusivity contract as the real Substrate. If multiple filter dimensions are provided, only apply the first matching one (matching the priority order in `__init__.py`). This makes the in-memory backend a strict conformance fixture.

Option B: Document the divergence and accept it.

## Why medium severity

Medium because it's a conformance gap that can cause production breakage for downstream consumers who test against InMemorySubstrate. Not critical because the real Substrate is the production path and it works correctly — the risk is false confidence from in-memory tests.