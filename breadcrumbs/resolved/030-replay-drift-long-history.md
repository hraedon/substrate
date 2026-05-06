---
number: "030"
title: "Replay drift assertion on long histories"
severity: low
status: proposed
kind: improvement
author: claude-opus-4-7
via: dep-software-factory-2-replay-correctness
date: "2026-05-06"
tags: [replay, scale, correctness, sf2-readiness]
related: ["025", "003"]
---

## Problem

The scale benchmark in `tests/test_scale.py` (BC-025) measures replay throughput at ~0.46ms/event on 1,000 events (100 items × 10 events). It asserts zero drift at that scale.

SF2 spec §8.4 calls out "replay correctness on long event histories" as a may-emerge blocker. SF2 will accumulate event histories per work-item that are 10× to 100× larger than the current benchmark exercises (multi-attempt retries, multi-stage pipelines, hook events, validator events, claim/release cycles). The benchmark proves replay is *fast* at modest scale; it does not prove replay is *correct* at the scale SF2 will hit.

## Proposed work

Extend the existing replay benchmark (or add a sibling) to exercise a longer history and assert drift = 0:

- 100 work-items × 100 events each = 10,000 events.
- Mix of event kinds: transitions, claim/release, link create/remove, custom field updates, hook events.
- Run `replay(project)`, assert `drift_count == 0` and the derived state for each work-item matches the live snapshot.

The performance number remains informational; the correctness assertion is the load-bearing addition.

## Why low severity

The benchmark already asserts drift = 0 at small scale. The risk is asymptotic — a bug that surfaces only past N events — and is more theoretical than observed. But this is cheap insurance: extending the existing test is a small change, and SF2 spec §8.4 explicitly flagged it.

## Acceptance criteria

- [ ] `tests/test_scale.py` includes a benchmark with ≥10,000 events across ≥100 work-items.
- [ ] Test asserts `drift_count == 0` and per-work-item derived state matches live snapshot.
- [ ] Marked `@pytest.mark.slow` to stay out of default runs, consistent with BC-025.

## Related

- BC-025 (scale benchmarks for replay, link queries, hook throughput)
- BC-003 (drift detection completeness — resolved)
- SF2 spec §8.4 (replay correctness on long histories — may-emerge blocker)
