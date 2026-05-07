# Substrate Worklog

Structured log of development sessions and milestones.

---

## 2026-05-07 — Session 10: BC-037 runtime ref validation, BC-033/034/035 RFCs, BC-038 in-memory backend

**Focus:** Resolve all actionable open breadcrumbs — BC-037 (high bug), BC-033/034/035 (RFCs), BC-038 (in-memory backend).

**Context:** Session 9 left 6 open breadcrumbs. User asked to start with BC-037, then knock out BC-033-035, then tackle BC-038.

**Delivered:**

1. **BC-037 — Runtime validation for `work_item_ref` fields** (high bug → resolved):
   - `src/substrate/_workflow.py`: Added `import uuid`; updated `_coerce_field` to validate UUID format for `work_item_ref` type; added `validate_work_item_refs()` function that queries `work_items_current` to verify existence and type match.
   - `src/substrate/_work_items.py`: Wired `validate_work_item_refs` into `create_work_item` after `validate_field_values`.
   - `src/substrate/__init__.py`: Wired `validate_work_item_refs` into `transition` after `validate_field_update`.
   - `src/substrate/_workflow_schema.json`: Made `target_work_item_type` optional for `work_item_ref` fields. Fields without `target_work_item_type` still check existence only.
   - `tests/test_work_item_ref_validation.py`: 10 new tests covering nonexistent UUID, wrong type, correct type, invalid format, optional None, untyped ref existence, transition-time validation.
   - `tests/test_sf2_workflows.py`: Fixed `test_version_pinning_across_v1_v2` and `test_full_pipeline_link_types` — both incorrectly set `test_suite_ref` to an `interface_spec` work item.

2. **BC-033 — PgBouncer transaction-mode documentation** (medium RFC → implemented):
   - `AGENTS.md`: Added "Known constraints" section documenting PgBouncer incompatibility.

3. **BC-034 — No-comments onboarding documentation** (low RFC → implemented):
   - `AGENTS.md`: Expanded "No comments in code" convention with full rationale.

4. **BC-035 — Telemetry-via-hooks worked example** (low RFC → implemented):
   - `examples/telemetry_via_hooks.py`: Complete, runnable minimal example.
   - `AGENTS.md`: Updated telemetry pattern section to link to example file.

5. **BC-038 — InMemorySubstrate** (high improvement → resolved):
   - `src/substrate/_in_memory.py`: Full `InMemorySubstrate` implementation (~1260 lines) matching the complete public API surface of `Substrate` (32 methods/properties). Implements workflow registration, work item CRUD, transitions, event logging, claims with TTL, links, actor roles, validators, hooks, replay, update_not_before, dead letter queue, and all query/filter operations — all in-process with no Postgres dependency. Reuses existing validation logic from `_workflow.py`.
   - `src/substrate/testing.py`: Public module exporting `InMemorySubstrate` as `substrate.testing.InMemorySubstrate`.
   - `tests/test_in_memory_conformance.py`: 50 conformance tests (25 scenarios × 2 backends) parameterized over real Substrate and InMemorySubstrate. Covers workflow registration, work item creation, transitions, events, claims, links, actor roles, queries, replay, and update_not_before.

**Breadcrumbs resolved:** BC-037, BC-033, BC-034, BC-035, BC-038.

**Remaining open:** BC-036 (external Postgres guide, accepted). Four pending drafts awaiting triage.

**Test Results:** 258 passed in 48.13s (+ 4 slow benchmarks excluded)

**Lint:** clean

---

## 2026-05-06 — Session 9: Error-path coverage sweep + Perplexity RFCs

**Focus:** Close error-path coverage gaps identified by unfiled audits; formalize Perplexity feedback as RFCs.

**Context:** Session 8 left 176 tests passing but two unfiled audits existed (`audit-error-paths.md`, `audit-spec-alignment.md`). User asked to write the missing tests and create breadcrumbs for anything not finished. Additionally, Perplexity review raised three concerns: PgBouncer transaction-mode scaling cliff, "no comments" onboarding friction, telemetry-via-hooks lacking a concrete example.

**Delivered:**

1. **New `tests/test_remaining_errors.py`** (10 tests): NOT_BEFORE_FUTURE, WORK_ITEM_TYPE_NOT_DECLARED, WORKFLOW_NOT_REGISTERED, LINK_CROSS_PROJECT, CUSTOM_FIELD_VIOLATION x5, DB_NOT_FOUND.
2. **Strengthened existing tests** in 6 files: replaced raw string assertions with `ErrorCode` enum assertions for INVALID_TRANSITION, ROLE_NOT_PERMITTED, WORKFLOW_VERSION_CONFLICT, WORKFLOW_VALIDATION_FAILED, WORK_ITEM_TYPE_NOT_DECLARED, CUSTOM_FIELD_VIOLATION, CLAIM_LOST, LINK_TYPE_NOT_ALLOWED, LINK_TARGET_NOT_FOUND, LINK_NOT_FOUND, IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD.
3. **Cleaned up dead error codes**: removed CLAIM_NOT_EXPIRED, IDEMPOTENCY_COLLISION, DEPRECATED_KEY_ID, LIBRARY_IS_SOLE_SIGNER, HOOK_NOT_DEAD_LETTERED. Wired REPLAY_HALTED into _ReplayHaltError (extends SubstrateError).
4. **Three RFCs created** in `breadcrumbs/rfc/`: RFC-033 (PgBouncer tx-mode, medium), RFC-034 (no-comments onboarding, low), RFC-035 (telemetry concrete example, low).
5. **Breadcrumbs reconciled** — moved audit reports to resolved/031, resolved/032; moved 026-030 to resolved/.

**Test Results:** 198 passed in 39.33s (+ 4 slow benchmarks excluded)

**Lint:** clean

**Commits:** dc0902f, bd4c900

---

## 2026-05-06 — Session 8: Test suite quality sweep — dedup, weak assertions, coverage gaps, _testing centralization

**Focus:** Comprehensive test suite audit and improvement

**Context:** Session 7 left zero open breadcrumbs with 154 tests passing. User asked to scan the repo with particular attention to the test suite and make appropriate improvements. A thorough audit identified 6 categories of issues: duplicated tests, weak assertions, untested error codes/API paths, `_testing.py` too thin (forcing direct internal imports), overly broad exception matching, and missing coverage.

**Delivered:**

1. **`_testing.py` expanded** — Re-exports `KeySet`, `replay_fn`, `sign_event`, `verify_event`, `Metrics`, `poll_and_process_hooks` with `__all__`. Reduces direct internal imports from 8 test files to ~2 (justified exceptions: `test_jcs.py` unit-tests `_jcs` directly; `test_startup_integrity.py` uses raw psycopg for migration-level tests).

2. **Weak assertions fixed** (5 tests):
   - `test_smoke.py::test_query_claimable_now` — was tautological (`claimed_by is None or claim_expires_at is not None` → always true). Now asserts `claimed_by is None AND claim_expires_at is None`.
   - `test_smoke.py::test_create_and_remove_link` — added `link_removed` event payload verification after removal.
   - `test_smoke.py::test_heartbeat` — now verifies `claim2.expires_at > claim1.expires_at`.
   - `test_production_readiness.py::test_valid_actor_kinds_accepted` — now verifies `actor_kind` persisted in created event.
   - `test_stale_heartbeat.py::test_valid_heartbeat_succeeds` — now verifies TTL extension.

3. **JCS exception specificity** — `test_jcs.py` `pytest.raises(Exception)` → `pytest.raises(IntegerDomainError)` for unsafe integer domain tests.

4. **Duplicate tests removed** (3):
   - `test_replay.py::test_replay_halts_on_revoked_key_event` (identical to test_phase3.py)
   - `test_key_lifecycle.py::test_replay_halts_on_revoked_key_event` (identical to test_phase3.py)
   - `test_signing.py::test_replay_detects_out_of_band_state_change` (identical to test_replay.py)

5. **New coverage tests** — `tests/test_coverage_gaps.py` (25 tests) covering previously-untested paths:
   - `TRANSITION_VIA_APPEND_BLOCKED` (2 tests: reject + allow custom)
   - `WORK_ITEM_NOT_FOUND` (2 tests: transition + append_event)
   - `CLAIM_NOT_FOUND` (2 tests: heartbeat + release on unclaimed)
   - `sweep_expired_claims` (3 tests: sweep + events + zero case)
   - `WORKFLOW_SEMANTIC_ERROR` (3 tests: no initial, unreachable, undeclared role)
   - `expected_attempt_number` (2 tests: reject stale + accept correct)
   - `read_events` filters (7 tests: by actor, transition, time range, empty, validation)
   - `query_work_items` filters (3 tests: needs_review, workflow_version, work_item_types)
   - `hmac_key_path=None` (1 test: rejects with UNKNOWN_KEY_ID)

6. **Direct internal imports cleaned up** — test_key_lifecycle.py, test_phase3.py, test_signing.py, test_scale.py now import from `_testing` instead of reaching into `_keys`, `_replay`, `_signing`, `_hooks`, `_observability` directly.

**Breadcrumbs resolved:** None filed; BC-026 partially addressed (test coverage added for several codes, but cleanup decision still pending).

**Test Results:** 176 passed in 40.8s (+ 3 slow benchmarks excluded)

**Lint:** clean

---

## 2026-05-06 — Session 7: Production readiness — migration packaging, metrics, validation, docstrings, spec sync, replay errors, test coverage

**Focus:** Production readiness sweep addressing 7 items from comprehensive codebase audit

**Context:** Session 6 left zero open breadcrumbs with 111 tests passing. All three phases (MVP, Phase 2, Phase 3) complete. User asked to clear breadcrumbs (none open) and begin next reasonable phase. A codebase audit identified 7 production-readiness items: critical migration discovery bug, unwired metric, missing validation, missing docstrings, stale spec.yaml, unstructured replay errors, and test coverage gaps.

**Delivered:**

1. **Migration discovery fix** — `_migrations.py:_migrations_dir()` now uses `importlib.resources.files("substrate").joinpath("migrations")` first (works in pip installs), falls back to parent-relative path for editable installs. `pyproject.toml` gains `force-include` to ship `migrations/` inside the wheel at `substrate/migrations/`.

2. **`claims_stolen` metric wired** — `_claims.py:acquire_claim` now returns 3-tuple `(Claim, escalated, stolen)` where `stolen = prior_actor_id is not None`. `__init__.py:acquire_claim` increments `claims_stolen` metric when a claim is stolen.

3. **`actor_kind` validation at API boundary** — New `_validate_actor_kind()` helper rejects invalid values (`"agent"`, `"human"`, `"system"` only) at all 6 API entry points that accept `actor_kind`.

4. **Docstrings on all 30+ public methods** — Complete docstrings with Args, Returns, Raises sections on every public `Substrate` method.

5. **`spec.yaml` updated to v4** — Phase 3 FRs (FR-24/25/26/27) reflected, resolved open questions removed from pending, delta-to-next-level pruned, Phase 3 decisions added to handoff.

6. **Structured replay errors** — `_replay.py` now raises `_ReplayHaltError` (a private `Exception` subclass) instead of bare `RuntimeError`. Replay catches it cleanly.

7. **New test coverage** — `tests/test_production_readiness.py` with 10 tests: 7 actor_kind validation tests (all 6 API entry points + valid kinds), transition event-id collision test, stolen claim event verification, same-actor re-acquire no-stolen verification.

Plus 5 previously untracked test files committed: `test_key_lifecycle.py` (14 tests), `test_link_errors.py` (4 tests), `test_stale_heartbeat.py` (3 tests), `test_startup_integrity.py` (7 tests), `test_version_pinning.py` (3 tests), plus improved `test_smoke.py` assertions.

**Breadcrumbs resolved:** None filed; none open before or after.

**Test Results:** 154 passed in 37.3s (+ 3 slow benchmarks excluded)

**Lint:** clean

---

## 2026-05-06 — Session 6 with glm-5.1 (opencode): Phase 3 — actor roles, replay resilience, spec decisions, update_not_before, field validation, E2E tests

**Focus:** Implement Phase 3 features and close spec gaps

**Context:** Session 5 left zero open breadcrumbs with 81 tests passing. Phase 1 (MVP) and Phase 2 (hooks/escalation) were complete. The user asked for three areas of work: actor → allowed_roles enforcement, continue-on-revoked replay flag, and §16 decision sweep. After those were delivered, the user approved a second batch: update_not_before API, custom field validation at transitions, and E2E integration tests.

**Delivered:**

FR-24 — Actor → allowed_roles enforcement (closes BR-09):
- `migrations/005_actor_roles.sql`: new `actor_roles` table with `(actor_id, role)` PK
- `src/substrate/_actor_roles.py`: register, unregister, list, enforcement check functions
- `src/substrate/__init__.py`: public API `register_actor_role()`, `unregister_actor_role()`, `list_actor_roles()`
- `src/substrate/__init__.py`: enforcement wired into `transition()` — opt-in, backward compatible
- `src/substrate/_errors.py`: new error codes `ACTOR_ROLE_NOT_AUTHORIZED`, `ACTOR_ROLE_ALREADY_REGISTERED`, `ACTOR_ROLE_NOT_REGISTERED`
- `src/substrate/_types.py`: new `ActorRole` frozen dataclass
- 9 tests in `tests/test_phase3.py`

FR-25 — Continue-on-revoked replay flag:
- `src/substrate/_replay.py`: `replay()` and `_replay_work_item()` accept `continue_on_revoked` flag; skips revoked-key events with structured warnings; returns warning count
- `src/substrate/__init__.py`: public `replay(continue_on_revoked=True)` API
- `src/substrate/_types.py`: `ReplayReport` gains `warnings` field (default 0)
- `src/substrate/_replay.py`: report table gains `warnings` column
- 4 tests in `tests/test_phase3.py`

FR-26 — update_not_before API:
- `src/substrate/__init__.py`: public `update_not_before()` method — emits `not_before_set` event, updates projection
- 5 tests in `tests/test_phase3.py`

FR-27 — Custom field validation at transitions:
- `src/substrate/_workflow.py`: new `validate_field_update()` function — validates `custom_fields_update` against work-item-type field definitions
- `src/substrate/__init__.py`: wired into `transition()` before event append
- 5 tests in `tests/test_phase3.py`

E2E integration tests:
- `tests/test_e2e.py`: 4 tests exercising realistic multi-agent workflows (full pipeline, not_before deferral, linked items, role enforcement)

§16 Decision sweep:
- Actor roles: implemented (FR-24)
- Postgres version: pinned to 15+
- Retention: always-grow at homelab scale; month-partition at 1M events
- Spec updated to v4 with all decisions resolved

Spec updates:
- `spec.md`: v4 revision — FR-24/25/26/27, AC-35/36/37/38, BR-09 rewrite, §12/§13/§15/§16/§17.9/§20 updates, handoff state
- `AGENTS.md`: status, source layout, public API updated

**Breadcrumbs resolved:** None new filed. All prior breadcrumbs remain resolved.

**Remaining open:** None.

**Test Results:** 111 passed in 33.5s (+ 3 slow benchmarks excluded)

**Lint:** clean

---

## 2026-05-05 — Session 5: BC-022 content-based idempotency, BC-023/024/025 feature work, BC-009/016/017 final closeout

**Focus:** Implement 6 breadcrumbs, resolve all remaining open items

**Context:** Session 4 left 6 open breadcrumbs (009, 016, 017 held open; 022, 023, 024, 025 newly filed by Opus). User asked to implement BC-022 (content-based idempotency) first, then BC-023/024/025, then close out BC-009/016/017.

**Delivered:**

BC-022 — Content-based workflow registration idempotency:
- `migrations/004_workflow_content_hash.sql`: adds `content_hash BYTEA` to `workflow_registry`
- `src/substrate/_errors.py`: renamed `WORKFLOW_VERSION_ALREADY_REGISTERED` → `WORKFLOW_VERSION_CONFLICT`
- `src/substrate/_workflow.py`: added `compute_content_hash()` and `compute_content_hash_from_dict()` using JCS + SHA-256
- `src/substrate/__init__.py`: `register_workflow()` computes hash, compares on collision — idempotent if same, raises if different; lazy-backfills legacy NULL hashes
- `spec.md` §8: amended registry uniqueness and error table with BC-022 rationale
- `tests/test_smoke.py`: `test_register_version_conflict` added

BC-023 — Optional payload on links:
- `src/substrate/_types.py`: `Link` dataclass gains `payload: dict | None`
- `src/substrate/_links.py`: `create_link()` accepts optional `payload`, stores in `link_created` event JSONB
- `src/substrate/__init__.py`: public `create_link()` passes `payload` through
- `tests/test_smoke.py`: `test_create_link_with_payload`

BC-024 — Telemetry-via-hooks pattern documentation:
- `AGENTS.md`: added "Patterns > Telemetry via hooks" section

BC-025 — Scale benchmarks:
- `tests/test_scale.py`: 3 benchmarks (replay, link queries, hook drain) marked `@pytest.mark.slow`
- `pyproject.toml`: registered `slow` marker
- Baselines: ~0.46ms/event replay, ~3ms link query, ~914 hooks/sec drain

BC-009 — JCS edge-case tests:
- `tests/test_jcs.py`: 16 tests covering float boundaries, integer domain (2^53), UTF-16 key ordering, determinism, NFC caveat

BC-016 — Pagination stability:
- Fix already in place (stable `work_item_id` cursor)
- `tests/test_smoke.py`: `test_pagination_stable_no_duplicates`

BC-017 — Test coverage closeout:
- All 8 load-bearing ACs + Phase 2 ACs verified covered

**Breadcrumbs resolved:** BC-009, BC-016, BC-017, BC-022, BC-023, BC-024, BC-025

**Test/lint results:** 81 passed + 3 slow benchmarks (excluded), ruff clean. Zero open breadcrumbs.

---

## 2026-05-05 — Session 4: Audit sweep — critical bug fix, replay correctness, robustness hardening

**Focus:** Comprehensive codebase audit and fix of 14 issues across correctness, robustness, concurrency, and style

**Context:** Phase 2 was complete with 61 tests passing. Two open breadcrumbs (BC-020, BC-021) from the prior session remained. User asked for a critical audit of the whole repo beyond existing breadcrumbs.

**Delivered:**

Critical bugs (1–3):
- **sweep_expired_claims crash** — `_claims.py:339`: `row[0]`/`row[1]` on `dict_row` results raised `KeyError`; fixed to `row["work_item_id"]`/`row["actor_id"]`
- **custom_fields lost in replay** — `_events.py:append_transition_event`: `custom_fields_update` now persisted in event payload under `custom_fields_update` key; `_replay.py` reads it back correctly
- **not_before lost in replay** — `_work_items.py:create_work_item`: `not_before` now included in `created` event payload as ISO string
- **acquire_claim return type** — `_claims.py`: return annotation corrected to `tuple[Claim, bool]` after BC-020 fix
