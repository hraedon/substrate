---
number: "009"
title: JCS implementation has edge-case correctness gaps for floats and supplementary chars
severity: medium
status: implemented
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

Real-world impact for substrate's typical payloads (string keys, simple values) is small — but the canonical hash underwrites an audit-trail promise. The promise is on shaky footing for any payload containing floats, large ints, or non-BMP keys.

## Spec reference

- FR-15 (RFC 8785 JCS canonical envelope)
- AC-26 (re-verification stability)

## Location

`src/substrate/_jcs.py` — `_serialize_number`, `_serialize_object`, `_serialize_string`

## Suggested fix

Two paths:

1. **Swap in a vetted JCS library.** `rfc8785` (PyPI) is reasonable; verify against the RFC test vectors. Removes the maintenance and audit burden.

2. **Constrain payloads to a JCS-safe subset.** Document a payload restriction: no floats (use string-encoded decimals or ints with declared scale), ASCII-or-BMP keys only, NFC strings only. Validate at signing time, reject violators.

Recommendation: option (1). The cost of a vendored library is negligible compared to maintaining a correct JCS implementation. Pairs with BC-008 — both bear on the audit-trail integrity promise.
