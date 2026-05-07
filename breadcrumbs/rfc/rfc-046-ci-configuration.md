---
number: "046"
title: Add CI configuration for automated make check
severity: medium
status: proposed
kind: improvement
author: assistant
date: "2026-05-07"
tags: [ci, automation, infrastructure]
related: []
---

## Observation

Substrate now has 278 tests, lint rules (including RUF), and a Makefile with `check`, `lint`, `test`, and `cov` targets. However, there is no automated CI (e.g. GitHub Actions) to run `make check` on pushes or PRs. Future sessions can silently drift if an agent forgets to run the suite before ending.

## Proposed

Add a `.github/workflows/ci.yml` that:
1. Spins up Postgres via `docker compose -f docker-compose.test.yml`
2. Installs the package with dev dependencies
3. Runs `make check`
4. Optionally runs `make cov` and uploads coverage to a dashboard

Should target `ubuntu-latest`, Python 3.11 and 3.12 matrix.
