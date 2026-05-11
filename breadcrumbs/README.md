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

## Deferred

| 083 | No uniqueness checks on state/transition/type names | medium | [deferred/083](deferred/083-no-uniqueness-checks-on-names.md) |
| 082 | Default values not type-checked at registration | medium | [deferred/082](deferred/082-default-values-not-type-checked.md) |
| 079 | Replay skips work items with zero events silently | medium | [deferred/079](deferred/079-replay-skips-zero-event-work-items.md) |
| 074 | continue_on_revoked=True skips signature verification entirely | high | [deferred/074](deferred/074-continue-on-revoked-skips-signature.md) |
| 070 | Replay temp tables accumulate between replay() calls | low | [deferred/070](deferred/070-replay-temp-table-accumulation.md) |
| 068 | validate_field_values takes WorkflowDefinition but validate_field_update takes raw dict | low | [deferred/068](deferred/068-inconsistent-workflow-param-types.md) |
| 065 | HookConsumer nested transaction risk with append_event under savepoints | low | [deferred/065](deferred/065-hook-savepoint-deadlock.md) |

## Resolved

| # | Title | Severity | Resolution |
|---|---|---|---|
| 087 | _validators dict not copy-on-write (thread safety) | medium | `register_validator` now uses copy-on-write pattern matching `register_hook_handler` |
| 086 | validate_json_safe_value silently passes non-JSON types | medium | Added else clause raising INVALID_ARGUMENT for set, bytes, tuple, Decimal, etc. |
| 085 | close() is not idempotent | medium | Added None guard on `self._mgr`; second call is a no-op |
| 084 | Empty enum_values array accepted | medium | Added `minItems: 1` to JSON Schema for enum_values |
| 081 | check_idempotency actor_id type annotation wrong | medium | Changed `actor_id: str` to `actor_id: str \| None` |
| 080 | Idempotency check does not verify work_item_id | medium | Added `work_item_id` param to `check_idempotency`; verifies match when provided |
| 078 | InMemory requeue_dead_lettered_hook loses work_item_id | medium | Store `work_item_id` at top level in dead-letter; use it directly on requeue |
| 077 | Missing validate_ttl in resolve_claim_acquire | high | Added `validate_ttl(ttl_seconds)` at top of `resolve_claim_acquire` |
| 076 | JSON-typed custom fields bypass validate_json_safe_value | high | Added `validate_json_safe_value` call in the json branch of `_coerce_field` |
| 075 | create_project and __init__ leak connection pool on failure | high | `create_project`: try/finally; `__init__`: try/except with `mgr.close()` on failure |
| 073 | InMemory read_events returns oldest events; Postgres returns newest | high | Fixed InMemory to sort DESC, take limit, reverse (matching Postgres) |
| 072 | Replay silently swallows unrecognized transitions with custom_fields_update | critical | Only apply custom_fields_update when transition matches workflow definition |
| 071 | Heartbeat revives expired claims (zombie revival) | critical | Added expiry check to `resolve_heartbeat`; expired claims now raise CLAIM_LOST |
| 069 | __init__.py has excessive _types re-export boilerplate | low | Consolidated ~20 individual import blocks into 3 grouped blocks (`_contract`, `_events`, `_types`) |
| 067 | _contract.py has no standalone unit tests | medium | Added `tests/test_contract.py` with 85 unit tests covering all 17 pure functions |
| 066 | KeySet hot-reload TOCTOU between active_key_id check and access | low | `active_key()` now captures `keys`/`active_id` as locals before check+access |
| 063 | Add optional prompt_template_hash field to ActorMetadata | low | Added `prompt_template_hash: str | None = None` to `ActorMetadata`; round-trip via `to_dict`/`from_dict`; 5 tests in `test_actor_metadata_contract.py` |
| 062 | Single-source-of-truth backend contract — eliminate hand-maintained InMemorySubstrate parity | high | Added `_contract.py` with 20 pure validation/decision functions; both backends refactored to delegate; 5 property-based conformance tests via hypothesis (Option A + B) |
| 061 | Provide a workflow-yaml validator that does not require a live database | low | Added `validate_yaml(path_or_string) -> ValidationResult` to `_workflow.py`; exposed via `substrate.validate_yaml` and `substrate.testing.validate_yaml`; 11 tests in `test_validate_yaml.py` |
| 060 | Canonical diagnostic-payload shape for transition events | low | Accepted as documentation convention; added "Diagnostic payload shape" pattern to AGENTS.md |
| 058 | Claim lifecycle events misattribute actor_kind as "system" for actor-triggered operations | low | Added `actor_kind` param (default `"agent"`) to `acquire_claim` and `release_claim` in both backends and public API; claim events now use caller's `actor_kind` |
| 057 | Replay output table mixes replayed state with live-projection columns | low | Set `last_event_at`, `claimed_by`, `claim_expires_at` to NULL in replay output table since replay does not derive claim state |
| 056 | WorkItem dataclass excludes attempt_number despite query fetching it | low | Added `attempt_number: int = 0` field to `WorkItem`; wired through `_row_to_work_item`, `_wi_to_work_item`, `to_dict`/`from_dict` |
| 055 | update_not_before projection mutation precedes idempotency check — TOCTOU | high | Moved idempotency check before projection mutation in both backends; prevents projection corruption on duplicate event_id |
| 054 | InMemorySubstrate and Postgres transition()/release_claim reset attempt_number by deleting claim row | high | Persist `attempt_number` on `work_items_current` and `_work_items` dict; `acquire_claim` increments from work item state instead of claim entry; migration 006 |
| 053 | Add CI configuration for automated make check | medium | Added `.github/workflows/ci.yml` with Postgres service container, Python 3.11/3.12 matrix, `make check` |
| 052 | InMemorySubstrate _hook_queue grows unboundedly | low | Prunes completed/dead_lettered entries after `poll_hooks` batch processing |
| 051 | InMemorySubstrate poll_hooks fabricates nil UUID for missing work_item_id | low | [resolved/051](resolved/051-in-memory-poll-hooks-nil-uuid-fallback.md) |
| 050 | InMemorySubstrate poll_hooks does not dead-letter unregistered handlers | low | [resolved/050](resolved/050-in-memory-poll-hooks-handler-not-registered.md) |
| 049 | check_actor_role_authorized silently allows actors with zero registered roles | low | [resolved/049](resolved/049-zero-roles-bypass-check.md) |
| 048 | InMemorySubstrate poll_hooks does not track hook status or retry stuck hooks | low | [resolved/048](resolved/048-in-memory-hook-status-tracking.md) |
| 047 | Remove unused pytest-postgresql and testcontainers dev dependencies | low | Removed from `pyproject.toml`; confirmed zero imports across codebase |
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
| 035 | Telemetry-via-hooks pattern needs a concrete worked example | low | Added `examples/telemetry_via_hooks.py` and AGENTS.md pattern section linking to it |
| 034 | "No comments in code" style rule — onboarding trade-off | low | Documented convention in AGENTS.md with full rationale; spec-cross-references acceptable |
| 033 | Schema-per-project and PgBouncer transaction-mode incompatibility | medium | Documented as known constraint in AGENTS.md |
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
| 064 | Backend divergence on null-byte (\u0000) strings in JSONB fields | medium | [resolved/064](resolved/064-null-byte-string-divergence.md) |
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