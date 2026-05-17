---
number: "172"
title: rfc8785 library is critical single point of failure for signature integrity
severity: medium
status: proposed
kind: design
author: security-audit
date: "2026-05-17"
tags: [security, crypto, signing, dependency, supply-chain]
related: ["009"]
---

## Observation

The `rfc8785` library (version 0.1.4) at `_jcs.py:8-9` is the sole implementation of RFC 8785 canonicalization used for HMAC signing envelope construction. Every event signature in the system depends on this library producing correct, deterministic output.

If `rfc8785` has a bug in edge-case serialization (e.g., float boundaries, Unicode normalization edge-cases, integer domain overflow), every signature produced by substrate would be non-verifiable. In a worse case, incorrect canonicalization could make forged events verifiable.

Key risk factors:
- `rfc8785` is a niche single-purpose library with one maintainer.
- Version 0.1.4 — pre-1.0, no stability guarantee.
- The JCS test suite at `tests/test_jcs.py` provides good coverage of known edge cases but cannot prove absence of bugs in the upstream library.
- No secondary canonicalization implementation exists as a cross-check (defense-in-depth).

Existing BC-009 replaced a homegrown JCS implementation with this library, which was the correct move. This breadcrumb tracks the residual risk.

## Mitigation Present

`tests/test_jcs.py` (131 lines) covers float boundaries, integer domains, key ordering, Unicode normalization, and determinism — providing a strong harness around the dependency.

## Proposed

- Pin to a specific `rfc8785` version hash rather than a floating `>=` constraint to prevent silent upgrades.
- Consider vendoring `rfc8785` (it is small — single module) to eliminate supply-chain risk.
- Consider a cross-validation mode: run an independent canonicalization implementation alongside and compare output on every sign/verify call (performance cost is minimal — only on mutation paths).
- Monitor `rfc8785` for CVEs and breaking changes.
