---
number: "168"
title: "Sidecar `list_recurrence_rules` and `list_actor_roles` drop filter parameters"
severity: high
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-16"
tags: [sidecar, plan-005, recurrence, actor-roles]
related: []
---

## Problem

The sidecar routes `list_recurrence_rules` and `list_actor_roles` called the core API with no arguments, ignoring the optional `status` and `actor_id` filter parameters. Clients using the sidecar could not filter results.

## Fix

Both routes now read their respective filter from `request.query_params` and pass it through to the core API.
