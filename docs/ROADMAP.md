# CortexGraph Roadmap

This document outlines the development roadmap for CortexGraph. For detailed implementation notes, see [future_roadmap.md](future_roadmap.md).

## Version 1.0.0 (Released ✅)

**Status:** Production-ready, feature-complete

- ✅ 11 MCP tools for memory management
- ✅ Temporal decay with 3 models (power-law, exponential, two-component)
- ✅ JSONL storage with in-memory indexing
- ✅ Algorithmic memory consolidation
- ✅ Unified search across STM and LTM
- ✅ Git integration for backups
- ✅ Obsidian vault integration
- ✅ 7 CLI commands
- ✅ Complete documentation suite
- ✅ CI/CD with GitHub Actions

## Version 1.1.0 (Planned - Q1 2026)

**Focus:** Stability, Testing, Security

### High Priority

- [ ] **Security Hardening** ([#6](https://github.com/prefrontal-systems/cortexgraph/issues/6))
  - Dependency scanning (Dependabot, safety, pip-audit)
  - Code security scanning (Bandit, Semgrep)
  - Supply chain verification (SBOM)
  - SECURITY.md policy

- [ ] **Fix mypy Type Checking** ([#1](https://github.com/prefrontal-systems/cortexgraph/issues/1))
  - Fix 30+ type errors
  - Re-enable mypy in CI

- [ ] **Improve Test Coverage** ([#7](https://github.com/prefrontal-systems/cortexgraph/issues/7))
  - Target: 80%+ coverage (currently 40%)
  - CLI tool tests
  - Integration tests
  - Error handling tests

- [ ] **Production Hardening** ([#8](https://github.com/prefrontal-systems/cortexgraph/issues/8))
  - File corruption handling
  - Graceful degradation
  - File locking for concurrent access
  - Better logging
  - Configuration validation

### Medium Priority

- [ ] **Platform Testing** ([#9](https://github.com/prefrontal-systems/cortexgraph/issues/9))
  - Windows testing (community help needed)
  - Linux testing (community help needed)
  - Cross-platform bug fixes

- [ ] **Performance Optimizations** ([#4](https://github.com/prefrontal-systems/cortexgraph/issues/4))
  - Benchmark suite
  - Tag/entity indexing
  - Embedding cache
  - Score caching

## Version 1.2.0 (Planned - Q2 2026)

**Focus:** Advanced Features, User Experience

### High Priority

- [ ] **Spaced Repetition** ([#2](https://github.com/prefrontal-systems/cortexgraph/issues/2))
  - Review scheduling
  - Review queue tool
  - Adaptive intervals (SM-2 inspired)

- [ ] **Adaptive Decay Parameters** ([#3](https://github.com/prefrontal-systems/cortexgraph/issues/3))
  - Category-based decay profiles
  - Usage-pattern learning
  - Auto-detection from tags/content

### Low Priority

- [ ] **LLM-Assisted Consolidation** ([#5](https://github.com/prefrontal-systems/cortexgraph/issues/5))
  - Optional LLM-powered merge decisions
  - Semantic understanding for better merges
  - Opt-in feature

## Version 2.0.0 (Future)

**Focus:** Advanced AI Features, Ecosystem Integration

- Machine learning for decay parameter optimization
- Multi-user support
- API server mode
- Plugins/extensions system
- Integration with popular tools (Raycast, Alfred, etc.)
- Mobile client support (iOS, Android)

---

## Contributing

We welcome contributions! Priority areas:

1. **Platform Testing** - Help test on Windows/Linux ([#9](https://github.com/prefrontal-systems/cortexgraph/issues/9))
2. **Security** - Implement security hardening ([#6](https://github.com/prefrontal-systems/cortexgraph/issues/6))
3. **Testing** - Increase coverage ([#7](https://github.com/prefrontal-systems/cortexgraph/issues/7))

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Links

- [GitHub Issues](https://github.com/prefrontal-systems/cortexgraph/issues)
- [Detailed Roadmap](future_roadmap.md)
- [Documentation](docs/)
- [Contributing Guide](CONTRIBUTING.md)

---

**Last Updated:** 2025-10-09
**Current Version:** 1.0.0
**Next Release:** 1.1.0 (Q1 2026 - Security & Stability)
