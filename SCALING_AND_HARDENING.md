# Scaling and Hardening CortexGraph

This report summarizes practical strategies to scale CortexGraph for heavier workloads and harden it for production use, while respecting its design constraints:

- Local-first, JSONL-only storage (no databases)
- MCP server model (short-lived tool calls, client-controlled lifecycle)
- Strict security posture (no implicit network access, least privilege on disk)

It is organized as:

1. Deployment and topology options
2. Storage layout and scaling patterns
3. Performance tuning and concurrency
4. Security hardening and operational controls
5. Observability, testing, and upgrade strategy

Where relevant, file paths and configuration options refer to the current codebase and docs (e.g., `docs/deployment.md`, `docs/configuration.md`, `PERFORMANCE_OPTIMIZATIONS.md`).

---

## 1. Deployment and Topology

### 1.1 Recommended Baseline Deployment

For a single user or small team:

- Install via UV tool (preferred for isolation and updates):
  - `uv tool install cortexgraph`
- Configuration location:
  - Primary: `~/.config/cortexgraph/.env`
  - Fallback (dev only): `./.env` in the project directory
- Integrate as an MCP server:
  - Claude Desktop / VS Code: `"command": "cortexgraph"` for tool installs
  - Development: `"command": "uv", "args": ["--directory", "/path/to/cortexgraph", "run", "cortexgraph"]`

This baseline already isolates CortexGraph in a dedicated environment and keeps all user data local (`~/.config/cortexgraph/jsonl` and your Obsidian vault).

### 1.2 Topology Patterns

Because CortexGraph uses local JSONL and Markdown files rather than a central database, scaling is primarily a matter of topology and filesystem layout.

**Pattern A: Per-User Instances (Recommended)**

- Each human user has:
  - Their own MCP client (Claude Desktop, VS Code, etc.)
  - Their own CortexGraph configuration and storage directory:
    - `~/.config/cortexgraph/jsonl` for STM
    - `LTM_VAULT_PATH` pointing to a personal Obsidian vault
- Benefits:
  - Strong isolation between users
  - No cross-user contention on JSONL files
  - Simple backup and restore per user
- Use when:
  - You have multiple people on the same machine or shared environment
  - You do not need shared memory between users

**Pattern B: Shared “Team Memory” Instance**

- One CortexGraph instance with:
  - Shared `CORTEXGRAPH_STORAGE_PATH` on a team-accessible filesystem
  - Shared `LTM_VAULT_PATH` pointing to a team Obsidian vault
- Accessed by multiple MCP clients using the same command path.
- Requirements:
  - Underlying filesystem supports safe concurrent access (e.g., local disk or properly configured network storage with file locking semantics).
  - Cooperative usage model (avoid running multiple long-lived CortexGraph processes writing to the same JSONL directory simultaneously).
- Use when:
  - You want a shared memory graph for a team or project
  - Trust boundaries among users are relatively strong

**Pattern C: Multi-Instance with Sharded Storage**

- You run N CortexGraph instances, each with its own storage root:
  - Example shard keys: user ID, project name, or tenant ID.
- The MCP client or a higher-level orchestration layer chooses which CortexGraph instance to talk to based on the shard key.
- Benefits:
  - Horizontal scaling without modifying CortexGraph’s storage layer
  - Clear boundaries between tenants/projects
- Use when:
  - You have many independent tenants
  - Storage volumes per tenant may grow large

> Note: Because CortexGraph is designed as a local MCP server with JSONL storage, **do not introduce SQLite or other external databases**. Scale out by topology (more instances, separate storage paths), not by replacing the storage backend.

---

## 2. Storage Layout and Scaling

### 2.1 Storage Paths

Key paths (see `docs/configuration.md` and `docs/deployment.md`):

- STM JSONL directory:
  - `CORTEXGRAPH_STORAGE_PATH=~/.config/cortexgraph/jsonl`
- LTM vault:
  - `LTM_VAULT_PATH=~/Documents/Obsidian/Vault`
- LTM index:
  - `LTM_INDEX_PATH=~/.config/cortexgraph/ltm_index.jsonl`

For scaling and safety:

- Use absolute paths in `.env` for shared or non-default locations.
- Keep STM and LTM on the same physical disk for simplicity unless you have a strong reason to separate them (e.g., SSD for STM, larger HDD for LTM).

### 2.2 Storage Sizing and Growth Controls

**JSONL STM files (`memories.jsonl`, `relations.jsonl`):**

- Growth is controlled by:
  - Decay and garbage collection thresholds:
    - `CORTEXGRAPH_FORGET_THRESHOLD`
    - Decay model parameters (`CORTEXGRAPH_DECAY_MODEL`, `CORTEXGRAPH_*`).
  - Promotion rules:
    - `CORTEXGRAPH_PROMOTE_THRESHOLD`
    - `CORTEXGRAPH_PROMOTE_USE_COUNT`
    - `CORTEXGRAPH_PROMOTE_TIME_WINDOW`
- For heavy usage or long-lived systems:
  - Prefer slightly higher forget thresholds (e.g., 0.06–0.08) to keep STM manageable.
  - Run compaction and maintenance regularly (see `cortexgraph-maintenance`).

**LTM Vault:**

- Markdown files accumulate as memories are promoted.
- Scaling mainly depends on:
  - Git backups and pruning strategy
  - Obsidian vault organization (folders, tags)

### 2.3 Maintenance and Compaction

Use the maintenance CLI (see `docs/deployment.md`):

- `cortexgraph-maintenance stats`
  - Inspect JSONL file sizes, active counts, and compaction hints.
- `cortexgraph-maintenance compact`
  - Rewrite JSONL files without tombstones/duplicates.

Recommended schedule:

- **Daily or Weekly**:
  - Run stats and compact if file sizes or tombstones grow significantly.
- **Monthly**:
  - Review archived memories and promotion behavior.
  - Adjust thresholds if STM is growing too fast or too slow.

For large stores (thousands of memories or more):

- Increase compaction frequency.
- Consider per-user or per-tenant shard directories to limit individual file sizes.

---

## 3. Performance Tuning and Concurrency

`PERFORMANCE_OPTIMIZATIONS.md` describes several optimizations already implemented:

- Embedding model caching
- Lazy loading of LTM index
- Buffered JSONL I/O and batch operations
- Tag-based indexing and pagination
- Async I/O support
- Background task manager
- Performance monitoring utilities

The following recommendations focus on how to **use** and **configure** these capabilities in a scalable deployment.

### 3.1 Configuration-Level Tuning

Key performance-related configuration options (see `PERFORMANCE_OPTIMIZATIONS.md` and `config.py`):

- `batch_size` — batch size for bulk operations (default: 100)
- `cache_size` — in-memory cache size (default: 1000)
- `enable_async_io` — enable async I/O for better concurrency
- `search_timeout` — search timeout in seconds (default: 5.0)

Guidelines:

- For heavier search workloads:
  - Increase `cache_size` to keep more frequently accessed memories and tags in memory.
  - Ensure `enable_async_io` is true to avoid blocking operations.
  - Tune `search_timeout` to a value that balances responsiveness with completeness.
- For heavy write workloads (many memories per session):
  - Use batch operations where possible (e.g., batch saving in tools/clients).
  - Keep `batch_size` moderate (50–200) to avoid large spikes in memory usage.

### 3.2 MCP-Level Concurrency

In MCP usage, CortexGraph is invoked via tools that run requests in isolation:

- Each request should be treated as short-lived; the server’s internal caching smooths repeated operations within the same process.
- To avoid JSONL write contention:
  - Prefer a **single long-lived CortexGraph process per storage directory**, rather than many short-lived processes writing concurrently.
  - If multiple MCP clients share a storage path, route them to the same `cortexgraph` command, not multiple independent processes each writing to the same files.

If you need true parallelism with separate processes:

- Use sharding or per-user paths so each process writes to its own JSONL files.
- Avoid multiple processes writing to the same JSONL directory unless you have verified filesystem-level locking semantics and are comfortable with the risk.

### 3.3 Embeddings and Semantic Search

Embeddings are optional and can be resource-intensive:

- Enable:
  - `CORTEXGRAPH_ENABLE_EMBEDDINGS=true`
  - `CORTEXGRAPH_EMBED_MODEL=all-MiniLM-L6-v2` (recommended lightweight model)
- Considerations:
  - First run will download the model (~50MB).
  - Embedding computations can be CPU-heavy; on constrained machines, limit embedding usage or batch embedding operations.
- Scaling strategies:
  - Use embeddings only where they add clear value (semantic search, clustering).
  - For low-end systems or large multi-tenant setups, consider disabling embeddings or limiting them to specific shards/users.

### 3.4 Background Tasks and Long-Running Operations

For expensive operations (index building, compaction, clustering):

- Use the background task manager (see `background.py`) to avoid blocking active requests.
- Schedule heavy jobs during off-peak hours:
  - LTM index rebuild
  - Large-scale clustering and consolidation
  - Full compaction of JSONL storage

Monitor performance metrics via:

- `get_performance_metrics()` and `reset_performance_metrics()` (see `performance.py` and `tools/performance.py`).
- Track average latencies and operation counts over time to validate tuning changes.

---

## 4. Security Hardening

CortexGraph already follows a strong security posture (see `docs/security.md` and `SECURITY.md`). The recommendations below focus on operationalizing and extending that posture.

### 4.1 Process Isolation and Privileges

- Run CortexGraph under a **dedicated OS user** where feasible:
  - Only this user should have read/write access to:
    - `~/.config/cortexgraph/`
    - The configured `LTM_VAULT_PATH` (or a subdirectory).
  - Avoid running under privileged accounts (e.g., root) unless absolutely necessary.
- For containerized deployments:
  - Use non-root containers.
  - Mount `~/.config/cortexgraph/` and the Obsidian vault as volumes with minimal necessary permissions.

### 4.2 Filesystem Permissions

Enforce restrictive permissions consistently:

- Config:
  - `.env` files should be `0600` (owner read/write only).
- Storage directories:
  - JSONL storage (`CORTEXGRAPH_STORAGE_PATH`) should be `0700`.
  - LTM vault should match your Obsidian practices; at minimum, only trusted users should have access.

On shared systems:

- Avoid placing `CORTEXGRAPH_STORAGE_PATH` or `LTM_VAULT_PATH` in world-readable locations.
- If using a shared “team memory” instance, treat the storage directory as containing sensitive personal data and restrict access accordingly.

### 4.3 Configuration and Secrets

- Never commit `.env` files or storage data to version control.
- When sharing diagnostics:
  - Redact file paths, personal data, and any sensitive content.
  - Prefer synthetic or anonymized examples.
- For Git-based backups of the Obsidian vault:
  - Use private repositories.
  - Consider client-side encryption if storing sensitive data off-device.

### 4.4 Network and Integration Boundaries

- CortexGraph is designed to run locally with no outbound network access by default:
  - Do not add remote API calls inside core modules or tools.
  - If you need network functionality (e.g., downloading models), confine it to explicit setup steps or separate scripts.
- Integration with MCP clients:
  - Limit which tools are exposed to the assistant if you have stricter security requirements.
  - Review tool definitions for potential data exfiltration paths (e.g., anything that can read arbitrary files).

### 4.5 Supply Chain and CI Hardening

Current measures (see `docs/security.md`):

- Dependabot, pip-audit, Bandit, CodeQL, SBOM generation roadmap.

Additional hardening steps:

- Pin dependencies more tightly in `pyproject.toml` once the ecosystem stabilizes.
- Enable SBOM-based scanning in CI (using `snyk_sbom_scan` or similar).
- Periodically review:
  - GitHub security advisories
  - CI logs for Bandit, CodeQL, and pip-audit

---

## 5. Observability, Testing, and Upgrade Strategy

### 5.1 Logging and Metrics

- Capture server logs:

  ```bash
  cortexgraph 2>&1 | tee ~/.config/cortexgraph/server.log
  ```

- Use performance metrics APIs:
  - Track operation latencies (search, save, clustering).
  - Watch for regressions after configuration changes or upgrades.

For multi-instance setups:

- Standardize log locations and formats so you can aggregate or inspect logs across instances.

### 5.2 Testing Under Load

Before rolling out configuration or topology changes:

- Generate synthetic workloads:
  - Scripts that save many memories, run diverse searches, and exercise consolidation/GC.
  - Use realistic tags and content sizes.
- Measure:
  - End-to-end latencies for key operations.
  - Growth in JSONL file sizes.
  - Memory usage of the `cortexgraph` process.

### 5.3 Upgrade and Migration Strategy

Because storage is JSONL and Markdown:

- Upgrades are primarily **schema-additive** and backward compatible.
- Good practice for upgrades:
  - Backup `~/.config/cortexgraph/jsonl/` and relevant parts of your Obsidian vault.
  - Upgrade CortexGraph (via `uv tool install` or `pip`).
  - Run tests if you are on a dev install (`PYTHONPATH=src pytest`).
  - Check `cortexgraph-maintenance stats` for inconsistencies.

For multi-instance deployments:

- Roll out updates gradually:
  - Upgrade one instance.
  - Verify behavior under typical workload.
  - Then upgrade remaining instances.

---

## 6. Summary Checklist

**Topology and Storage**

- [ ] Choose per-user, team, or sharded instances.
- [ ] Set explicit `CORTEXGRAPH_STORAGE_PATH`, `LTM_VAULT_PATH`, `LTM_INDEX_PATH`.
- [ ] Tune decay and promotion thresholds for expected load.
- [ ] Schedule regular `cortexgraph-maintenance stats` and `compact`.

**Performance**

- [ ] Enable async I/O and tune `batch_size`, `cache_size`, `search_timeout`.
- [ ] Use a single long-lived process per storage directory.
- [ ] Decide whether embeddings are necessary and configure accordingly.
- [ ] Run heavy operations via background tasks during off-peak hours.

**Security**

- [ ] Run under a dedicated OS user with minimal privileges.
- [ ] Enforce `0600` on `.env` and `0700` on storage directories.
- [ ] Keep all data local and avoid adding implicit network calls.
- [ ] Review integration/tool exposure for potential data leaks.

**Operations**

- [ ] Capture logs and monitor performance metrics.
- [ ] Test configuration changes under synthetic load.
- [ ] Back up JSONL and vault content before upgrades.
- [ ] Roll out upgrades gradually, especially in multi-instance deployments.

This checklist, combined with the detailed sections above, provides a concrete path to scaling CortexGraph responsibly while maintaining its privacy-preserving, local-first design and strong security posture.

