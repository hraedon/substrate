# substrate

Coordination + state plane for agent pipelines: a strict, versioned core schema and protocol providing work-items, events, claims/leases, actors, and link types over Postgres.

Each project deploys substrate as its own isolated instance (one DB per project; no cross-project state). On top of the core, each project declares its workflow declaratively — states, transitions, role-gating, typed custom fields, and link types. Side effects are hooks the project owns; substrate dispatches events but executes no project code.

Spec lives in `spec.md` (authoritative) with `spec.yaml` as a machine-readable sidecar.

## Status

Pre-implementation. Spec at level 3.
