---
number: "152"
title: "Workflow content hash includes raw_yaml, making whitespace/formatting break idempotency"
severity: high
status: implemented
resolution: "Both `compute_content_hash` and `compute_content_hash_from_dict` now pop `raw_yaml` from the dict before JCS canonicalization."
kind: bug
author: agent
date: "2026-05-15"
tags: [workflow, idempotency, fr-17]
related: []
---

## Problem

`build_definition` stores the raw YAML string in `WorkflowDefinition.raw_yaml`.
`compute_content_hash` SHA-256s the entire `wf.to_dict()`, which includes `raw_yaml`.
Therefore, two logically identical workflow files with different whitespace or comments
produce different content hashes. `register_workflow` then rejects the second with
`WORKFLOW_VERSION_CONFLICT` instead of recognizing idempotency.

The spec FR-17 says: *"Content-based idempotency: re-registration of the same `(name, version)`
with identical content (SHA-256 of JCS-canonicalized definition)"*. Identical logical content
should hash identically.

## Impact

Reformatting a workflow YAML (e.g., running a linter or renaming a key) breaks content-based
idempotency, causing unnecessary version conflicts or duplicate registrations.

## Files / Lines

- `src/substrate/_workflow.py` (~457-464)
- `src/substrate/__init__.py` (~394-424)

## Fix

Remove `raw_yaml` from the dict passed to `canonicalize` in `compute_content_hash`, or
compute the hash solely from the structured data fields (states, transitions, types, roles, etc.).
