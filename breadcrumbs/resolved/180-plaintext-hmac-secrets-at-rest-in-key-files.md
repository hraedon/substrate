---
number: "180"
title: HMAC secrets stored as plaintext in key files — no encrypted key file or KMS support
severity: medium
status: proposed
kind: improvement
author: security-audit
date: "2026-05-17"
tags: [security, crypto, keys, secrets-management]
related: ["100", "066"]
---

## Observation

`KeySet._load()` at `_keys.py:62-67` reads HMAC secrets from a JSON file as plaintext. Secrets are stored as either raw strings or Base64-encoded bytes in the file. There is no support for:
- Encrypted key files (e.g., age-encrypted, GPG-wrapped, or AES-KW).
- External key management services (KMS, Vault, AWS Secrets Manager).
- Environment-variable-based key injection.

BC-100 accepted in-memory plaintext as an environmental trust boundary. This breadcrumb extends that concern to the at-rest storage. The test key file at `tests/test_keys.json` contains a real (test-only) secret in plaintext.

Operators are expected to protect the key file via filesystem permissions or Kubernetes Secrets mounts. This is a documented design choice per §15, but no structured warning or startup check flags the "plaintext keys at rest" condition.

## Proposed

- Add a startup log warning when plaintext keys files are loaded: `log.warning("keys.plaintext_at_rest", path=str(self._path))`.
- Add optional support for K3s/K8s Secret mounts containing Base64-encoded entries (already works via `isinstance(secret, str)` branch for Base64 strings, but could be documented).
- Optionally: accept a `hmac_secret: str` environment variable path or direct value to avoid file-based keys completely for KMS-provisioned deployments.
