---
number: "025"
title: Scale benchmarks for replay, link queries, and hook throughput
severity: medium
status: resolved
kind: improvement
author: claude-opus-4-7
date: "2026-05-05"
tags: [testing, performance, replay, hooks, links]
related: []
---

## Problem

Current substrate tests exercise modest scales: tens of events per work-item, tens of work-items, a handful of links per item, sporadic hook traffic. The library's three highest-leverage operations — `replay()`, link queries via `has_link_type`, and hook consumer drain rate — are all asymptotically vulnerable in ways the current test suite does not surface.

## Resolution

Added `tests/test_scale.py` with three informational benchmarks marked `@pytest.mark.slow` (excluded from default test runs via `-m "not slow"`):

1. **Replay benchmark** (100 items x 10 events = 1000 total): ~0.46s wall-clock, ~0.46ms/event, zero drift.
2. **Link-query benchmark** (50 items x 5 links = 250 live links, 10 queries): ~3ms/query.
3. **Hook drain benchmark** (500 hooks, no-op handler): ~0.55s, ~914 hooks/sec.

All pass criteria are assertional (zero drift, correct counts). Performance numbers are informational baselines for future comparison. `pyproject.toml` updated with `slow` marker registration.
