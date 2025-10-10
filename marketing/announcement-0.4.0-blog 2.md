---
title: Mnemex v0.4.0 — CI Hardening, SBOM, Type Checking
date: 2025-10-09
draft: true
---

We’ve shipped Mnemex 0.4.0 (pre‑1.0), focused on build quality, supply‑chain visibility, and developer experience.

Highlights

- CycloneDX SBOM for every push/PR (Security workflow)
- Bandit scans (non‑blocking) with consolidated Security Summary
- mypy re‑enabled in CI; codebase type‑clean
- Pre‑commit hooks: Ruff (lint + format) and mypy (src‑only)
- Guard workflow: blocks committing built site artifacts to `main`
- GitHub Actions updated: actions/checkout v5, codecov‑action v5, setup‑uv v7

Why this matters

Mnemex is a local, privacy‑first memory system for AI assistants. These changes increase trust and transparency:

- SBOM improves supply‑chain visibility for dependencies
- Bandit and CodeQL provide continuous security scanning
- mypy and Ruff improve code health and maintainability

What’s next (0.5.0)

- Cross‑platform testing (Windows/Linux)
- Performance benchmarks and optimizations
- Production hardening: error handling, file locking
- Continued security improvements

Links

- Release: https://github.com/simplemindedbot/mnemex/releases/tag/v0.4.0
- Repo: https://github.com/simplemindedbot/mnemex
- Docs: https://simplemindedbot.github.io/mnemex/

Versioning

We are using pre‑1.0 SemVer (0.y.z) until we’ve completed cross‑platform testing and are confident in API stability.
