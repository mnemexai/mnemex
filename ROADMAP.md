# Mnemex Roadmap

This document outlines the development roadmap for Mnemex. For detailed implementation notes, see [future_roadmap.md](future_roadmap.md).

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

- [ ] **Security Hardening** ([#6](https://github.com/simplemindedbot/cortexgraph/issues/6))
  - Dependency scanning (Dependabot, safety, pip-audit)
  - Code security scanning (Bandit, Semgrep)
  - Supply chain verification (SBOM)
  - SECURITY.md policy

- [ ] **Fix mypy Type Checking** ([#1](https://github.com/simplemindedbot/cortexgraph/issues/1))
  - Fix 30+ type errors
  - Re-enable mypy in CI

- [ ] **Improve Test Coverage** ([#7](https://github.com/simplemindedbot/cortexgraph/issues/7))
  - Target: 80%+ coverage (currently 40%)
  - CLI tool tests
  - Integration tests
  - Error handling tests

- [ ] **Production Hardening** ([#8](https://github.com/simplemindedbot/cortexgraph/issues/8))
  - File corruption handling
  - Graceful degradation
  - File locking for concurrent access
  - Better logging
  - Configuration validation

### Medium Priority

- [ ] **Platform Testing** ([#9](https://github.com/simplemindedbot/cortexgraph/issues/9))
  - Windows testing (community help needed)
  - Linux testing (community help needed)
  - Cross-platform bug fixes

- [ ] **Performance Optimizations** ([#4](https://github.com/simplemindedbot/cortexgraph/issues/4))
  - Benchmark suite
  - Tag/entity indexing
  - Embedding cache
  - Score caching

## Recent Improvements (v0.6.6-dev)

**Completed:** 2025-11-14

### Critical Bug Fixes
- ✅ Fixed use_count=0 scoring bug causing new memories to be immediately GC-eligible
  - Changed formula from `use_count^β` to `(use_count+1)^β`
  - New memories now get grace period (baseline score ~1.0) instead of zero score

### Search & Clustering Enhancements
- ✅ Upgraded search.py with Jaccard similarity fallback
  - Matches clustering.py quality for consistent semantic search
  - Better results even without embeddings
- ✅ Updated review candidate filtering to use text_similarity

### Embeddings & Maintenance
- ✅ Added backfill_embeddings MCP tool for batch embedding generation
- ✅ Achieved 100% embedding coverage (171/171 memories)
- ✅ Verified high-quality clustering with embeddings (10 clusters, cohesion 0.77-0.82)

### Feature Planning
- ✅ Created comprehensive auto-recall specification
- ✅ Feature branch ready: `feature/auto-recall-conversation`

---

## Version 0.7.0 (Planned - Q1 2026)

**Focus:** Natural Language Activation Phase 2

### High Priority

- [ ] **Auto-Recall During Conversation** (Spec created 2025-11-14)
  - Automatic memory search when discussing related topics
  - Silent reinforcement via observe_memory_usage
  - Contextual surfacing (subtle/interactive modes)
  - Cross-domain usage detection (Maslow effect)
  - **Feature branch:** `feature/auto-recall-conversation`
  - **Spec:** [features/auto-recall-conversation.md](features/auto-recall-conversation.md)
  - **Implementation phases:**
    1. Silent Reinforcement (MVP) - Background search + auto-reinforce
    2. Subtle Surfacing - Natural context injection
    3. Interactive Mode - User-controlled surfacing
    4. Cross-Domain Detection - Maslow effect tracking

- [ ] **Conversational Memory Review**
  - Natural review prompts during conversation
  - "Memory check-in" mode for research topics
  - Batch reinforcement by project/tag

## Version 1.2.0 (Planned - Q2 2026)

**Focus:** Advanced Features, User Experience

### High Priority

- [ ] **Enhanced Spaced Repetition** ([#2](https://github.com/simplemindedbot/cortexgraph/issues/2))
  - ✅ Basic natural spaced repetition (v0.5.1 - DONE)
  - Review scheduling improvements
  - Review queue tool
  - Adaptive intervals (SM-2 inspired)

- [ ] **Adaptive Decay Parameters** ([#3](https://github.com/simplemindedbot/cortexgraph/issues/3))
  - Category-based decay profiles
  - Usage-pattern learning
  - Auto-detection from tags/content

### Low Priority

- [ ] **LLM-Assisted Consolidation** ([#5](https://github.com/simplemindedbot/cortexgraph/issues/5))
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

1. **Platform Testing** - Help test on Windows/Linux ([#9](https://github.com/simplemindedbot/cortexgraph/issues/9))
2. **Security** - Implement security hardening ([#6](https://github.com/simplemindedbot/cortexgraph/issues/6))
3. **Testing** - Increase coverage ([#7](https://github.com/simplemindedbot/cortexgraph/issues/7))

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Links

- [GitHub Issues](https://github.com/simplemindedbot/cortexgraph/issues)
- [Detailed Roadmap](future_roadmap.md)
- [Documentation](docs/)
- [Contributing Guide](CONTRIBUTING.md)

---

**Last Updated:** 2025-11-14
**Current Version:** 0.6.5 (Natural Language Activation + Spaced Repetition)
**Next Release:** 0.7.0 (Q1 2026 - Auto-Recall & Conversational Review)
