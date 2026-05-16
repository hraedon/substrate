---
number: "170"
title: "register_workflow_file double-reads file when no extends:"
severity: low
status: resolved
kind: improvement
author: kimi-k2.6
date: "2026-05-16"
tags: [api, workflow]
related: []
---

## Problem

`Substrate.register_workflow_file` and `InMemorySubstrate.register_workflow_file` called `p.read_text()` a second time in the `else` branch (`no extends:`), making two file reads for the common case.

## Fix

Hoist `raw_text = p.read_text()` before the branch; use `raw_text` in the else branch.
