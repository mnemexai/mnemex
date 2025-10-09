---
title: Mnemex v0.4.0 Deep‑Dive — Building Trust: SBOM, Scans, Types, and DX
date: 2025-10-09
draft: true
---

Mnemex 0.4.0 is about earning trust through transparency and discipline. As a privacy‑first, local memory system for AI assistants, we want users and contributors to see what runs, how it’s built, and where it’s going.

Supply‑chain visibility
- **CycloneDX SBOM**: We produce an SBOM for every push/PR. This helps downstream users audit dependencies and integrate with supply‑chain tools.
- **Non‑blocking security scans**: Bandit outputs are summarized in CI, alongside CodeQL. Findings won’t block development automatically, but they’re visible and trackable.

Code health & maintainability
- **Types**: mypy is re‑enabled in CI; the codebase is type‑clean, increasing refactor safety and API clarity.
- **Formatting & linting**: Ruff handles both lint and format, reducing style drift and keeping PRs focused on logic.
- **Pre‑commit**: We ship hooks for Ruff (lint + format) and mypy (src‑only) so common issues are caught before they hit CI.

Operational hygiene
- **Guard workflow**: Prevents built‑site artifacts from being committed to `main`. Docs build remains reproducible via GitHub Pages.
- **Action bumps**: actions/checkout v5, codecov‑action v5, setup‑uv v7 — tested and aligned with GH‑hosted environments.

Road to 0.5.0
- **Cross‑platform testing** (Windows/Linux), informed by community feedback
- **Performance benchmarks** and optimizations for search, consolidation, and storage
- **Production hardening**: file locking, corruption handling, and clearer failure modes

Versioning policy
- We’re using **pre‑1.0 SemVer (0.y.z)** while APIs evolve and platform testing completes. Expect faster iteration with tagged, documented releases.

Links
- Release notes: https://github.com/simplemindedbot/mnemex/releases/tag/v0.4.0
- Repository: https://github.com/simplemindedbot/mnemex
- Documentation: https://simplemindedbot.github.io/mnemex/

