---
number: "062"
title: "Single-source-of-truth backend contract — eliminate hand-maintained InMemorySubstrate parity"
severity: high
status: proposed
kind: design
author: opencode
date: "2026-05-09"
tags: [rfc, backend, in-memory, testing, spec-parity]
related: ["054", "050", "048", "045"]
---

## Summary

Substrate maintains two full backend implementations — Postgres (`__init__.py` + SQL migrations) and `InMemorySubstrate` (`_in_memory.py`) — that must behave identically on every API surface. This is not a test double; it is a parallel backend maintained by hand.

The v2 factory (software-factory-2) has now been bitten by InMemory/Postgres divergence twice in golden runs (BC-063). Substrate itself has resolved ten InMemorySubstrate parity bugs across Sessions 13–17 (BC-045 through BC-058). The pattern is clear: **hand-maintained dual backends will drift, and the drift will always be discovered in production, not in unit tests.**

This RFC proposes a structural fix: a single machine-readable backend contract that both backends consume, with machine-checked equivalence. Human developers do not hand-edit both backends for a single logical change.

## Problem statement

### The invariant we want

> For every sequence of valid API calls, the Postgres backend and the InMemory backend produce identical `WorkItem`, `Event`, `Claim`, and `ReplayReport` state.

### Current state

- Postgres backend: SQL migrations + Python orchestration in `__init__.py` (~1,358 lines façade)
- InMemory backend: pure Python reimplementation in `_in_memory.py` (~1,493 lines)
- Conformance tests: parametrized tests run both backends through the same scenarios
- What actually happens: developers add a feature to Postgres, then manually translate it into InMemory Python. Edge cases (race conditions, TTL boundaries, claim sweep semantics, hook retry, dead-lettering) are missed because the translation is lossy.

### Why conformance tests are insufficient

Conformance tests only catch what the test author thought to assert. They do not catch:
- Concurrent interleavings that differ between dict-based locking and Postgres `SELECT FOR UPDATE`
- Timestamp edge cases (Postgres `now()` vs Python `datetime.now(UTC)`)
- Hook retry timing and back-off semantics
- Claim TTL expiry and auto-steal race conditions
- Event ordering under load

Golden Run 002 found two bugs that ~270 unit tests missed precisely because the tests exercised happy-path conformance, not edge-case divergence.

## Proposed solutions

Three options, ordered from conservative to fundamental.

### Option A: Property-based conformance testing (conservative)

Add a property-based test suite that generates random valid API call sequences and asserts state equivalence between backends.

- Tool: `hypothesis` or a custom sequence generator
- Each generated sequence is a random walk through `create → claim → transition → release → sweep → replay`
- After every sequence, compare final `WorkItem`, `Event` stream, `Claim` state, and `ReplayReport` between backends
- Run in CI nightly and on every PR

**Pros:**
- No backend rewrite required
- Catches divergence automatically
- Can be implemented independently of other changes

**Cons:**
- The backends still drift; we just detect it faster
- Shrinking failing sequences is hard for concurrent operations
- Does not prevent the problem, only reduces its latency

### Option B: Declarative backend contract (moderate)

Extract all state-transition logic into a single declarative contract file. Both backends interpret the same contract.

- Contract format: YAML or Python dataclasses describing:
  - States and their invariants
  - Transitions: preconditions (what must be true), mutations (what changes), postconditions (what must be true after)
  - Claim lifecycle: TTL semantics, auto-steal rules, heartbeat rules
  - Hook lifecycle: retry count, dead-letter conditions
  - Event append rules: idempotency, seq allocation, signing
- Postgres backend: the contract drives SQL generation or SQL templates
- InMemory backend: the contract drives Python dict manipulation

**Pros:**
- One logical change = one contract edit
- Both backends update mechanically
- The contract is readable by non-developers (you)
- Can be validated independently of either backend (static analysis of the contract)

**Cons:**
- Significant upfront engineering (2–3 sessions)
- Contract language must be expressive enough to capture SQL locking semantics and Python dict semantics equivalently
- Risk: the contract language itself becomes a source of bugs

### Option C: Generate InMemory from Postgres contract (fundamental)

Treat the Postgres schema + migrations as the single source of truth. Generate the InMemory backend automatically from the SQL schema and migration files.

- Parse SQL DDL (migrations) into an abstract schema
- Parse SQL DML patterns (in `__init__.py` or extracted stored procedures) into abstract operations
- Generate a Python dict-based backend that mirrors the abstract schema and operations
- The generated code lives in `src/substrate/_in_memory_generated.py`
- Hand-written overrides live in `_in_memory_patches.py` for cases where the generator is insufficient
- CI enforces: `make generate-in-memory && git diff --exit-code`

**Pros:**
- Postgres is the unambiguous source of truth
- InMemory backend is always in sync by construction
- No contract language to design and debug
- The generator can be tested independently

**Cons:**
- SQL → Python generator is non-trivial (3–4 sessions minimum)
- Requires extracting all business logic from raw SQL strings into named, parseable operations
- Some SQL semantics (window functions, CTEs, `FOR UPDATE`) have no direct Python equivalent
- May need a hybrid: generated core + hand-written edges

## Recommendation

**Adopt Option B (declarative contract) with Option A (property-based testing) as immediate stopgap.**

Rationale:
- Option C is correct but expensive. It requires a SQL parser + code generator that becomes its own maintenance burden. The principal cannot evaluate a generator's correctness without reading generated code.
- Option B keeps the contract human-readable and the backends simple interpreters. The contract is the thing the principal reviews.
- Option A runs in parallel and catches existing divergence while Option B is being built.

## Phase and prerequisites

- **Phase:** Not tied to a numbered substrate phase. This is cross-cutting infrastructure.
- **Prerequisite:** FR-27 (custom field validation at transition) should be stable, because the contract must express validation rules.
- **Blocking on:** Nothing. Can start immediately.
- **Blocked by:** Nothing.

## Acceptance criteria (principal-verifiable)

1. A human adding a new transition rule edits **exactly one file** (the contract), and CI passes without editing either backend source file.
2. The contract file is readable without Python expertise. It describes states, transitions, and invariants in declarative form.
3. A nightly CI job runs property-based conformance testing (Option A) and reports any divergence within 24 hours.
4. No future InMemorySubstrate parity bug is resolved by hand-editing both backends.

## Open questions

- Should the contract be YAML (readable) or Python dataclasses (executable, type-checked)?
- How do we express Postgres locking semantics (`SELECT FOR UPDATE`, gap-free `event_seq` allocation) in a backend-agnostic way?
- Do we keep the existing `_in_memory.py` as a grandfathered implementation and migrate incrementally, or do we require a cutover?

## Related

- v2 BC-063: "InMemorySubstrate drift history — integration test surface is 10x smaller than unit test surface"
- Substrate BC-054: "InMemorySubstrate and Postgres transition()/release_claim reset attempt_number"
- Substrate BC-050–052: "InMemorySubstrate poll_hooks parity gaps"
- Software Factory v1 BC-018/030/035/036: "MockSubstrate diverges from real substrate"
