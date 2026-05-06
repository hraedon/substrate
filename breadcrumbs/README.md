# Breadcrumbs

Defects, design questions, and improvements for substrate. One file per item, numbered for reference. Numbers do not imply priority order — see `severity` in each file's frontmatter.

## Schema

```yaml
---
number: "001"
title: Short descriptive title
severity: critical | high | medium | low
status: proposed | in_progress | implemented | obsolete
kind: bug | design | improvement
author: who-raised-it
date: "YYYY-MM-DD"
tags: [topic, fr-XX, ac-NN]
related: ["002", "003"]
---
```

## Severity

- **critical** — blocks correct operation; substrate cannot be trusted for stated guarantees
- **high** — load-bearing spec property unfulfilled; silent-correctness risk
- **medium** — defect with workaround or limited blast radius
- **low** — edge case, polish, or minor API ergonomics

## Open

| # | Title | Severity | Status |
|---|---|---|---|
| 033 | Schema-per-project incompatible with PgBouncer transaction mode | medium | proposed |
| 034 | "No comments in code" style rule creates onboarding cliff | low | proposed |
| 035 | Telemetry-via-hooks pattern needs a concrete worked example | low | proposed |
| 036 | External Postgres as a backend — adapter abstraction | medium | proposed |

## Resolved

| # | Title | Severity | Resolution |
|---|---|---|---|
| 001 | Replay does not verify signatures or check key status | high | [resolved/001](resolved/001-replay-no-signature-verification.md) |
| 002 | Replay output table contains live snapshot, not derived state | medium | [resolved/002](resolved/002-replay-table-live-snapshot.md) |
| 003 | Drift detection compares only current_state and last_event_seq | high | [resolved/003](resolved/003-drift-detection-incomplete.md) |
| 004 | Idempotency silently accepts different payloads under same event_id | medium | [resolved/004](resolved/004-idempotency-silent-mismatch.md) |
| 005 | Claim mutations do not emit events | high | [resolved/005](resolved/005-claims-emit-no-events.md) |
| 006 | Heartbeat does not check attempt_number for stolen-by-self | medium | [resolved/006](resolved/006-heartbeat-attempt-number.md) |
| 007 | idempotency_key parameter accepted but ignored on several mutations | medium | Hybrid: dropped from register_workflow (natural key on name,version); renamed to event_id on acquire_claim/release_claim/create_link/remove_link; all wired through to _events.append dedup |
| 008 | Signing scheme does not deliver jsonb-drift survival promised by FR-15 | high | Option A: spec FR-15 amended to store canonical envelope bytes; added canonical_envelope BYTEA column; verify_event uses stored bytes, not jsonb re-serialization. AC-26 test now non-vacuous |
| 009 | JCS implementation has edge-case correctness gaps | medium | Swapped in `rfc8785` library (PyPI); 16 edge-case tests covering float boundaries, integer domain, UTF-16 key ordering, determinism, NFC caveat |
| 016 | Pagination over moving last_event_seq target can skip or duplicate | low | Changed to stable cursor by `work_item_id` only; pagination-stability test added |
| 017 | Test coverage missing for load-bearing ACs | high | 81 tests + 3 benchmarks across 9 files covering AC-17, AC-24, AC-25, AC-26, AC-28, AC-29, AC-33, AC-34 and Phase 2 ACs |
| 018 | Tests reach into private _mgr attribute for out-of-band SQL | low | Created `substrate._testing` module centralizing `_mgr` coupling; all test files import from it |
| 019 | Session-scoped smoke test fixture accumulates state across tests | low | Switched to module-scoped fixture with DROP SCHEMA teardown via `_testing.drop_project_schema`, matching pattern in other test files |
| 020 | Escalation metric placement requires extra DB read | low | `_check_escalation` returns bool; `acquire_claim` returns `tuple[Claim, bool]`; no extra `get_work_item` read; documented `Literal` usage for NOTIFY |
| 021 | Hook consumer swallows all exceptions, no reconnect | medium | Catch `psycopg.OperationalError` specifically; exponential backoff reconnection with max attempts; `threading.Event` replaces bare `bool`; documented `Literal` for NOTIFY payload |
| 022 | Workflow re-registration is idempotent but spec says reject | medium | Content-based idempotency: same content returns existing, different content raises `WORKFLOW_VERSION_CONFLICT`. Migration 004 adds `content_hash BYTEA`. Spec §8 amended per BC-022 |
| 023 | Optional payload JSONB on links | low | Added `payload: dict | None` to `Link` dataclass and `create_link()` API; stored in `link_created` event JSONB; no migration needed |
| 024 | Document the telemetry-via-hooks pattern | low | Added "Patterns > Telemetry via hooks" section to AGENTS.md |
| 025 | Scale benchmarks for replay, link queries, and hook throughput | medium | Added `tests/test_scale.py` with 3 benchmarks marked `@pytest.mark.slow`; baseline: ~0.46ms/event replay, ~3ms link query, ~914 hooks/sec drain |
