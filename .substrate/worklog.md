# Substrate Worklog

Structured log of development sessions and milestones.

---

## 2026-05-08 — Session 17: Adversarial-review breadcrumb sweep (BC-055–059)

**Focus:** Resolve all five pending numbered breadcrumbs from adversarial review pass; promote two draft RFCs to numbered items.

**Delivered:**

1. **BC-055 (high): update_not_before TOCTOU** — Moved `check_idempotency` call before the `UPDATE work_items_current SET not_before` mutation in Postgres backend. Added early idempotency check in InMemory backend before mutating `wi["not_before"]`. Prevents projection corruption on duplicate `event_id`.

2. **BC-056 (low): WorkItem excludes attempt_number** — Added `attempt_number: int = 0` field to `WorkItem` dataclass; wired through `_row_to_work_item`, `_wi_to_work_item`, `to_dict`/`from_dict`. Column was already fetched from DB but silently discarded.

3. **BC-057 (low): Replay output mixed live/replayed columns** — Set `last_event_at`, `claimed_by`, `claim_expires_at` to NULL in replay output table INSERT. These were live-snapshot values, not replayed data, making the table semantically confusing.

4. **BC-058 (low): Claim events actor_kind misattribution** — Added `actor_kind` parameter (default `"agent"`) to `acquire_claim` and `release_claim` in both backends and public API. Claim events now use caller's `actor_kind` instead of hardcoded `"system"`. `sweep_expired_claims` keeps `"system"` which is correct.

5. **BC-059 (low): default_value vs default key inconsistency** — Made `validate_field_update`, `_rebuild_wf`, and `CustomFieldDef.from_dict` accept both `"default_value"` and `"default"` keys via fallback.

6. **BC-060/061 promoted** — Moved draft breadcrumbs from `pending/` to numbered items (canonical diagnostic payload shape, workflow YAML validator helper).

**Breadcrumbs resolved:** BC-055, BC-056, BC-057, BC-058, BC-059.

**Test Results:** 282 passed, lint clean.

---

## 2026-05-08 — Session 16: Opus feedback sweep + open breadcrumb fix

**Focus:** Address three Opus feedback items; resolve three open InMemorySubstrate hook breadcrumbs.

**Delivered:**

1. **Opus item 1 — `__init__.py` god-module assessment** — Verified the 1,337 lines are 100% façade: thin wrappers, docstrings, error-code translation, metric increments. No business logic beyond `_validate_actor_kind` (a 6-line guard). Decision: no extraction needed until additional Phase-3+ surface pushes it past ~1,500 lines.

2. **Opus item 2 — working-tree churn** — `git status` showed zero modified files, clean tree. The 32 modified test files from Session 14 were committed in 930bb61. No stale drift.

3. **Opus item 3 — README status text** — Changed "MVP complete. All Phase 1 FRs implemented and tested." → "MVP + Phase 2 + Phase 3 complete. All FRs implemented and tested. See `AGENTS.md` for current status."

4. **BC-050 (low): InMemorySubstrate poll_hooks does not dead-letter unregistered handlers** — `_in_memory.py poll_hooks` now dead-letters entries with no registered handler, matching real backend (`_hooks.py:125-129`).

5. **BC-051 (low): InMemorySubstrate poll_hooks nil UUID fallback** — Removed `uuid.UUID(int=0)` default. Missing `work_item_id` now dead-letters with error "work_item_id missing from payload", matching real backend (`_hooks.py:134-139`).

6. **BC-052 (low): InMemorySubstrate hook-queue unbounded growth** — `poll_hooks` now prunes `_hook_queue` after each batch, removing `completed` and `dead_lettered` entries. Prevents memory leaks in long-running tests.

7. **RFC renumbering** — Renumbered `RFC-046` → `RFC-053` to fix numbering collision with breadcrumb `046` and `resolved/046`.

**Breadcrumbs resolved:** BC-050, BC-051, BC-052.

**Remaining open:** RFC-053 (CI configuration) — medium, infrastructure item out of scope for agent sessions.

**Test Results:** 282 passed, lint clean.

---

## 2026-05-07 — Session 15 (continued): Breadcrumb sweep round 2 (BC-047, BC-048, BC-049)

**Focus:** Close out all remaining open breadcrumbs except BC-046 (CI config, out of scope).

**Delivered:**

1. **BC-049 (low): Zero-roles bypass documented** — Added docstrings to `check_actor_role_authorized` (`_actor_roles.py`) and `_check_actor_role_authorized` (`_in_memory.py`) explaining FR-24 semantics: enforcement only applies to actors with at least one registered role.

2. **BC-048 (low): InMemorySubstrate hook status tracking** — Added `status` and `updated_at` fields to in-memory hook queue entries. `poll_hooks` now resets stuck `in_progress` entries (>5 min), marks entries `in_progress` before dispatch, `completed` on success, `dead_lettered` on max retries. Parity with real backend's `poll_and_process_hooks`.

3. **BC-047 (low): Stuck-hook double-processing documented** — Added docstring to `poll_and_process_hooks` (`_hooks.py`) documenting the double-processing risk: slow-but-not-stuck handlers may be re-dispatched. Accepted as design limitation; advisory locks noted as future fix.

**Breadcrumbs resolved:** BC-047, BC-048, BC-049.

**Remaining open:** BC-046 (CI configuration) — medium, infrastructure item.

**Test Results:** 282 passed, lint clean.

---

## 2026-05-07 — Session 15: Breadcrumb sweep (BC-043, BC-044, BC-045)

**Focus:** Resolve open breadcrumbs prioritized by severity.

**Context:** Three open breadcrumbs selected: BC-045 (medium, InMemorySubstrate signing parity), BC-044 (low, test import dogfooding), BC-043 (low, read_events ordering docs).

**Delivered:**

1. **BC-045 (medium): InMemorySubstrate loads hmac_key_path** — When `hmac_key_path` is non-empty, `InMemorySubstrate` now creates a real `KeySet` and signs events with HMAC-SHA256 via `_signing.sign_event`. Empty `hmac_key_path` (default) retains dummy signing for test convenience. Catches configuration drift early.
   - `src/substrate/_in_memory.py`: Added `KeySet` import, `_sign_event` import, `self._key_set` field, real signing branch in `_make_event`, `key_set=self._key_set` on all 6 call sites.

2. **BC-044 (low): Test suite dogfoods public API** — Migrated all 23 test files from `substrate._testing` to `substrate.testing` for `drop_project_schema`. Internal symbols (`KeySet`, `raw_transaction`, etc.) remain in `_testing`.

3. **BC-043 (low): read_events ordering documented** — Added ordering semantics to docstrings in both `Substrate.read_events` (`__init__.py`) and `InMemorySubstrate.read_events` (`_in_memory.py`): work_item_id → ASC by event_seq; time range → ASC by (timestamp, event_seq); otherwise → DESC.

**Breadcrumbs resolved:** BC-043, BC-044, BC-045.

**Test Results:** 282 passed, lint clean.

---

## 2026-05-07 — Session 14: GLM must-have/should-have items, composite read_events, public API closeouts

**Focus:** Deliver 6 GLM items (3 must-have, 3 should-have) from SF2 Phase 2 integration sweep.

**Context:** GLM requested HookContext public export, composite read_events filters, BC-042 closeout, public drop_project_schema, hmac_key_path contract fix, and Makefile + RUF rules.

**Delivered:**

1. **HookContext re-exported** — Added `HookContext as HookContext` to `src/substrate/__init__.py` so consumers can import it for handler type annotations.

2. **Composite read_events filters** — Replaced "exactly one filter dimension" constraint with true AND composition in both backends:
   - `src/substrate/_events.py`: Added `read_events_composite()` with layered SQL WHERE clauses
   - `src/substrate/__init__.py`: `Substrate.read_events()` now delegates to composite query; docstring updated
   - `src/substrate/_in_memory.py`: `InMemorySubstrate.read_events()` now layers filters instead of mutually-exclusive branches
   - Added 2 conformance tests in `tests/test_in_memory_conformance.py` covering `work_item_id + transition` and `actor_id + transition`

3. **BC-042 closed** — Moved to `breadcrumbs/resolved/` with resolution note. `connection_info` is stable public API.

4. **drop_project_schema public API** — Exported from `substrate.testing` alongside `InMemorySubstrate`.

5. **hmac_key_path contract fixed** — `InMemorySubstrate` parameter changed from `str | None = None` to `str = ""`, matching real `Substrate` which rejects `None`.

6. **Makefile + RUF rules** — Added `Makefile` with `check`, `lint`, `test`, `cov` targets. Added `"RUF"` to ruff select. Fixed surfaced RUF012/RUF059 violations in 4 test files.

7. **Breadcrumbs opened:**
   - BC-043 (low): composite read_events ordering semantics undocumented
   - BC-044 (low): test suite still imports drop_project_schema from _testing
   - BC-045 (medium): InMemorySubstrate silently ignores hmac_key_path
   - RFC-046 (medium): CI configuration for automated make check
   - RFC-047 (low): remove unused pytest-postgresql / testcontainers dev dependencies

8. **Breadcrumbs resolved:** BC-042.

**Test Results:** 282 passed, lint clean.

---

## 2026-05-07 — Session 13 (continued): Correctness fixes, validation gaps, regression tests, breadcrumb filing

**Focus:** Fix remaining correctness and validation issues identified during scan; add regression tests; file breadcrumbs for all fixes and remaining polish items.

**Context:** User asked to knock out remaining items from the session 13 scan and file breadcrumbs.

**Delivered:**

1. **BC-044: `ttl_seconds` validation** — Added `INVALID_ARGUMENT` error code. `acquire_claim` and `heartbeat_claim` now reject zero/negative TTL in both Substrate and InMemorySubstrate.

2. **BC-045: `validate_field_update` raises on unknown type** — Changed from silent return to `WORK_ITEM_TYPE_NOT_DECLARED`, matching `validate_field_values` behavior.

3. **BC-046: Hook dispatch nil UUID fallback** — `poll_and_process_hooks` now dead-letters hooks with missing `work_item_id` instead of fabricating a nil UUID.

4. **Type annotations tightened** — `_rebuild_wf` return type (`-> WorkflowDefinition`), `key_set: KeySet` in `_claims.py` (3 locations), `metrics: Metrics | None` in `_hooks.py` (2 locations), `SubstrateError.code` typed as `ErrorCode`.

5. **InMemorySubstrate `list_actor_roles` sort order** — Changed from `created_at` to `(actor_id, role)` matching real backend.

6. **8 new regression tests** (`tests/test_session13_regression.py`):
   - `TestSweepRaceCondition` (2 tests): sweep doesn't clobber new claims
   - `TestBeforeSeqOrdering` (2 tests): ascending order, exclusion semantics
   - `TestTtlSecondsValidation` (3 tests): zero/negative rejection for acquire + heartbeat
   - `TestValidateFieldUpdateRejectsUnknownType` (1 test): raises on undeclared type

7. **Breadcrumbs filed:**
   - BC-043 (high, resolved): sweep_expired_claims race condition
   - BC-044 (medium, resolved): ttl_seconds validation
   - BC-045 (medium, resolved): validate_field_update silent return
   - BC-046 (medium, resolved): hook nil UUID fallback
   - BC-047 (low, proposed): stuck hook double-processing
   - BC-048 (low, proposed): InMemorySubstrate hook status tracking
   - BC-049 (low, proposed): zero-roles bypass

**Breadcrumbs resolved:** BC-043, BC-044, BC-045, BC-046.

**Test Results:** 278 passed in 108.18s

**Lint:** clean

---

## 2026-05-07 — Session 13: Remaining session-12 items, fresh scan fixes, BC-042 implementation

**Focus:** Pick up session 12's remaining items; fresh scan for additional issues; fix all MEDIUM-severity bugs found.

**Context:** Session 12's reflection listed remaining work: BC-042 (DSN public API), hooks reconnect log, missing from_dict methods, unspecified MEDIUM issues. Did a fresh scan of all source files, identified 8 new MEDIUM + 10 LOW issues.

**Delivered:**

1. **BC-042: Exposed `connection_info` as public API** — Added `ConnectionInfo` frozen dataclass to `_types.py` with `host`, `port`, `database`, `project` fields. Added `connection_info` property on `Substrate` (parses DSN via `urlparse`, strips credentials). Exported via `__init__.py`. Status promoted to implemented.

2. **Fixed `_hooks.py` reconnect log always showing `attempt=0`** — `reconnect_attempts` was reset to 0 before the log line. Now captures `successful_attempt` before resetting.

3. **Added missing `from_dict` methods** — `ValidatorContext.from_dict`, `HookContext.from_dict`, `QueryPage.from_dict` (takes `item_from_dict` factory for generic deserialization).

4. **M-1 (real backend): Fixed `sweep_expired_claims` race condition** — `UPDATE work_items_current SET claimed_by = NULL` could clobber a newly-acquired claim between the DELETE and the FOR UPDATE lock. Changed WHERE clause to `AND claimed_by = %s` (matching expired `prior_actor_id`), so a re-claimed row is not overwritten.

5. **M-2: Fixed InMemorySubstrate `read_events` `before_seq` ordering** — Was returning DESC order; real backend reverses to ASC. Added `list(reversed(...))` to match.

6. **M-3: Added `connection_info` to InMemorySubstrate** — Returns `ConnectionInfo(host=None, port=None, database=None, project=...)`.

7. **M-4: InMemorySubstrate `poll_hooks` now emits `hook_dead_lettered` events** — Dead-lettered hooks now produce audit events in the event log, matching the real backend's `_move_to_dead_letter`.

8. **M-6: Fixed SQL f-string in `append_transition_event`** — Replaced f-string interpolation of `claim_clear` with psycopg `SQL` composition (`+ claim_clear + SQL(" WHERE ...")`).

9. **M-7: InMemorySubstrate `_check_escalation` now returns `bool`** — Was `-> None` (implicit), diverged from real backend's `-> bool`.

10. **M-8: InMemorySubstrate hook queue `hook_type` fixed** — Changed from `"transition"` to `"async"` matching real backend.

11. **L-6: `SubstrateError.code` type tightened** — Changed from `str` to `ErrorCode` for type-safety.

**Breadcrumbs resolved:** BC-042 (implemented).

**Test Results:** 270 passed in 118.40s

**Lint:** clean

---

## 2026-05-07 — Session 12: Validation scan — fix HIGH/MEDIUM issues, add test coverage, promote breadcrumbs

**Focus:** Comprehensive validation of repo state; fix all HIGH-severity issues found; fill test coverage gaps; promote breadcrumbs.

**Context:** User asked for full repo analysis, verification of recent changes, and recommended next steps. Analysis identified 3 HIGH, 8 MEDIUM, and 10 LOW issues plus spec AC coverage gaps.

**Delivered:**

1. **H-1: Fixed `_claims.py:30` return type annotation** — `acquire_claim` returns `tuple[Claim, bool, bool]` but was annotated `tuple[Claim, bool]`. Breaks type checkers.

2. **H-2: Fixed `_in_memory.py` `poll_hooks` passing raw dict instead of `HookContext`** — Handlers now receive a proper `HookContext` dataclass matching the real `poll_and_process_hooks` behavior. Tests that validate handler behavior against `HookContext` attributes will now be faithful.

3. **H-3 + M-8: Fixed InMemorySubstrate `read_events` filter semantics + transition key divergence** — InMemorySubstrate now stores `wf.to_dict()` instead of raw YAML dict, eliminating the `from`/`to` vs `from_state`/`to_state` key divergence in transitions (3 locations: transition lookup, state assignment, replay). `read_events` now uses priority-based matching (work_item_id > actor_id > start/end > transition) matching the real Substrate, instead of compositing all filters.

4. **M-5: Fixed `ActorKind` case mismatch** — `ActorKind.AGENT` was `"AGENT"` (uppercase) but validation checks `"agent"` (lowercase). Fixed enum values to lowercase.

5. **M-1: Fixed `register_actor_role` docstring** — Was describing `unregister_actor_role`'s error. Removed the incorrect `Raises` block.

6. **L-6: Fixed `requeue_dead_lettered_hook` losing `work_item_id`** — Requeued entry now preserves `work_item_id` and `transition` from the original payload, matching the real backend.

7. **New test file: `tests/test_hook_consumer.py`** (4 tests) — Smoke tests for `start_hook_consumer`/`stop_hook_consumer` lifecycle (AC-14), idempotent start/stop, and poll-based hook delivery with `HookContext` verification.

8. **New test file: `tests/test_claim_link_idempotency.py`** (4 tests) — Event_id dedup verification for `acquire_claim`, `release_claim`, `create_link`, `remove_link` (AC-24).

**Breadcrumbs resolved:** BC-040 (read_events filter semantics), BC-041 (conformance coverage gaps).

**Breadcrumbs promoted:** BC-042 (DSN public API, proposed).

**Test Results:** 270 passed in 111.42s

**Lint:** clean

---

## 2026-05-07 — Session 11: Validation scan — InMemorySubstrate bug fixes, BC-036 resolution, error-code cleanup

**Focus:** Deep validation scan of the repo after Deepseek's session 10 work; fix all bugs found; close remaining breadcrumbs.

**Context:** User asked for a comprehensive validation of the repo's current state. A thorough scan of `_in_memory.py` and recent commits revealed 10 issues ranging from critical to low.

**Delivered:**

1. **CRITICAL: `_check_escalation` wrong argument count** — `_in_memory.py` called `_append_claim_event(wi, uuid.uuid4(), "system", "escalated", {...})` with 5 args; function takes 4. Would crash at runtime on escalation. Fixed by removing stray `"system"` arg.

2. **CRITICAL: `poll_hooks` imports non-existent `run_hook_handler`** — `_in_memory.py` imported `from ._hooks import run_hook_handler` which doesn't exist in `_hooks.py`. Would crash with `ImportError`. Fixed by removing the import and calling the handler directly.

3. **HIGH: InMemorySubstrate replay missing `needs_review`, `not_before`, `last_event_seq` drift detection** — Replay only checked `current_state` and `custom_fields` for drift; the real Substrate checks all 5 fields. Added `derived_needs_review`, `derived_not_before`, `derived_last_seq` tracking and full 5-field comparison. Also added `hook_dead_lettered` to the skip list and `not_before_set`/`escalated` as tracked transitions.

4. **HIGH: Claim events used wrong `actor_id`** — `_append_claim_event` hardcoded `actor_id="system"` for all claim events. The real Substrate uses the actual claiming/releasing actor. Added `actor_id` keyword argument; wired correct actor_id at all call sites (acquire=actor_id, release=actor_id, expire=prior_actor_id or "system").

5. **MEDIUM: `_dead_letter` typed as `list[dict]` but used as `dict[int, dict]`** — Fixed type annotation.

6. **MEDIUM: `read_events` returned ASC order vs real Substrate's DESC** — Rewrote to match real Substrate's ordering semantics per filter type (DESC for work_item_id then reversed, DESC for actor/transition, ASC for time-range, ASC for since).

7. **LOW: Stale `ACTOR_ROLE_ALREADY_REGISTERED` in ErrorCode enum** — Removed from `_errors.py`. Updated `__init__.py` docstring to reflect idempotent behavior. Updated `spec.md` error table.

8. **LOW: `CUSTOM_FIELD_VIOLATION` misused for `actor_kind` validation** — Added `INVALID_ACTOR_KIND` error code to `_errors.py`. Updated both `__init__.py` and `_in_memory.py` to use it.

9. **BC-036 resolved** — External Postgres deployment guide (RFC) was already complete with "accepted" status. Moved from `breadcrumbs/rfc/` to `breadcrumbs/resolved/`.

10. **InMemorySubstrate double YAML parse** — `register_workflow` called both `parse_and_validate` (which parses YAML) and `parse_workflow_yaml` (which parses the same YAML again). Added `validate_and_build()` to `_workflow.py` accepting a pre-parsed dict; InMemorySubstrate now parses once.

**Breadcrumbs filed:** Two pending drafts:
- `in-memory-read-events-filter-semantics.md` — InMemorySubstrate composites filters; real Substrate is mutually exclusive
- `in-memory-conformance-coverage-gaps.md` — Missing conformance tests for claim actor_id, dead-letter, replay drift, sort order

**Open breadcrumbs:** 0 numbered. 6 pending drafts awaiting triage.

**Test Results:** 262 passed in 106.68s

**Lint:** clean

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
