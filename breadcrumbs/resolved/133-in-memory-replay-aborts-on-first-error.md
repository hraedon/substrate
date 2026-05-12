---
number: "133"
title: InMemory replay aborts on first error instead of per-work-item error handling
severity: high
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-12"
resolved_date: "2026-05-12"
tags: [in-memory, replay, conformance]
related: []
---

## Problem

InMemory `replay()` had no try/except around individual work items. Any error (signature failure, state violation, missing workflow) propagated and aborted the entire replay, returning no report. Postgres replay catches errors per work item, increments `halted_count`, and continues.

InMemory also silently skipped unrecognized transitions and missing workflows instead of raising REPLAY_HALTED like Postgres.

## Resolution

Wrapped per-work-item replay logic in try/except catching SubstrateError and generic Exception, incrementing halted count. Added REPLAY_HALTED raises for missing workflow definitions and state-machine violations (transition name exists but wrong from_state), matching Postgres behavior.
