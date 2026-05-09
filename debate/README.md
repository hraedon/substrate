# Active Debate

Structured positions on architectural and design questions that are not yet resolved to a breadcrumb or RFC. One file per topic. These are arguments and recommendations, not defects.

When a debate item is resolved (accepted or rejected), it should be:
- Accepted → move to a spec amendment, breadcrumb, or RFC with resolution note
- Rejected → move to `debate/resolved/` with rejection rationale
- Stale → close if no activity for 60 days

## Index

| # | Title | Position | Blocking |
|---|---|---|---|
| 001 | Backend contract single-source-of-truth | Adopt declarative contract (Option B from RFC-062) with property-based testing stopgap | Phase 4+ or dedicated infrastructure sprint |
| 002 | Workflow composition | Re-evaluate `!include` deferral before Phase 4 YAML becomes unmaintainable | Phase 4 (jury and race) |
