---
number: "138"
title: InMemory create_link drops empty dict payload via truthiness check
severity: low
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-12"
resolved_date: "2026-05-12"
tags: [in-memory, links, conformance]
related: []
---

## Problem

`if payload:` in InMemory `create_link()` evaluates to False when `payload={}`, omitting the `link_payload` key from the event. Postgres uses `if payload is not None`, preserving empty dicts.

## Resolution

Changed to `if payload is not None:`, matching Postgres behavior.
