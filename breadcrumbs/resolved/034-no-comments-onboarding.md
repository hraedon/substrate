# RFC-034: "No comments in code" style rule — onboarding trade-off

---
number: "034"
title: '"No comments in code" style rule — onboarding trade-off'
severity: low
status: implemented
kind: design
author: perplexity-review
related: []
---

## Current state

AGENTS.md § Conventions states:

> **No comments in code (style rule)**

The project treats `spec.md` and `AGENTS.md` as the canonical reference for behavior and intent. Code is expected to be self-explanatory through naming and structure.

## Problem

While the "no comments" rule is defensible for agents who have full context of the spec and AGENTS.md, it creates a steep onboarding cliff for casual contributors (humans) who:

1. Clone the repo and open a source file without having read the 30+ page spec.
2. Want to understand a guard clause or invariant without flipping between files.
3. Submit a PR and get it rejected because they added explanatory comments.

In other words, the rule optimizes for **agent maintainability** at the cost of **human discoverability**.

## Assessed severity: low

Not a correctness issue. The spec and AGENTS.md exist and are comprehensive. It is a contributor-experience concern.

## Options

### Option A: Keep the rule, document it more prominently (recommended)

Add a `CONTRIBUTING.md` (or section in README.md) that:

1. States the rule explicitly.
2. Explains the rationale (spec is canonical, comments drift, agents read the spec).
3. Gives an example of what to do instead of comments (e.g., extract a well-named helper function, add a test case, update the spec).

**Pros:** Zero relaxation of the rule, sets expectations for humans.  
**Cons:** Still a cliff — just a well-marked one.

### Option B: Allow "why" comments on non-obvious invariants

Narrows the rule to:

> No comments that state *what* the code does (that should be obvious from the code).  
> Comments on *why* an invariant exists are acceptable if the reason is not derivable from the spec.

Example:

```python
# AC-29: snapshot isolation means we can read uncommitted events
# from the same transaction without seeing interleaved writes.
rows = conn.execute(...).fetchall()
```

**Pros:** Preserves most of the "no comment" benefit while allowing traceability to spec rationales.  
**Cons:** Subjective — "why" vs. "what" is a judgment call, creates review friction.

### Option C: Require spec cross-references instead of prose comments

Allow inline comments only if they are machine-readable references to ACs or FRs:

```python
# AC-28
rows = conn.execute(...).fetchall()
```

**Pros:** Minimal prose drift, still provides traceability.  
**Cons:** Requires humans to keep AC numbers in working memory or look them up.

### Option D: Drop the rule entirely and adopt a normal commenting style

**Pros:** Lowest onboarding cliff, industry-standard.  
**Cons:** Comments will drift as the spec evolves. Agents may be misled by stale comments. Increases line count without increasing correctness.

## Recommendation

Implement **Option A** now (visible contributor guidelines).  
If the project ever opens to external human contributors, revisit **Option C** as a middle ground.

## Questions to resolve

1. Is the project intended to stay agent-maintained, or will it accept human PRs?
2. Should `CONTRIBUTING.md` be added now, or is that premature until external contributors exist?
3. Should the linter enforce the rule (e.g., `ruff` check for comment blocks) or is it social convention?
