---
number: "042"
title: Expose Substrate DSN (or equivalent) as public API
severity: medium
status: proposed
kind: improvement
author: claude-opus-4-7
date: "2026-05-07"
origin: software-factory-2 BC-015 (resolved with workaround)
tags: [api-ergonomics, testing]
related: []
---

## Observation

Software-factory-2's integration tests needed the substrate DSN to construct fixture infrastructure (project-scoped substrate fixtures, parallel project creation in tests). The only access path is the private `_mgr._dsn`. SF2 BC-015 resolved this with a `factory_config` fixture using public `substrate.project`, but the underlying substrate-level gap remains: there is no public way to ask a `Substrate` instance "what database are you connected to?"

## Proposed

Expose the DSN (or, more conservatively, a connection-info object that supports the legitimate downstream uses without leaking secrets) as public API. Likely shape:

```python
sub.connection_info  # -> ConnectionInfo(host, port, database, project)
# or
sub.dsn  # -> str (with password stripped/masked)
```

## Why medium severity

The workaround works for SF2 today. But every integration-test author will rediscover this gap, and the workaround leaks substrate's project model into consumer test infrastructure. Cheap to fix, eliminates a recurring papercut.
