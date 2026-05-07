---
number: "pending"
title: Provide a workflow-yaml validator that does not require a live database
severity: low
status: draft
kind: improvement
author: claude-opus-4-7
date: "2026-05-07"
origin: software-factory-2 Phase 2 planning review
tags: [api-ergonomics, ci, downstream-consumer]
---

## Observation

To verify that a workflow YAML parses and registers cleanly, software-factory-2 must create a real substrate project (full migration run, real DB connection, register, then drop). SF2's Phase 2 plan adds `tests/test_phase2_workflow_roundtrip.py` doing exactly this as a CI regression guard. Every consumer authoring workflows will replicate this pattern.

## Proposed

Ship `substrate.workflow.validate_yaml(path) -> ValidationResult` as a pure-Python validator: schema check, transition-graph well-formedness (no orphan states, terminal states actually terminal, every transition's `from`/`to` exist), ref-target validation (`work_item_ref` `target_work_item_type` resolves to a defined type), `allowed_roles` reference defined roles.

No DB dependency. Suitable for CI lint pipelines and pre-commit hooks.

## Why low severity

Workaround (real-DB round-trip) works. But it's slow, requires docker-compose in CI, and discourages running the check often. A pure validator runs in milliseconds and shifts the feedback loop from "CI tells you" to "your editor / pre-commit tells you."

Bonus: a public validator gives substrate a hook for documenting the workflow YAML schema beyond code-as-spec.
