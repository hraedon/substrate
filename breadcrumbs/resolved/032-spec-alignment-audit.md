# Substrate Spec-to-Code-to-Test Alignment Audit

**Date:** 2026-05-06
**Scope:** All FRs (01–25), all ACs (01–36)
**Method:** Each FR/AC checked against source code (`src/substrate/`) and test files (`tests/`).

## Summary

| Status | Count |
|--------|-------|
| [covered] | 37 |
| [partial] | 13 |
| [gap] | 4 |

No [gap] items have missing code — all code paths exist. Gaps are missing *tests* for implemented code.

## High-severity gaps

| AC | Description | Risk | Code exists | Tests missing |
|----|-------------|------|-------------|---------------|
| AC-16 | Key lifecycle (unknown/revoked/deprecated) | Security-adjacent | `_keys.py:100-134` | Zero tests for signing-context key rejection |
| AC-20 | Startup integrity (migrations + version check) | Fail-fast safety | `_migrations.py:82-90`, `_integrity.py:40-49` | Zero tests |
| AC-21 | Structured log + Prometheus output | Observability contract | `_observability.py` (19 counters, log_operation) | Zero behavioral tests |
| AC-12 | Pinned-version transition isolation | Correctness under version upgrades | `__init__.py:384-409` (version-locked query) | No cross-version test |

## Medium-severity partials

| AC | Description | What's tested | What's missing |
|----|-------------|---------------|----------------|
| AC-07 | Stale heartbeat rejection | Valid heartbeat extends TTL | No test for different actor_id or advanced attempt_number → CLAIM_LOST |
| AC-09 | sweep_expired_claims | claimable_now query excludes expired | No test for sweep returning count / removing rows |
| AC-14 | hook_dead_lettered event | Dead-letter table checked | No assertion that `hook_dead_lettered` event was emitted |
| AC-18 | Error format specificity | Broad substring matching | No test for YAML line number, JSON pointer, semantic element name |
| AC-19 | Non-existent DB fails fast | Multiple workflows tested | No test for DB_NOT_FOUND error |
| AC-22 | Link validation negatives | Valid link + event tested | No test for cross-project or disallowed-type rejection |
| AC-23 | link_removed event + history | remove_link called in tests | No assertion on link_removed event emission or history preservation |
| AC-24 | Full idempotency surface | Event-append idempotency well-tested | No test for duplicate event_id on transition, claim, or link mutations |
| AC-27 | replay_report row uniqueness | Categories checked individually | No test asserting exactly one row per work-item |
| AC-31 | NOTIFY payload content | Hook delivery tested | No test capturing NOTIFY to verify payload is event_id only |
| AC-32 | Concurrent pagination | Pagination no-overlap tested | No test with concurrent appends during scan |

## Covered items (37 total)

AC-01, AC-02, AC-03, AC-04, AC-05, AC-08, AC-10, AC-11, AC-13, AC-15, AC-17, AC-25, AC-26, AC-28, AC-29, AC-30, AC-33, AC-34, AC-35, AC-36, FR-01, FR-02, FR-03, FR-04, FR-05, FR-05b, FR-06, FR-07, FR-08, FR-09a, FR-09b, FR-10, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, FR-17, FR-18, FR-19, FR-20, FR-21, FR-22, FR-23, FR-24, FR-25

## Recommendations

1. **AC-16 tests are the highest priority.** Key lifecycle is security-adjacent. Write tests for: unknown key_id rejection with structured log check, revoked key rejection, deprecated key acceptance with warning. These are small, deterministic tests.

2. **AC-20 tests are second priority.** Startup integrity is a fail-fast gate. Write tests that: register a workflow with incompatible substrate_version and verify WORKFLOW_VERSION_INCOMPATIBLE, and verify MIGRATION_REQUIRED when schema version is behind.

3. **AC-21 tests require infrastructure.** Testing Prometheus counters and structured logs needs caplog/fixtures. Consider whether the coverage value justifies the fixture investment, or whether a one-time manual verification with a checklist is sufficient.

4. **AC-12 cross-version test.** Register workflow v1 (without a transition), then v2 (with the transition). Create a work-item pinned to v1. Attempt the v2-only transition. Assert rejection.
