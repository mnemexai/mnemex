---
title: Mnemex v0.4.0 — CI Hardening, SBOM, Type Checking
date: 2025-10-09
draft: true
---

Mnemex 0.4.0 ships with a focus on build quality, supply‑chain visibility, and developer experience.

Highlights
- CycloneDX SBOM artifact for every push/PR (Security workflow)
- Bandit runs (non‑blocking) with results summarized in CI
- mypy re‑enabled in CI; codebase is type‑clean
- Pre‑commit hooks: Ruff (lint + format) and mypy (src‑only)
- Guard workflow blocks committing built site artifacts to `main`
- Actions bumped: actions/checkout v5, codecov‑action v5, setup‑uv v7

Docs & Visibility
- Security Scanning and SBOM badges in README
- SECURITY documents SBOM and support policy
- CONTRIBUTING adds pre‑commit usage

Next (0.5.0 target)
- Cross‑platform testing (Windows/Linux)
- Performance benchmarks and optimizations
- Production hardening: error handling, file locking
- Continued security improvements

Release notes: https://github.com/simplemindedbot/mnemex/releases/tag/v0.4.0

