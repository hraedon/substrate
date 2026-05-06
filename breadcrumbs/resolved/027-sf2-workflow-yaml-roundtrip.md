---
number: "027"
title: "Round-trip SF2 workflow YAMLs through register_workflow"
severity: high
status: proposed
kind: improvement
author: claude-opus-4-7
via: dep-software-factory-2-phase-0
date: "2026-05-06"
tags: [workflows, integration, sf2-blocker, validators]
related: []
---

## Problem

Software Factory v2's `phase1.yaml` and `full_pipeline.yaml` (in `/projects/software-factory-2/workflows/`) have never been loaded into substrate. Both pin `substrate_version: "0.1.0"` and exercise substrate features in combinations the existing test suite does not:

- Multi-role `claim` transitions (10 roles in `full_pipeline.yaml`).
- `work_item_types` with `custom_fields` declaring `required: true` and `type: json` (e.g., `interface_spec.ac_ids`, `interface_spec.diagnostics`).
- `attempt_threshold: 3` driving the escalation mechanism on real workflow shapes.
- The two YAMLs as separate workflow versions (1 and 2) intended to coexist under version-pinned work-items per BC-022 / FR-13.

Whatever breaks when these YAMLs are first loaded is exactly what would break on SF2 Phase 1 day-one, and it is an order of magnitude more expensive to debug there than here.

## Proposed work

Add an integration test in substrate (e.g., `tests/test_sf2_workflows.py`) that:

1. Reads both YAMLs from `/projects/software-factory-2/workflows/`. (If cross-repo path coupling is undesirable, copy them into `tests/fixtures/` with a comment noting the upstream source.)
2. Calls `register_workflow` on each and asserts no error.
3. For `phase1.yaml`: creates an `interface_spec` work-item under v1, walks `claim → submit → gate_pass`, asserts the transition validator rejects a `submit` missing the required `artifact_path` custom field.
4. For `full_pipeline.yaml`: creates a work-item per type, asserts each declared role can claim, asserts unauthorized roles are rejected with `ROLE_NOT_PERMITTED`.
5. Registers both versions in the same project schema and asserts version pinning behaves per BC-022 (a v1 work-item cannot use a v2-only transition).

The test should fail loudly on any schema mismatch, missing field, or validator wiring gap.

## Why this is high severity

This is the only item on the pre-SF2 list that is a *strict prerequisite* for SF2 Phase 1 — SF2 cannot start without these workflows loading. Doing it now front-loads the inevitable and surfaces issues while substrate is the focus.

## Acceptance criteria

- [ ] `tests/test_sf2_workflows.py` exists and passes.
- [ ] Both YAMLs register without error.
- [ ] Custom-field validators (`required: true`) reject transitions missing required fields with `CUSTOM_FIELD_VIOLATION`.
- [ ] Role gating rejects unauthorized claims with `ROLE_NOT_PERMITTED`.
- [ ] Version pinning is exercised across the v1/v2 pair.

## Related

- SF2 BC-002 (runner skeleton complexity)
- substrate BC-022 (workflow re-registration semantics)
- spec FR-13 (version-pinned transitions)
