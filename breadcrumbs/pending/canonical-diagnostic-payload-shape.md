---
number: "pending"
title: Canonical diagnostic-payload shape for transition events
severity: low
status: draft
kind: design
author: claude-opus-4-7
date: "2026-05-07"
origin: software-factory-2 Phase 2 planning review
tags: [event-schema, observability, downstream-consumer]
related: ["028"]
---

## Observation

Software-factory-2 invented a `payload = {"diagnostics": {gate_name, passed, messages, message, diagnostic_kind, target_role}}` shape on `gate_fail` and `channel_fail` transition events. It's load-bearing for SF2's failure-summary derivation and router dispatch. Every other substrate consumer that emits failure-bearing transitions will invent its own shape, and those shapes will be incompatible at the telemetry layer.

This parallels BC-028's `actor_metadata` contract: substrate doesn't *enforce* a shape, but having a canonical recommendation prevents fragmentation across consumers.

## Proposed

Document a canonical diagnostic payload shape in substrate's API guide (not necessarily code-enforced). Suggested shape, drawn from SF2's experience:

```python
payload = {
    "diagnostics": {
        "kind": str,         # consumer-defined enum value
        "summary": str,      # one-line human-readable
        "messages": list[str],  # detailed lines
        "context": dict,     # consumer-specific structured data
    }
}
```

Then each consumer extends `kind` and `context` for its domain. SF2's `DiagnosticKind` enum is the model.

## Why low severity

Documentation-only initially. Becomes more important as substrate gains a second major consumer; if telemetry tooling is ever built atop substrate's event log (e.g., the cross-consumer pass-rate reporter SF2 will build in Phase 2 Wave 8), incompatible payload shapes become real friction.
