# Substrate Worklog

Structured log of development sessions and milestones.

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
