---
title: Mnemex v0.4.0 — CI Hardening, SBOM, Type Checking
date: 2025-10-09
draft: true
---

We’ve shipped Mnemex 0.4.0 (pre‑1.0), focused on quality, transparency, and developer experience.

Highlights
- Supply‑chain visibility: CycloneDX SBOM for every push/PR
- Continuous security: Bandit (non‑blocking) + CodeQL summary in CI
- Code health: mypy re‑enabled (type‑clean), Ruff lint/format
- DX: pre‑commit hooks (Ruff + mypy), guard workflow to block built‑site artifacts on main
- CI upgrades: actions/checkout v5, codecov‑action v5, setup‑uv v7

Why this matters
- Mnemex is a local, privacy‑first memory system for AI assistants.
- These changes strengthen trust (SBOM, scans) and maintainability (types, lint).

What’s next (0.5.0)
- Cross‑platform testing (Windows/Linux)
- Performance benchmarks and optimizations
- Production hardening: file locking, error handling

Links
- Release: https://github.com/simplemindedbot/mnemex/releases/tag/v0.4.0
- Repo: https://github.com/simplemindedbot/mnemex
- Docs: https://simplemindedbot.github.io/mnemex/

We’re operating on pre‑1.0 SemVer (0.y.z) until cross‑platform testing and API stability are complete.

