---
number: "151"
title: "recurrence_fires_total metric emitted but has no Metrics.inc definition, so fires are silently uncounted"
severity: high
status: implemented
resolution: "Added `recurrence_fires_total` to the counters dict in `Metrics.inc` with Prometheus name `substrate_recurrence_fires_total`."
kind: bug
author: agent
date: "2026-05-15"
tags: [recurrence, observability, fr-28]
related: []
---

## Problem

`_recurrence.py` calls `metrics.inc("recurrence_fires_total", project)`. The `Metrics.inc`
method constructs a `counters` dict that does **not** contain `"recurrence_fires_total"`,
so it falls through to:

```python
else:
    log.warning("metrics.unknown_counter", name=name)
```

The recurrence fire count is therefore never emitted to Prometheus. Recurrence health is
unobservable, violating the operational expectation that production features have metrics.

## Impact

Operators cannot set alerts on recurrence schedule health, detect stuck schedulers, or
observe fire rates. This is a production-readiness gap for FR-28.

## Files / Lines

- `src/substrate/_observability.py` (~28-106)
- `src/substrate/_recurrence.py` (~299)

## Fix

Add `"recurrence_fires_total": ("substrate_recurrence_fires_total", "Recurrence fires")`
to the `counters` dict in `Metrics.inc`, and add a corresponding Prometheus counter
export in `Metrics._prom_report`.
