---
number: "017"
title: Test coverage missing for load-bearing ACs
severity: high
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [testing, ac-17, ac-24, ac-26, ac-28, ac-29, ac-33, ac-34]
related: ["001", "002", "003", "004", "008"]
---

## Problem

`tests/test_smoke.py` covers happy paths only (20 tests). The load-bearing ACs that distinguish substrate from "ad-hoc Postgres tables" have no coverage:

| AC | Property | Status |
|---|---|---|
| AC-17 | Replay halts on revoked-key event | No test (and BC-001 — feature unimplemented) |
| AC-24 | Idempotent retry returns original; collision-with-different-payload rejected | Partial: `test_event_idempotency` checks happy-path; no mismatch test (BC-004) |
| AC-25 | `expected_event_seq` mismatch rejection | No test |
| AC-26 | Re-verify after simulated jsonb formatting change | No test (and BC-008 — design unresolved) |
| AC-28 | Concurrent `event_seq` allocation under contention is gap-free | No test — the property test the spec explicitly calls out |
| AC-29 | Direct `UPDATE work_items_current` outside substrate detected as drift | No test (and BC-003 — drift detection incomplete) |
| AC-33 | Pre-signed event rejection at the public API | No test (library-as-sole-signer is structurally enforced but not asserted) |
| AC-34 | Static inspection that no Postgres types leak across the API | No test |

Several of these would have caught the BC-001/002/003/004/008/010 defects at development time. Happy-path coverage doesn't exercise any of the audit/replay/idempotency/concurrency machinery that's the spec's reason for existing.

## Spec reference

§11 Acceptance Criteria — full list. The eight ACs above are flagged as load-bearing in the original review.

## Location

`tests/test_smoke.py` — extend or split into focused suites:
- `tests/test_concurrency.py` — AC-28 property test
- `tests/test_signing.py` — AC-26 jsonb-drift simulation
- `tests/test_replay.py` — AC-17 (revoked key), AC-29 (out-of-band edit drift)
- `tests/test_idempotency.py` — AC-24 mismatch, AC-25 expected_seq
- `tests/test_api_surface.py` — AC-33 pre-signed rejection, AC-34 import inspection

## Suggested fix

Order matters here. AC-28 (concurrency) and AC-26 (signing) are independent and can be authored alongside fixes for BC-001/002/003. AC-34 is a static check that costs ~20 lines. AC-33 requires deciding *how* a caller would even attempt to submit a pre-signed event — the public API doesn't accept signature/canonical_hash parameters today, so the test asserts the absence (that no such parameter exists in the public method signatures, equivalent to AC-34's static check).

For AC-28, use `psycopg`'s thread-safe pool with N=20–50 worker threads each appending to the same work-item; assert that resulting `event_seq` values are gap-free 1..N*K.
