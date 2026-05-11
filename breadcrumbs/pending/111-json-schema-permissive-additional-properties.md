---
number: "111"
title: JSON Schema permits additionalProperties:true everywhere — workflow isolation unclear
severity: medium
status: proposed
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, workflow, fr-17]
related: []
---

## Description

`_workflow.py:50-60` validates workflow YAML against JSON Schema using `Draft202012Validator`. The schema at `_workflow_schema.json` may permit `additionalProperties: true` in many places, allowing workflows to define arbitrary extra fields that are not validated.

A workflow with extra fields could potentially:
1. Define transitions that grant more permissions than the schema strictly shows
2. Define "validator" or "hook" names that match system-reserved names
3. Add metadata that could confuse downstream consumers

## Evidence

- `_workflow.py:50`: `jsonschema.Draft202012Validator(schema)`
- `_workflow_schema.json`: loaded from file; contents not reviewed in detail
- No schema lock or pinning: any valid JSON Schema passes validation

## Impact

- A malformed workflow could define behavior that conflicts with other workflows in the same project
- If `additionalProperties: true` is used broadly, the schema doesn't actually constrain workflows as much as intended
- Downstream tooling that relies on schema validation might be surprised by extra fields

## Fix

1. Review `_workflow_schema.json` and set `additionalProperties: false` where extra fields serve no purpose
2. Add `unevaluatedProperties: false` (Draft 2019-09+) to transition and state objects
3. Document which extra fields are permitted (if any) and why

## Notes

This requires reviewing the actual schema file. The schema may already be well-constrained. This is a call for audit rather than a confirmed issue.