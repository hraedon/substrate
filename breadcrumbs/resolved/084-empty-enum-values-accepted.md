---
number: "084"
title: "Empty enum_values array accepted, makes enum fields unusable"
severity: medium
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

JSON Schema doesn't require `minItems: 1` for `enum_values`. An enum field with
empty values passes registration, then rejects every value at runtime, making
the field permanently unusable.

## Fix

Add `"minItems": 1` to the enum_values schema definition.
