# Breadcrumbs

Defects, design questions, and improvements for substrate. One file per item, numbered for reference. Numbers do not imply priority order — see `severity` in each file's frontmatter.

## Schema

```yaml
---
number: "001"
title: Short descriptive title
severity: critical | high | medium | low
status: proposed | in_progress | implemented | accepted | obsolete
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
| 052 | InMemorySubstrate _hook_queue grows unboundedly | low | proposed |
| 051 | InMemorySubstrate poll_hooks fabricates nil UUID for missing work_item_id | low | proposed |
| 053 | Add CI configuration for automated make check | medium | proposed |

## Resolved

| # | Title | Severity | Resolution |
|---|---|---|---|
| 049 | check_actor_role_authorized silently allows actors with zero registered roles | low | [resolved/049](resolved/049-zero-roles-bypass-check.md) |
| 048 | InMemorySubstrate poll_hooks does not track hook status or retry stuck hooks | low | [resolved/048](resolved/048-in-memory-hook-status-tracking.md) |
| 047 | Stuck hook recovery could cause double-processing | low | [resolved/047](resolved/047-stuck-hook-double-processing.md) |
| 045 | InMemorySubstrate accepts but silently ignores hmac_key_path | medium | [resolved/045](resolved/045-in-memory-substrate-ignores-hmac-key-path.md) |
| 044 | Test suite still imports drop_project_schema from substrate._testing | low | [resolved/044](resolved/044-test-suite-imports-drop-project-schema-from-private-module.md) |
| 043 | read_events composite filter ordering semantics are undocumented | low | [resolved/043](resolved/043-read-events-composite-ordering-semantics.md) |
| 042 | Expose Substrate DSN (or equivalent) as public API | medium | `Substrate.connection_info` property implemented and stable; returns `ConnectionInfo(host, port, database, project)` |
| 041 | Conformance tests missing coverage for claim event actor_id, dead-letter, replay drift, hook consumer | medium | [resolved/041](resolved/041-conformance-coverage-gaps.md) |
| 040 | InMemorySubstrate read_events composited filters; real Substrate is mutually exclusive | medium | [resolved/040](resolved/040-in-memory-read-events-filter-semantics.md) |
| 039 | register_actor_role should be idempotent by default | low | Duplicate registration now no-op in both backends; SF2 try/except wrappers removed |
| 038 | Ship first-class test fixtures / in-memory backend for downstream consumers | high | [resolved/038](resolved/038-in-memory-test-fixtures.md) |
| 037 | work_item_ref fields accept any UUID — no existence or type enforcement at runtime | high | [resolved/037](resolved/037-work-item-ref-no-runtime-validation.md) |
| 036 | External Postgres deployment guide | n/a | [resolved/036](resolved/036-external-postgres-deployment.md) |
| 032 | Spec-to-Code-to-Test Alignment Audit | n/a | [resolved/032](resolved/032-spec-alignment-audit.md) |
| 031 | Error-Path Coverage Sweep | n/a | [resolved/031](resolved/031-error-path-coverage-sweep.md) |
| 030 | Replay drift assertion on long histories | low | [resolved/030](resolved/030-replay-drift-long-history.md) |
| 029 | Hook-miss recovery: documented event-since-cursor primitive | medium | [resolved/029](resolved/029-hook-miss-recovery-cursor.md) |
| 028 | Document and type the actor_metadata contract | medium | [resolved/028](resolved/028-actor-metadata-contract.md) |
| 027 | Round-trip SF2 workflow YAMLs through register_workflow | high | [resolved/027](resolved/027-sf2-workflow-yaml-roundtrip.md) |
| 026 | Dead error codes: defined but never raised | low | [resolved/026](resolved/026-dead-error-codes.md) |
| 025 | Scale benchmarks for replay, link queries, and hook throughput | medium | Added `tests/test_scale.py` with 3 benchmarks marked `@pytest.mark.slow`; baseline: ~0.46ms/event replay, ~3ms link query, ~914 hooks/sec drain |
| 024 | Document the telemetry-via-hooks pattern | low | Added "Patterns > Telemetry via hooks" section to AGENTS.md |
| 023 | Optional payload JSONB on links | low | Added `payload: dict | None` to `Link` dataclass and `create_link()` API; stored in `link_created` event JSONB; no migration needed |
| 022 | Workflow re-registration is idempotent but spec says reject | medium | Content-based idempotency: same content returns existing, different content raises `WORKFLOW_VERSION_CONFLICT`. Migration 004 adds `content_hash BYTEA`. Spec §8 amended per BC-022 |
| 021 | Hook consumer swallows all exceptions, no reconnect | medium | Catch `psycopg.OperationalError` specifically; exponential backoff reconnection with max attempts; `threading.Event` replaces bare `bool`; documented `Literal` for NOTIFY payload |
| 020 | Escalation metric placement requires extra DB read | low | `_check_escalation` returns bool; `acquire_claim` returns `tuple[Claim, bool]`; no extra `get_work_item` read; documented `Literal` usage for NOTIFY |
| 019 | Session-scoped smoke test fixture accumulates state across tests | low | Switched to module-scoped fixture with DROP SCHEMA teardown via `_testing.drop_project_schema`, matching pattern in other test files |
| 018 | Tests reach into private _mgr attribute for out-of-band SQL | low | Created `substrate._testing` module centralizing `_mgr` coupling; all test files import from it |
| 017 | Test coverage missing for load-bearing ACs | high | 81 tests + 3 benchmarks across 9 files covering AC-17, AC-24, AC-25, AC-26, AC-28, AC-29, AC-33, AC-34 and Phase 2 ACs |
| 016 | Pagination over moving last_event_seq target can skip or duplicate | low | Changed to stable cursor by `work_item_id` only; pagination-stability test added |
| 015 | Replay matches transitions by name only, not (name, from_state) | medium | [resolved/015](resolved/015-replay-name-only-match.md) |
| 014 | remove_link does not validate that the link exists | low | [resolved/014](resolved/014-remove-link-no-existence-check.md) |
| 013 | has_link_type filter does not account for link_removed events | medium | [resolved/013](resolved/013-has-link-type-ignores-removal.md) |
| 012 | Event.timestamp returned to caller differs from server-side stored value | low | [resolved/012](resolved/012-event-timestamp-mismatch.md) |
| 011 | Event dataclass missing workflow_name field | low | [resolved/011](resolved/011-event-missing-workflow-name.md) |
| 010 | append_event allows arbitrary transition strings, bypassing FR-11/FR-12 | high | [resolved/010](resolved/010-append-event-bypasses-validation.md) |
| 009 | JCS implementation has edge-case correctness gaps | medium | Swapped in `rfc8785` library (PyPI); 16 edge-case tests covering float boundaries, integer domain, UTF-16 key ordering, determinism, NFC caveat |
| 008 | Signing scheme does not deliver jsonb-drift survival promised by FR-15 | high | Option A: spec FR-15 amended to store canonical envelope bytes; added canonical_envelope BYTEA column; verify_event uses stored bytes, not jsonb re-serialization. AC-26 test now non-vacuous |
| 007 | idempotency_key parameter accepted but ignored on several mutations | medium | Hybrid: dropped from register_workflow (natural key on name,version); renamed to event_id on acquire_claim/release_claim/create_link/remove_link; all wired through to _events.append dedup |
| 006 | Heartbeat does not check attempt_number for stolen-by-self | medium | [resolved/006](resolved/006-heartbeat-attempt-number.md) |
| 005 | Claim mutations do not emit events | high | [resolved/005](resolved/005-claims-emit-no-events.md) |
| 004 | Idempotency silently accepts different payloads under same event_id | medium | [resolved/004](resolved/004-idempotency-silent-mismatch.md) |
| 003 | Drift detection compares only current_state and last_event_seq | high | [resolved/003](resolved/003-drift-detection-incomplete.md) |
| 002 | Replay output table contains live snapshot, not derived state | medium | [resolved/002](resolved/002-replay-table-live-snapshot.md) |
| 001 | Replay does not verify signatures or check key status | high | [resolved/001](resolved/001-replay-no-signature-verification.md) |
