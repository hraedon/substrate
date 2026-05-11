---
number: "086"
title: "validate_json_safe_value silently passes non-JSON types"
severity: medium
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_contract.py:340-349` — `set`, `bytes`, `Decimal`, custom objects all pass
validation but crash at JSONB serialization. An unrecognized type should raise.

## Fix

Add else clause that raises SubstrateError for unrecognized types.
