---
model: kimi-k2p6-turbo
datetime: 2026-05-18T16:00 UTC
project: substrate
---

# Session Reflection — 2026-05-18

**Work summary:** Research and positioning session. Scanned the full repo (spec v4, AGENTS.md, 180+ resolved breadcrumbs, active debates, source tree). Read Plans 007–009 (Public API Facade, Trust Model Hardening, Operational Runtime). Authored three debate positions (003–005) and filed two new breadcrumbs (184–185). No code changes.

---

## On the project

Substrate is in a remarkably clean state for a project this size. 528 tests passing, zero open breadcrumbs before this session, spec and code aligned. The most impressive signal is the **breadcrumb discipline** — 180+ resolved defects tracked as one-file-per-item with frontmatter, severity, and cross-references. This is not a project that loses institutional knowledge.

The three draft RFCs (Plans 007–009) show the project is transitioning from "build the core" to "prepare for broader deployment." The plans are well-scoped and threat-model-aware. My only structural concern: Plan 009's "Option A + Option B combined" proposal feels like over-delivery. The sidecar (Plan 005) already serves the daemon deployment shape; a standalone `substrate-maintainer` process is speculative infrastructure without a concrete consumer.

## On the work done

This session was purely analytical — reading, evaluating, writing positions. The positions are grounded in the actual plan text and the existing codebase state. I'm confident in the sequencing recommendation (008 → 007 → 009) because:
- 008 (trust hardening) is the highest value and has no dependency on 007
- 007 (facade decomposition) makes 009 cleaner by removing domain methods from the top-level class
- 009 (operational runtime) is the least urgent and benefits most from the other two

The two breadcrumbs (184, 185) are genuine gaps I noticed during plan review, not padding. Both are observability blind spots that would bite an operator in production.

## On what remains

**Next session should implement Plan 008 WS-1 and WS-5** — they are small, high-impact, and pure `_contract.py` / `KeySet` changes:
1. `strict_roles: bool = False` flag + `role_source` enforcement in `resolve_transition`
2. Raise on unknown key status + `expected_key_count` assertion + `keys_loaded` log

**WS-3 (vendor rfc8785)** should follow in the same or next session. It's a file copy + a CI cross-validation test.

**Plan 007** should be deferred until after 008. The facade extraction is mechanical but touches every public method and every test file. Doing it after 008 means the facade objects are born with the right policy hooks.

**Plan 009** should be scoped down to Option A (timer thread) only, with the metrics and health indicator specified in BC-185.

## Gaps to flag

- **Plan 009 Option B is premature.** No deployment scenario exists where neither in-process embedding nor the sidecar is appropriate. Building `substrate-maintainer` now is infrastructure without a user. (`plans/009-operational-runtime.md:82-90`)
- **WS-2 memory protection is partially wishful thinking in CPython.** `mlock()` via `ctypes` and string zeroization are unreliable due to Python string interning and the garbage collector. The plan acknowledges this but still includes them. Drop these and keep only env-var injection. (`plans/008-trust-model-hardening.md:63-70`)
- **Hook queue depth is completely invisible.** No gauge, no structured log field, no way for an operator to know the queue is backing up until dispatch latency degrades beyond 30s. This is a production blind spot. (`src/substrate/_hooks.py`, `src/substrate/sidecar/routes_hooks.py`)
- **Maintenance thread metrics are unspecified in Plan 009.** The plan mentions `substrate_maintenance_errors_total` but no per-operation counters. An operator cannot distinguish "running and idle" from "dead." (`plans/009-operational-runtime.md:189-196`)
- **rfc8785 cross-validation is described as "at build time" rather than CI-gated.** If this is implemented as a one-time build script, upstream drift will not be caught when the vendored copy is bumped months later. It must be a pytest test in the required CI path. (`plans/008-trust-model-hardening.md:77-82`)
