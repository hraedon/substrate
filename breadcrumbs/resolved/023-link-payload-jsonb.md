---
number: "023"
title: Optional payload JSONB on links
severity: low
status: resolved
kind: improvement
author: claude-opus-4-7
date: "2026-05-05"
tags: [links, api, ergonomics]
related: []
---

## Problem

Links currently carry only `(from_id, to_id, link_type)`. There is no place to attach context to the relation itself. When a downstream system wants to record *why* two work-items are linked, or carry rationale/diagnostics on the relation, it has to either:

- Encode the rationale into one of the work-items' `custom_fields` (couples the relation's metadata to a side, asymmetrically), or
- Create a dedicated work-item to hold the rationale (heavyweight; introduces a separate node just to annotate an edge).

Events have an optional `payload` for exactly this purpose; links don't. The asymmetry is mild but noticeable when modeling pipelines where edges carry meaningful structure (e.g., a `reviews` link with juror verdict and rationale, an `escalation_of` link with the failure summary that drove escalation).

## Resolution

Added optional `payload: dict | None` to links. No migration needed — links are event-sourced (no separate `links` table); the payload is stored in the `link_created` event's JSONB payload under `link_payload` key.

- `Link` dataclass gains `payload: dict | None = None` field with `to_dict`/`from_dict` support.
- `create_link()` internal and public API accept optional `payload` parameter.
- Payload stored in the `link_created` event payload and returned in the `Link` dataclass.
- Test: `test_create_link_with_payload` verifies round-trip.
- `remove_link` semantics unchanged; payload is on the live link, not the tombstone.
