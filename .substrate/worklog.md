# Substrate Worklog

Structured log of development sessions and milestones.

---

## 2026-05-05 — Session 3: Phase 2 implementation

**Focus:** Implement all Phase 2 FRs (FR-10 escalation, FR-13 hooks/validators, FR-14 dead-letter requeue, FR-18 lint helper)

**Context:** MVP was complete with 43 passing tests across 6 test files. User asked to implement the next phase. Discussed scope — all four Phase 2 FRs in dependency order. Phase 2 adds reactivity (hooks, validators) and tooling (lint, dead-letter requeue) once consumers exist.

**Delivered:**
- **FR-10** — Escalation: `_check_escalation()` in `_claims.py` triggers on claim acquire when `attempt_number >= attempt_threshold`; sets `needs_review = true` on `work_items_current`; emits `escalated` event; idempotent via existence check under canonical lock; partial unique index `idx_events_one_escalated` as safety net
- **FR-13** — Hooks & Validators: New `_hooks.py` module with sync validator execution (5s timeout via ThreadPoolExecutor), async hook enqueue into `hook_queue` with NOTIFY, background `HookConsumer` thread with LISTEN + 30s polling, retry with exponential backoff, dead-letter move after max retries with `hook_dead_lettered` event emission
- **FR-14** — Dead-letter requeue: `requeue_dead_lettered_hook()` moves entry from `hook_dead_letter` back to `hook_queue` with reset retry count; re-notifies consumer
- **FR-18** — Lint helper: `_lint.py` with `validate_actor_metadata()` checking recommended fields (model, provider, role_source), role_source value validation, and optional JSON Schema conformance

**Infrastructure changes:**
- Migration `003_escalation_idempotency.sql` — unique partial index on events for escalated transition
- `_connection.py` — stores DSN, exposes `dsn` property for hook consumer's dedicated connection
- `_errors.py` — added `HOOK_NOT_FOUND`, `HOOK_NOT_DEAD_LETTERED`
- `_types.py` — added `ValidatorContext`, `HookContext`, `DeadLetterEntry`
- `_observability.py` — added 9 new metrics counters (hooks_dispatched/succeeded/failed/dead_lettered, validators_succeeded/failed/timed_out, escalations)
- `_replay.py` — handles `escalated` (sets needs_review) and `hook_dead_lettered` transitions
- `__init__.py` — 8 new public methods: `register_validator()`, `register_hook_handler()`, `start_hook_consumer()`, `stop_hook_consumer()`, `poll_hooks()`, `requeue_dead_lettered_hook()`, `list_dead_lettered_hooks()`, `validate_actor_metadata()`

**Breadcrumbs raised:** BC-020 (escalation metric placement), BC-021 (hook consumer NOTIFY error handling)

**Test Results:** 61 passed (43 existing + 18 new) in 21.25s

**Lint:** 0 errors (ruff)

---

## 2026-05-05 — Session 2 with glm-5.1 (opencode)

**Focus:** Resolve breadcrumbs across replay, claims, idempotency, links, and API surface

**Context:** Previous session delivered the full MVP with 20 passing tests. A review by claude-opus produced 17 breadcrumbs (defects and design questions). User asked to read the worklog and reasoning.log, then resolve breadcrumbs in priority order.

**Delivered:**
- **BC-001** — `_replay.py`: Added signature verification + key status check per event; halted on revoked keys or signature mismatch
- **BC-002** — `_replay.py`: Replay table now populated with replay-derived state via explicit INSERT, not live snapshot
- **BC-003** — `_replay.py`: `_states_match` compares all 5 derived fields (current_state, custom_fields, needs_review, not_before, last_event_seq); added `_diff_fields` for actionable drift detail
- **BC-004** — `_events.py`: `check_idempotency` now compares actor_id and transition on collision; raises `IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD`
- **BC-005** — `_claims.py`: Claim mutations now emit events (claim_acquired, claim_stolen, claim_released, claim_expired); replay updated to recognize them
- **BC-006** — `_claims.py`: `heartbeat_claim` accepts `expected_attempt_number`; rejects stale-session heartbeats with CLAIM_LOST
- **BC-010** — `__init__.py`: `Substrate.append_event` rejects transitions that match a workflow-defined transition; forces use of `transition()` instead
- **BC-011** — `_types.py` + `_events.py`: Added `workflow_name: str` to Event dataclass and all constructors
- **BC-012** — `_events.py`: Both append functions use `RETURNING timestamp`; Event.timestamp now matches BR-08 (server-stamped)
- **BC-013** — `_work_items.py`: `has_link_type` filter now excludes links with subsequent `link_removed` events via NOT EXISTS subquery
- **BC-014** — `_links.py`: `remove_link` validates live link existence before emitting `link_removed`; raises LINK_NOT_FOUND
- **BC-015** — `_replay.py`: Transition matching uses `(name, from_state)` tuple; name-only matches from wrong state now halt
- Adapted start/end/reflection skills from `/projects/software-factory` into `.substrate/commands/`

**Breadcrumbs resolved:** BC-001, BC-002, BC-003, BC-004, BC-005, BC-006, BC-010, BC-011, BC-012, BC-013, BC-014, BC-015 (12 of 17)

**Remaining open:** BC-007 (unwired idempotency keys), BC-008 (signing jsonb-drift, design), BC-009 (JCS edges, design), BC-016 (pagination, design), BC-017 (test coverage)

**Test Results:** 20 passed in 0.63s

**Lint:** 0 errors (ruff)

---

## 2026-05-05 — Session with glm-5.1 (opencode)

**Focus:** Full MVP implementation of substrate library

**Context:** User provided a complete Level 3 spec (708 lines). Discussed language choice (Python vs Rust vs Go — Python selected for library-in-process model and agent integration). User proposed schema-per-project isolation instead of DB-per-project mid-design — adopted as a superior middle ground.

**Delivered:**
- Complete Python package: 3,291 lines across 17 modules
- Schema-per-project Postgres isolation via `SET LOCAL search_path`
- Migration runner with numbered SQL files
- RFC 8785 JCS canonicalization + HMAC-SHA256 signing
- Workflow YAML parser with 3-pass validation (YAML → JSON Schema → semantic)
- Event store with gap-free `event_seq`, idempotent append, optimistic locking
- Transactionally-consistent projection (`work_items_current`)
- Structured work-item query (FR-05b) with combinable filters + cursor pagination
- Full claim lifecycle: acquire, heartbeat, release, auto-steal, sweep
- State transition validation against pinned workflow version (FR-11)
- Role-gating validation (FR-12)
- Typed directed links with cross-work-item deadlock prevention (ascending lock order)
- Replay with drift detection into fresh table + report
- Startup integrity checks (migration currency, version compatibility)
- Structured logging (structlog) + Prometheus metrics
- 20 smoke tests, all passing
- 0 lint errors (ruff)

**Key Design Decisions:**
- Schema-per-project over DB-per-project: one pool, one backup, engine-enforced isolation, federation-ready
- `dict_row` factory on psycopg3 connections for dict-style access
- Migration tracking table bootstrapped by runner (not migration SQL)
- Unknown transitions in replay treated as no-ops (not halted)
- `Substrate.create_project()` class method for schema + migration init
- `transition()` on Substrate as high-level API (combines FR-11/12 + event append + claim release)

**Test Results:** 20 passed in 0.65s

**Reflection:** Clean build from a thorough spec. The schema-per-project pivot mid-design was the right call — it simplified the connection model and made federation trivially achievable. The spec's level of detail meant very few ambiguous points; the main design work was translating the spec's transaction model into psycopg3's pool + transaction API correctly.

**Artifacts:**
- `src/substrate/` — 17 Python modules + JSON Schema
- `migrations/001_initial.sql` — 7 tables with indexes
- `tests/test_smoke.py` — 20 tests across 10 test classes
- `tests/test_keys.json` — HMAC test key set
- `tests/test_workflow.yaml` — sample workflow definition
- `AGENTS.md` — agent guide for future sessions
- `.substrate/worklog.md` — this file
- `.substrate/reasoning.log` — decision log
- `.substrate/reflections/` — session reflections
