# Mnemex Marketing Brief (v0.4.0)

## Positioning

Mnemex is a local, privacy‑first memory system for AI assistants. It models human‑like memory dynamics (temporal decay + reinforcement), stores short‑term memory in human‑readable JSONL, and promotes long‑term memory as Markdown for Obsidian.

## What’s New in 0.4.0

- CI hardening and supply‑chain visibility:
  - CycloneDX SBOM artifact for every push/PR
  - Bandit runs (non‑blocking) + summary
  - Guard workflow blocks committing built site artifacts to `main`
- Code quality:
  - mypy re‑enabled in CI; type‑clean codebase
  - Pre‑commit hooks (Ruff lint/format, mypy src‑only)
- Docs/visibility:
  - Security Scanning and SBOM badges in README

## Key Messages

- Privacy & Local‑First: all data lives on your machine; no cloud; human‑readable formats
- Human‑like Memory: temporal decay with reinforcement; promotion to Obsidian Markdown
- Transparent Infrastructure: SBOM, security scans, type checking, pre‑commit quality gates

## Links

- Repo: https://github.com/simplemindedbot/mnemex
- Docs site: https://simplemindedbot.github.io/mnemex/
- Release: https://github.com/simplemindedbot/mnemex/releases/tag/v0.4.0

## Next Milestones (0.5.0)

- Cross‑platform testing (Windows/Linux)
- Performance benchmarks/optimizations
- Hardened error handling and file locking

