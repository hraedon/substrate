---
number: "102"
title: No rate limiting on any public API endpoint
severity: critical
status: accepted
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, denial-of-service, api]
related: ["103"]
resolution_date: "2026-05-11"
---

## Resolution

Accepted — out of scope. Substrate is an in-process library, not a network daemon (AGENTS.md: "Library, not daemon. Runs in-process. No HTTP server."). Rate limiting is the host application's responsibility. The connection pool size (default 10) is configurable. No code fix warranted.
