---
number: "024"
title: Document the telemetry-via-hooks pattern
severity: low
status: resolved
kind: improvement
author: claude-opus-4-7
date: "2026-05-05"
tags: [docs, hooks, observability, fr-13]
related: []
---

## Problem

Substrate's hook system (FR-13) supports the pattern of subscribing to events to maintain external denormalized state — telemetry tables, reporting views, cross-project rollups, search indexes. The capability exists but is not documented as an intended pattern.

## Resolution

Added "Patterns > Telemetry via hooks" section to `AGENTS.md` documenting the recommended shape:
1. Reporting table in a separate schema with indexed query dimensions.
2. Hook handler that reads `actor_metadata`, extracts dimensions, upserts reporting row.
3. Rebuild path: drain events through the same handler in `event_seq` order.

Guidance: do not add denormalized columns to substrate's `events` table for consumer-specific dimensions.
