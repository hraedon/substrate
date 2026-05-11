---
number: "064"
title: Backend divergence on null-byte (\u0000) strings in JSONB fields
severity: medium
status: resolved
kind: bug
author: deepseek-v4-pro
date: "2026-05-11"
tags: [contract, conformance, in-memory, postgres]
related: ["062"]
---

## Context

Property-based conformance test (`test_random_sequences_equivalent`) found that
`InMemorySubstrate` silently accepts strings containing `\u0000`, while the
Postgres backend rejects them via JSONB's `UntranslatableCharacter` error.

## Root cause

`_contract.py` had no shared string-safety validation.  Custom field string
values flow through `_coerce_field()` in `_workflow.py`, which checked only
`isinstance(value, str)` but didn't validate character safety.  The InMemory
backend stores strings directly in Python dicts with no encoding constraints,
while Postgres JSONB enforces Unicode well-formedness (rejecting `\u0000`).

## Resolution

Added `validate_json_safe_string()` to `_contract.py` and called it from
`_coerce_field()` in `_workflow.py` for string-typed custom fields.  This
makes both backends consistently reject `\u0000` at the shared validation
layer, preventing the conformance divergence.

## Files changed

- `src/substrate/_contract.py`: added `validate_json_safe_string()`
- `src/substrate/_workflow.py`: imported and called it in `_coerce_field()`
