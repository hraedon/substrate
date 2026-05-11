---
number: "100"
title: HMAC key material held in plaintext Python memory
severity: critical
status: accepted
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, signing, fr-15]
related: ["101", "104"]
resolution_date: "2026-05-11"
---

## Resolution

Accepted as environmental trust boundary. Python inherently holds all in-process data as plaintext memory. Any library performing HMAC in-process has this property. The HMAC signing is already internal to the library (spec §17.9). Using an HSM/KMS is a production deployment decision, not a code fix. Documented as a known trust assumption.
