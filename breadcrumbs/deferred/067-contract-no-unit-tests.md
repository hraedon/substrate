---
number: "067"
title: _contract.py has no standalone unit tests
severity: medium
status: deferred
kind: improvement
author: deepseek-v4-pro
date: "2026-05-11"
tags: [contract, testing, coverage]
related: ["062"]
---

## Context

`_contract.py` contains 21 pure functions extracted in RFC-062. All are tested
implicitly through existing integration tests and property-based conformance
tests, but no standalone unit tests exist for edge cases.

## Risk

Boundary conditions (e.g., `resolve_claim_acquire` with `claim_attempt_number=0`
vs `None`, negative TTL boundary in `validate_ttl`, empty dict/lists in
`validate_json_safe_value`) are only tested if integration/property coverage
happens to reach them.

## Options

- Add `tests/test_contract.py` with dedicated edge-case tests for each function
- Accept that property-based conformance + integration tests provide sufficient
  coverage for the current phase
