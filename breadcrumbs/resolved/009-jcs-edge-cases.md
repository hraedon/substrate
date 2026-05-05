---
number: "009"
title: JCS implementation has edge-case correctness gaps for floats and supplementary chars
severity: medium
status: resolved
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [signing, jcs, audit, fr-15]
related: ["008"]
---

## Problem

`_jcs.py` implements RFC 8785 (JCS) but has known correctness gaps:

1. **Number serialization** uses Python `repr(float)` with a small fix-up. ECMAScript `Number.prototype.toString` (which RFC 8785 specifies) differs at edges: very small floats (`< 1e-6` switches to scientific in ECMAScript; Python's threshold is different), large exponents, integers above `2^53` (Python ints are unbounded; ECMAScript loses precision and renders differently).

2. **Object key sort** uses Python `sorted` (UTF-32 codepoint order). RFC 8785 specifies UTF-16 code unit order. The difference matters for supplementary-plane characters (above U+FFFF — emoji, less common scripts) where surrogate pairs sort differently than their codepoints.

3. **String escaping** is correct for control chars but doesn't normalize Unicode. RFC 8785 implicitly requires NFC; non-NFC strings could produce different canonical bytes after a round-trip through some Postgres pipelines.

## Resolution

Swapped in `rfc8785` PyPI library replacing hand-rolled implementation. Edge-case test suite added in `tests/test_jcs.py` (16 tests) verifying:

- **Float boundaries**: 1e-7 (scientific), 1e-6 (decimal), 1e20 (integer form), 1e21 (scientific), 0.1+0.2 (precision), 1.0→1 (integer), -0.0→0 (normalized)
- **Integer domain**: safe integers (2^53-1) pass; unsafe integers (2^53, 2^64) raise `IntegerDomainError`
- **Key ordering**: ASCII sorted correctly; supplementary chars use UTF-16 code unit order; nested objects sorted recursively
- **Determinism**: same input → same output; JSON round-trip stable
- **NFC caveat**: NFC and NFD forms produce different canonical bytes (documented, not normalized by library). In practice, Postgres JSONB stores strings in NFC, so this is not an issue for substrate payloads. NFC round-trips are stable.
