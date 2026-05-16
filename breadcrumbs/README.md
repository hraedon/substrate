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

_(none)_

## Open

_(none)_

## Resolved

| # | Title | Severity | Resolution |
|---|---|---|---|
| 170 | `register_workflow_file` double-reads file when no `extends:` | low | Hoisted `raw_text = p.read_text()` before the branch; single read in both backends. |
| 169 | Sidecar `fire_recurrence`/`cancel_recurrence_rule`/`requeue_dead_lettered_hook` use raw `dict` body — no input validation | high | Created typed Pydantic models (`FireRecurrenceRequest`, `RequeueDeadLetteredHookRequest`); added `rule_id` to `CancelRecurrenceRuleRequest`; updated routes. |
| 168 | Sidecar `list_recurrence_rules` and `list_actor_roles` drop filter parameters | high | Both routes now read `status`/`actor_id` from query params and pass through to core API. |
| 167 | `claim_hooks` marks all rows `in_progress` before filtering — hooks with missing `work_item_id` stranded | high | Reordered: build valid_ids first, only mark those rows `in_progress`. Rows without work_item_id stay pending for normal dead-letter path. |
| 166 | Recurrence `count_remaining` exhaustion sets `None` instead of stopping — rules fire forever | critical | Check `new_count <= 0` before setting to None; exhausted status set immediately. Fixed in both Postgres and InMemory backends. |
| 165 | Sidecar `heartbeat_claim` uses `AcquireClaimRequest` instead of `HeartbeatClaimRequest` — `expected_attempt_number` dropped | critical | Route now uses `HeartbeatClaimRequest`; wires `expected_attempt_number` through to core API. |
| 161 | Sidecar `update_recurrence_rule` reads `rule_id` from query_params instead of body — KeyError at runtime | high | Added `rule_id: str` to `UpdateRecurrenceRuleRequest` model; route handler reads `_parse_uuid(body.rule_id)` instead of `request.query_params`. |
| 162 | Sidecar sole-signer middleware reads request body before Pydantic — depends on Starlette body caching | medium | Middleware now reads via `request.stream()` explicitly and caches on `request._body`, making the body-available-to-downstream contract explicit. |
| 163 | Sidecar hook lifecycle tests are stubs — Plan 005 §10 not fully exercised | medium | Added `hook_test_workflow` with `hooks: [on_complete]` on transition; implemented claim→complete round trip, lease expiry→sweep→reclaim, and sweep tests. |
| 164 | `_find_next_future_slot` 10000-iter cap silently loses slots on sub-minute schedules | medium | Interval schedules now compute next-future-slot in closed form (O(1) arithmetic). Rrule schedules raise `RECURRENCE_SCHEDULE_INVALID` on cap hit instead of returning stale slot. |
| 160 | ConnectionPool missing configurable `max_lifetime` and health-check parameters | low | Added `pool_max_lifetime` parameter to `ConnectionManager`, `Substrate.__init__`, and `Substrate.create_project`, passed through to `psycopg_pool.ConnectionPool(max_lifetime=...)`. |
| 159 | `timestamp` custom field validation only checks `isinstance(str)`, accepts invalid date strings | low | Added `datetime.fromisoformat(value)` validation in `_coerce_field` for timestamp type, raises CUSTOM_FIELD_VIOLATION on invalid ISO strings. |
| 158 | `_parse_semver` crashes with `IndexError` on non-3-part version strings | medium | `_parse_semver` now validates exactly 3 dot-separated components, raises SubstrateError(WORKFLOW_VERSION_INCOMPATIBLE) on malformed input with descriptive message. |
| 157 | `check_idempotency` returns original event even when retry payload differs | medium | Accepted — payloads with non-deterministic fields (e.g., link_id) make strict comparison infeasible. UniqueViolation recovery (BC-150) provides sufficient protection. |
| 156 | `drop_project_schema` leaks an open database connection if `DROP` raises | medium | Replaced manual `connect/close` with `with psycopg.connect(...) as conn:` context manager. |
| 155 | Hook consumer reconnect max-attempts is off-by-one (allows 11 instead of 10) | medium | Changed `>` to `>=` in both initial-connect and mid-flight reconnect attempt checks. |
| 154 | `examples/telemetry_via_hooks.py` uses f-string SQL interpolation for schema/table names | medium | Replaced all f-string SQL with `psycopg.sql.Identifier` and `psycopg.sql.SQL` composition. |
| 153 | `read_events_by_work_item` scans all partitions because `timestamp` partition key is unbounded | high | Added `timestamp <= last_event_at` upper bound using `work_items_current.last_event_at`, enabling Postgres to prune future partitions. |
| 152 | Workflow content hash includes `raw_yaml`, making whitespace/formatting break idempotency | high | Both `compute_content_hash` and `compute_content_hash_from_dict` now pop `raw_yaml` from the dict before JCS canonicalization. |
| 151 | `recurrence_fires_total` metric emitted but has no `Metrics.inc` definition, so fires are silently uncounted | high | Added `recurrence_fires_total` to the counters dict in `Metrics.inc` with Prometheus name `substrate_recurrence_fires_total`. |
| 150 | `UniqueViolation` catch raises false-positive `IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD` on identical-payload races | high | On UniqueViolation, re-runs `check_idempotency` against the persisted row. If actor_id/transition/work_item_id match, returns existing event. |
| 149 | `fire_recurrence` returns `None` work-item on idempotent retry | critical | On early-exit (next_fire_at > now), queries events table by JSONB containment on recurrence_rule_id to find and return the existing work item. |
| 148 | Partitioned events table loses global `event_id` uniqueness; cross-work-item collisions possible | critical | Added `pg_advisory_xact_lock` on SHA-256 hash of event_id before INSERT in both `append_event` and `append_transition_event`. |
| 147 | `update_not_before` updates projection BEFORE event insert, violating spec ordering | high | Moved projection UPDATE to after `_append_event` call in both Postgres and InMemory backends. |
| 146 | `run_validator` ThreadPoolExecutor blocks after timeout while holding canonical row lock | critical | Replaced `with ThreadPoolExecutor` with manual lifecycle: `shutdown(wait=False, cancel_futures=True)` on timeout. |
| 145 | Missing orphan-check in replay after dropping work_item_id FK | medium | Added orphan detection in replay: pre-fetches all events grouped by work_item_id, halts on orphan events without a created transition, warns on orphans with a created event. |
| 141 | `_dict_contains` diverges from Postgres `@>` on nested JSON custom fields | medium | Replaced `_dict_contains` with recursive containment matching Postgres `@>` semantics: deep dict containment, list subset, scalar equality. 3 new conformance tests for nested JSON fields. |
| 140 | Property test `reuse_eid` strategy never fires — idempotency coverage is dead | medium | Replaced `st.lists(operation())` with `st.data()` iterative draw threading `event_id_pool` between draws. Event IDs generated at draw time so both backends use the same value. Fixed InMemory projection-before-event bugs in `acquire_claim`, `release_claim`, `create_work_item`. |
| 128 | Extract shared EventStore protocol to prevent backend divergence | high | `_event_store.py` with `EventStore` protocol, `InMemoryEventStore`, `PostgresEventStore`, shared `append_event()`. InMemory fully migrated; Postgres migrated for `append_event`. All 411 tests pass. |
| 137 | InMemory hook_queue entry IDs can collide after poll_hooks cleanup | medium | Replaced with monotonically increasing counter |
| 136 | InMemory read_events sort order diverges from Postgres for time-range queries | medium | Fixed ascending sort for time-range queries, added event_seq tiebreaker |
| 135 | validate_not_before raises TypeError on naive/aware datetime mismatch | medium | Added timezone normalization matching validate_not_before_delta |
| 134 | Postgres event INSERT can raise raw UniqueViolation on concurrent event_id collision | medium | Wrapped INSERTs in try/except UniqueViolation |
| 133 | InMemory replay aborts on first error instead of per-work-item error handling | high | Added per-work-item try/except, REPLAY_HALTED for missing workflows and state violations |
| 132 | InMemory requeue_dead_lettered_hook loses transition and payload data | high | Added transition to dead-letter dict; requeue reads directly from entry |
| 131 | InMemory sweep_expired_claims unconditionally clears claimed_by without steal detection | high | Already fixed by BC-114; InMemory sweep now checks `claimed_by` and `claim_expires_at` match before clearing |
| 130 | Replay does not derive claim_expires_at, latent drift risk | medium | Derivation implemented by GLM-3 (Session 24); `_states_match` intentionally excludes `claim_expires_at` because heartbeats mutate it without events |
| 129 | InMemory _append_claim_event and _append_simple_event bypass idempotency | critical | Already fixed by BC-116 in Session 24; both helpers call `check_idempotency()` at top |
| 127 | Replay temp-table cleanup is transactional | medium | Moved `drop_old_replay_tables` out of `_replay` transaction into `Substrate.replay()` pre-step with raw connection + commit |
| 126 | Dead-letter requeue loses original max_retries | medium | Migration 008 adds `max_retries INTEGER` to `hook_dead_letter`; wired through `_move_to_dead_letter`, `requeue_dead_lettered_hook`, and InMemory equivalents |
| 125 | InMemory missing input validation on several paths | medium | Added `validate_event_id` and `validate_not_before_delta` to InMemory `create_work_item`, `acquire_claim`, `release_claim`, `create_link`, `remove_link`, `update_not_before` |
| 124 | InMemory register_validator/register_hook_handler mutate in-place | medium | Switched to copy-on-write pattern matching Postgres backend |
| 123 | Workflow semantics do not reject duplicate transition/state/type names | high | Added `_require_unique` helper; duplicate state names, work_item_type names, role names, link_type names, transitions (name+from_state), and custom fields within a type now raise `WORKFLOW_SEMANTIC_ERROR` |
| 122 | InMemory read_events returns empty list with no filters | high | Added default branch returning all events sorted by `(timestamp, event_seq)` DESC, matching Postgres |
| 121 | Substrate.close unsafe on partially-constructed instances | high | Initialize `_hook_consumer = None` before the try block; guard `close()` with `is not None` check |
| 120 | HookConsumer dies silently on initial connection failure | high | Wrapped initial connect in the same retry loop used for mid-flight reconnections |
| 119 | validate_json_safe_value raises raw TypeError on non-string dict keys | high | Added `isinstance(value, str)` guard in `_check_string_safe` raising `SubstrateError(INVALID_ARGUMENT)` |
| 118 | create_work_item does not bound not_before delta | high | Added `_validate_not_before_delta` in `create_work_item` API boundary for both Postgres and InMemory |
| 117 | InMemory remove_link fallback logic broken | high | Changed fallback to scan events in reverse `event_seq` order and check the most recent event for the `(from, to, type)` tuple |
| 116 | InMemory claim/link operations bypass idempotency checks | critical | Moved idempotency check into `_append_claim_event` and `_append_simple_event` helpers so all callers inherit it |
| 115 | InMemory backend event_seq off-by-one vs Postgres on create_work_item | critical | InMemory `create_work_item` now emits `created` event with `event_seq = next_event_seq` (1) and updates `last_event_seq` / `next_event_seq` to match Postgres |
| 114 | Sweep emits spurious claim_expired events causing replay drift | critical | Postgres `sweep_expired_claims` now checks `cur.rowcount > 0` before emitting the event; InMemory sweep checks `wi[claimed_by] == claim[actor_id]` before clearing |
| 113 | Jsonb() wrapper type would replace fragile per-entry-point validation | low | Implemented — Jsonb frozen dataclass validates on construction; internal functions accept Jsonb | None; public API wraps dict | None at boundary |
| 112 | Sync validator row-lock DoS — operational hardening | medium | Implemented — statement_timeout, AST I/O detection, near-timeout watchdog |
| 111 | JSON Schema permits additionalProperties:true everywhere — workflow isolation unclear | medium | Rejected — false alarm; schema already has `additionalProperties: false` at every level |
| 110 | custom_fields merge in append_transition_event is shallow, not deep | medium | Accepted — shallow merge by design; predictable, consumers include full nested structures |
| 109 | synchronous_commit configure callback raises silently on connection failure | medium | Rejected — false alarm; psycopg pool discards connections if configure raises |
| 108 | (empty entry — no BC-108 in tree) | n/a | n/a |
| 107 | validate_work_item_refs propagates unhandled ValueError from uuid.UUID() | medium | Fixed; wrapped in try/except, raises `SubstrateError(CUSTOM_FIELD_VIOLATION)` |
| 106 | Unbounded not_before allows permanent work-item DOS | high | Fixed; added `validate_not_before_delta()` with 365-day max |
| 105 | Replay skip of revoked-key events with continue_on_revoked=True leaves bad events in log | high | Accepted — events are immutable audit trail by design |
| 104 | expected_event_seq missing from create_link and remove_link — TOCTOU race | high | Accepted — FOR UPDATE lock provides adequate serialization |
| 103 | Client-supplied event_id not validated as UUIDv4; no entropy guarantees | critical | Fixed; added `validate_event_id()` checking version nibble; wired into all public API methods |
| 102 | No rate limiting on any public API endpoint | critical | Accepted — out of scope; library not daemon |
| 101 | actor_metadata role claim is self-attested without independent verification | critical | Accepted — by design per BR-09 and trust tier definitions |
| 100 | HMAC key material held in plaintext Python memory | critical | Accepted — environmental trust boundary; inherent to in-process HMAC |
| 099 | InMemorySubstrate.release_claim can raise KeyError on concurrent sweep | medium | Changed `del` to `.pop(work_item_id, None)` |
| 098 | claimable_now filter uses transaction-time now() instead of statement-time | medium | Documented as design choice; `clock_timestamp()` alternative noted in spec |
| 097 | drop_project_schema does not validate project name before executing DROP SCHEMA | medium | `validate_project_name()` now called before any SQL is executed |
| 096 | run_validator loses original exception chain | medium | Added `from e` to preserve exception chain for downstream debugging |
| 095 | InMemorySubstrate replay ignores continue_on_revoked and never verifies signatures | high | In-memory replay now verifies dummy signatures and respects `continue_on_revoked` when KeySet is configured |
| 094 | Hook queue table lacks a composite index for the polling query | high | Migration 007 adds `idx_hook_queue_poll (status, next_retry_at, id)` partial index |
| 093 | query_work_items has_link_type filter performs correlated sequential scan without index | high | Migration 007 adds `idx_events_link_type` partial composite index on link transitions |
| 092 | validate_json_safe_value allows NaN and Infinity, which Postgres JSONB rejects | high | Added explicit float branch rejecting `NaN` and `±Inf` with `INVALID_ARGUMENT` |
| 091 | Schema name validation accepts reserved / system schema names | high | `validate_project_name` now rejects `public`, `pg_*`, `information_schema`, etc. |
| 090 | Replay does not reconstruct claim state — projection not fully derivable from events | critical | `_replay_work_item` now tracks `claimed_by` from claim events; included in `_states_match` / `_diff_fields` |
| 089 | append_event accepts reserved system transition names — can spoof escalations and corrupt replay | critical | Added `_RESERVED_TRANSITIONS` frozenset; blocked in both Postgres and in-memory `append_event` |
| 088 | Async hook queue poll lacks row locking — concurrent consumers double-process hooks | critical | Added `FOR UPDATE SKIP LOCKED` to `poll_and_process_hooks` SELECT |
| 087 | _validators dict not copy-on-write (thread safety) | medium | `register_validator` now uses copy-on-write pattern matching `register_hook_handler` |
| 086 | validate_json_safe_value silently passes non-JSON types | medium | Added else clause raising INVALID_ARGUMENT for set, bytes, tuple, Decimal, etc. |
| 085 | close() is not idempotent | medium | Added None guard on `self._mgr`; second call is a no-op |
| 084 | Empty enum_values array accepted | medium | Added `minItems: 1` to JSON Schema for enum_values |
| 083 | No uniqueness checks on state/transition/type names | medium | Accepted — deduplication is deterministic; error surfaces at runtime |
| 082 | Default values not type-checked at workflow registration | medium | Accepted — late validation surfaces error at creation time |
| 081 | check_idempotency actor_id type annotation wrong | medium | Changed `actor_id: str` to `actor_id: str \| None` |
| 080 | Idempotency check does not verify work_item_id | medium | Added `work_item_id` param to `check_idempotency`; verifies match when provided |
| 079 | Replay skips work items with zero events silently | medium | Accepted — zero-event items are already corrupt beyond replay's scope |
| 078 | InMemory requeue_dead_lettered_hook loses work_item_id | medium | Store `work_item_id` at top level in dead-letter; use it directly on requeue |
| 077 | Missing validate_ttl in resolve_claim_acquire | high | Added `validate_ttl(ttl_seconds)` at top of `resolve_claim_acquire` |
| 076 | JSON-typed custom fields bypass validate_json_safe_value | high | Added `validate_json_safe_value` call in the json branch of `_coerce_field` |
| 075 | create_project and __init__ leak connection pool on failure | high | `create_project`: try/finally; `__init__`: try/except with `mgr.close()` on failure |
| 074 | continue_on_revoked=True skips signature verification entirely | high | Fixed; separated key lookup from status check; revoked keys now verify signature, only unknown keys skip |
| 073 | InMemory read_events returns oldest events; Postgres returns newest | high | Fixed InMemory to sort DESC, take limit, reverse (matching Postgres) |
| 072 | Replay silently swallows unrecognized transitions with custom_fields_update | critical | Only apply custom_fields_update when transition matches workflow definition |
| 071 | Heartbeat revives expired claims (zombie revival) | critical | Added expiry check to `resolve_heartbeat`; expired claims now raise CLAIM_LOST |
| 070 | Replay temp tables accumulate between replay() calls | low | Accepted — tables cleaned at next replay; dropping would break API contract |
| 069 | __init__.py has excessive _types re-export boilerplate | low | Consolidated ~20 individual import blocks into 3 grouped blocks (`_contract`, `_events`, `_types`) |
| 068 | validate_field_values takes WorkflowDefinition but validate_field_update takes raw dict | low | Accepted — raw dict avoids allocation in hot transition path |
| 067 | _contract.py has no standalone unit tests | medium | Added `tests/test_contract.py` with 85 unit tests covering all 17 pure functions |
| 066 | KeySet hot-reload TOCTOU between active_key_id check and access | low | `active_key()` now captures `keys`/`active_id` as locals before check+access |
| 065 | HookConsumer nested transaction risk with append_event under savepoints | low | Accepted — nested savepoints are standard Postgres; low probability in practice |
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