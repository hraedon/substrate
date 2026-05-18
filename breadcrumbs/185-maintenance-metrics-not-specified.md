---
number: "185"
title: Maintenance metrics not specified in Plan 009 — operator blind to sweeps
severity: medium
status: proposed
kind: improvement
author: kimi-k2p6-turbo
date: "2026-05-18"
tags: [observability, metrics, maintenance, plan-009]
related: ["184"]
---

# BC-185 — Maintenance metrics not specified in Plan 009

## Problem

Plan 009 (Operational Runtime) proposes a `MaintenanceThread` that runs `sweep_expired_claims`, `sweep_expired_hook_leases`, `ensure_event_partitions`, and `fire_due_recurrences` on configurable intervals. The plan mentions `substrate_maintenance_errors_total` but does not specify operational counters that let an operator verify the thread is doing work.

Without per-operation counters, an operator cannot distinguish between:
- "Maintenance is running and there is nothing to do" (healthy)
- "Maintenance thread died and is not running at all" (unhealthy)

## Proposed fix

Specify and implement the following Prometheus counters for the maintenance thread:

| Counter | Description |
|---|---|
| `substrate_maintenance_cycles_total` | Maintenance loop iterations completed |
| `substrate_maintenance_claims_swept_total` | Claims expired and cleared |
| `substrate_maintenance_hook_leases_swept_total` | Stranded hook leases recovered |
| `substrate_maintenance_partitions_created_total` | Event partitions created |
| `substrate_maintenance_recurrences_fired_total` | Recurring work-items created |

Additionally, expose a boolean property:

```python
@property
def maintenance_healthy(self) -> bool:
    """True if the maintenance thread is running and its last cycle succeeded."""
```

## Acceptance criteria

1. All counters above are visible in Prometheus output after `start_maintenance()` is called.
2. `maintenance_healthy` returns `False` if the thread has crashed or the last cycle raised an unhandled exception.
3. InMemory backend emits equivalent structured log lines (no Prometheus registry required).

## Resolution

_(pending implementation or rejection)_
