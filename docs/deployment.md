# Deployment Guide

## Production Installation (Recommended)

### Prerequisites

- Python 3.10+
- `uv` package manager

### Installation Options

**Recommended: UV Tool Install from PyPI**

```bash
# Install from PyPI (recommended - fast, isolated, automatic updates)
uv tool install cortexgraph
```

**Alternative Methods:**

```bash
# Using pipx (similar isolation, cross-platform)
pipx install cortexgraph

# Using pip (traditional, installs in current environment)
pip install cortexgraph

# From GitHub (latest development version)
uv tool install git+https://github.com/prefrontal-systems/cortexgraph.git
```

All methods install `cortexgraph` and all 7 CLI commands. Configuration goes in `~/.config/cortexgraph/.env`.

---

## Development Setup

### Prerequisites

- Python 3.10+
- `uv` (recommended) or `pip`
- Git

### Editable Installation

**For development only:**

```bash
# Clone the repository
git clone https://github.com/prefrontal-systems/cortexgraph.git
cd cortexgraph

# Install with uv (recommended)
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Edit .env with your settings
vim .env
```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=cortexgraph --cov-report=html

# Run specific test file
pytest tests/test_decay.py

# Run with verbose output
pytest -v
```

---

## MCP Integration

### Claude Desktop (macOS)

Configuration file location:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**For UV tool install (recommended):**

```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "cortexgraph"
    }
  }
}
```

**For development (editable install):**

```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "uv",
      "args": ["--directory", "/path/to/cortexgraph", "run", "cortexgraph"],
      "env": {"PYTHONPATH": "/path/to/cortexgraph/src"}
    }
  }
}
```

**Configuration:** All settings go in `~/.config/cortexgraph/.env`, not in the MCP config. See `.env.example` for options.

**Troubleshooting: Command Not Found**

If Claude Desktop shows `spawn cortexgraph ENOENT` errors, the `cortexgraph` command isn't in Claude Desktop's PATH.

GUI applications on macOS/Linux don't inherit shell PATH configurations (`.zshrc`, `.bashrc`, etc.). Claude Desktop only searches:
- `/usr/local/bin`
- `/opt/homebrew/bin` (macOS)
- `/usr/bin`, `/bin`, `/usr/sbin`, `/sbin`

If `uv tool install` placed `cortexgraph` in `~/.local/bin/` or another custom location, Claude Desktop can't find it.

**Solution: Use absolute path**

```bash
# Find where cortexgraph is installed
which cortexgraph
# Example output: /Users/username/.local/bin/cortexgraph
```

Update Claude config with the absolute path:

```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "/Users/username/.local/bin/cortexgraph"
    }
  }
}
```

**Alternative: System-wide install**

```bash
# Option 1: Symlink to system location
sudo ln -s ~/.local/bin/cortexgraph /usr/local/bin/cortexgraph

# Option 2: Install with UV to system location (requires admin)
sudo uv tool install git+https://github.com/prefrontal-systems/cortexgraph.git
```

Restart Claude Desktop after configuration.

### Claude Desktop (Windows)

Configuration file location:
```
%APPDATA%\Claude\claude_desktop_config.json
```

**For UV tool install:**

```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "cortexgraph"
    }
  }
}
```

**For development:**

```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\cortexgraph", "run", "cortexgraph"],
      "env": {"PYTHONPATH": "C:\\path\\to\\cortexgraph\\src"}
    }
  }
}
```

### VSCode with MCP Extension

**For UV tool install:**

```json
{
  "mcp.servers": {
    "cortexgraph": {
      "command": "cortexgraph"
    }
  }
}
```

**For development:**

```json
{
  "mcp.servers": {
    "cortexgraph": {
      "command": "uv",
      "args": ["--directory", "${workspaceFolder}", "run", "cortexgraph"],
      "env": {"PYTHONPATH": "${workspaceFolder}/src"}
    }
  }
}
```

---

## Configuration Profiles

### Profile 1: Fast Decay (Daily Memory)

Use for information that's only relevant for a day or two.

```bash
# .env
CORTEXGRAPH_DECAY_LAMBDA=8.02e-6  # 1-day half-life
CORTEXGRAPH_FORGET_THRESHOLD=0.03
CORTEXGRAPH_PROMOTE_THRESHOLD=0.7
CORTEXGRAPH_PROMOTE_USE_COUNT=3
```

### Profile 2: Standard (Default)

Balanced for general use.

```bash
# .env
CORTEXGRAPH_DECAY_LAMBDA=2.673e-6  # 3-day half-life
CORTEXGRAPH_FORGET_THRESHOLD=0.05
CORTEXGRAPH_PROMOTE_THRESHOLD=0.65
CORTEXGRAPH_PROMOTE_USE_COUNT=5
```

### Profile 3: Long-Term STM (Weekly)

For information that should persist longer.

```bash
# .env
CORTEXGRAPH_DECAY_LAMBDA=1.145e-6  # 7-day half-life
CORTEXGRAPH_FORGET_THRESHOLD=0.08
CORTEXGRAPH_PROMOTE_THRESHOLD=0.6
CORTEXGRAPH_PROMOTE_USE_COUNT=7
```

### Profile 4: With Embeddings

Enable semantic search and clustering.

```bash
# .env
CORTEXGRAPH_ENABLE_EMBEDDINGS=true
CORTEXGRAPH_EMBED_MODEL=all-MiniLM-L6-v2
CORTEXGRAPH_SEMANTIC_HI=0.88
CORTEXGRAPH_SEMANTIC_LO=0.78
CORTEXGRAPH_CLUSTER_LINK_THRESHOLD=0.83
```

**Note**: First run will download the model (~50MB).

---

## Decay Model Configuration

Select decay behavior via `CORTEXGRAPH_DECAY_MODEL`:

```bash
# 1) Power-Law (default; heavier tail, most human)
CORTEXGRAPH_DECAY_MODEL=power_law
CORTEXGRAPH_PL_ALPHA=1.1              # shape (typical 1.0–1.2)
CORTEXGRAPH_PL_HALFLIFE_DAYS=3.0      # target half-life used to derive t0

# 2) Exponential (lighter tail, forgets sooner)
CORTEXGRAPH_DECAY_MODEL=exponential
CORTEXGRAPH_DECAY_LAMBDA=2.673e-6     # ~3-day half-life (ln(2)/(3*86400))

# 3) Two-Component (fast early forgetting + heavier tail)
CORTEXGRAPH_DECAY_MODEL=two_component
CORTEXGRAPH_TC_LAMBDA_FAST=1.603e-5   # ~12-hour half-life
CORTEXGRAPH_TC_LAMBDA_SLOW=1.147e-6   # ~7-day half-life
CORTEXGRAPH_TC_WEIGHT_FAST=0.7        # weight of fast component (0–1)

# Shared parameters
CORTEXGRAPH_DECAY_BETA=0.6            # sub-linear use count weight
CORTEXGRAPH_FORGET_THRESHOLD=0.05     # GC threshold
CORTEXGRAPH_PROMOTE_THRESHOLD=0.65    # promotion threshold
CORTEXGRAPH_PROMOTE_USE_COUNT=5
CORTEXGRAPH_PROMOTE_TIME_WINDOW=14
```

Tuning tips:
- Power-Law has a heavier tail; consider a slightly higher `CORTEXGRAPH_FORGET_THRESHOLD` (e.g., 0.06–0.08) or reduce `CORTEXGRAPH_PL_HALFLIFE_DAYS` to maintain GC budget.
- Two-Component forgets very recent items faster; validate promotion and GC rates and adjust thresholds as needed.

---

## Storage Management

### Location

Default directory: `~/.config/cortexgraph/jsonl/`

Custom location via `CORTEXGRAPH_STORAGE_PATH` environment variable.

### Backup

```bash
# Simple backup
cp ~/.config/cortexgraph/jsonl/memories.jsonl ~/.config/cortexgraph/backups/memories.jsonl.backup
cp ~/.config/cortexgraph/jsonl/relations.jsonl ~/.config/cortexgraph/backups/relations.jsonl.backup

# Timestamped backup
cp ~/.config/cortexgraph/jsonl/memories.jsonl ~/.config/cortexgraph/backups/memories.jsonl.$(date +%Y%m%d)
cp ~/.config/cortexgraph/jsonl/relations.jsonl ~/.config/cortexgraph/backups/relations.jsonl.$(date +%Y%m%d)

# Automated daily backup (cron)
0 2 * * * cp ~/.config/cortexgraph/jsonl/memories.jsonl ~/.config/cortexgraph/backups/memories.jsonl.$(date +\%Y\%m\%d) && cp ~/.config/cortexgraph/jsonl/relations.jsonl ~/.config/cortexgraph/backups/relations.jsonl.$(date +\%Y\%m\%d)
```

### Migration

Not applicable. JSONL storage requires no schema migrations.

### Reset Storage

```bash
# WARNING: This deletes all memories
rm -rf ~/.config/cortexgraph/jsonl

# Next run will create fresh storage files
cortexgraph
```

---

## Integration with Basic Memory

### Setup

1. Configure Basic Memory MCP server
2. Set `BASIC_MEMORY_PATH` to your Obsidian vault
3. STM will create a `STM/` folder in the vault
4. Promoted memories appear as Markdown notes

### Vault Structure

```
Vault/
├── STM/
│   ├── memory-abc-123.md
│   ├── project-deadline.md
│   └── important-note.md
└── [other Basic Memory notes]
```

### Promotion Workflow

```bash
# 1. Auto-detect promotion candidates
{
  "auto_detect": true,
  "dry_run": true
}

# 2. Review candidates in response

# 3. Promote
{
  "auto_detect": true,
  "dry_run": false
}

# 4. Check vault for new notes
ls ~/Documents/Obsidian/Vault/STM/
```

---

## Maintenance Tasks

### Maintenance CLI

Use the built-in CLI for storage housekeeping:

```bash
# Show JSONL storage stats (active counts, file sizes, compaction hints)
cortexgraph-maintenance stats

# Compact JSONL (rewrite files without tombstones/duplicates)
cortexgraph-maintenance compact

# With explicit path
cortexgraph-maintenance --storage-path ~/.config/cortexgraph/jsonl stats
```

### Daily Maintenance (Automated)

Create a maintenance script `~/.config/cortexgraph/maintenance.sh`:

```bash
#!/bin/bash
# Mnemex Server Daily Maintenance

LOG_FILE="$HOME/.config/cortexgraph/maintenance.log"
echo "=== Maintenance run at $(date) ===" >> "$LOG_FILE"

# Backup storage
cp "$HOME/.config/cortexgraph/jsonl/memories.jsonl" "$HOME/.config/cortexgraph/backups/memories.jsonl.$(date +%Y%m%d)"
cp "$HOME/.config/cortexgraph/jsonl/relations.jsonl" "$HOME/.config/cortexgraph/backups/relations.jsonl.$(date +%Y%m%d)"

# Log stats
echo "Storage files: $(ls -l $HOME/.config/cortexgraph/jsonl | wc -l)" >> "$LOG_FILE"
```

Schedule with cron:
```bash
# Run daily at 2 AM
0 2 * * * ~/.config/cortexgraph/maintenance.sh
```

### Weekly GC

Run garbage collection weekly:

```json
{
  "dry_run": false,
  "archive_instead": true
}
```

### Monthly Review

1. Check promotion candidates
2. Review archived memories
3. Adjust thresholds if needed
4. Clean up old backups

---

## Monitoring

### Storage Stats

Use `cortexgraph-search --verbose` or write a small script that uses `JSONLStorage.get_storage_stats()` for counts and compaction hints.

### Logs

Server logs are written to stderr. Capture with:

```bash
cortexgraph 2>&1 | tee ~/.config/cortexgraph/server.log
```

Or configure in MCP settings with log file output.

---

## Troubleshooting

### Server won't start

1. Check Python version: `python --version` (need 3.10+)
2. Check dependencies: `pip list | grep mcp`
3. Check storage path exists: `ls -la ~/.config/cortexgraph/jsonl`
4. Check permissions on storage files

### Embeddings not working

1. Install embeddings support: `pip install sentence-transformers`
2. Check model downloads: `~/.cache/torch/sentence_transformers/`
3. Verify `CORTEXGRAPH_ENABLE_EMBEDDINGS=true` in config
4. Check logs for model loading errors

### Promotion fails

1. Verify `BASIC_MEMORY_PATH` is set and valid
2. Check vault directory exists and is writable
3. Verify Obsidian vault path is correct
4. Check for file permission errors

### Storage issues

1. Restore from `~/.config/cortexgraph/backups/memories.jsonl.*` and `relations.jsonl.*`.
2. To rebuild fresh storage, remove `~/.config/cortexgraph/jsonl` and restart.

---

## Performance Tuning

### For Large Stores (> 5000 memories)

```bash
Use `JSONLStorage.compact()` periodically to reclaim space from tombstones and duplicates. Consider a higher `CORTEXGRAPH_FORGET_THRESHOLD` for aggressive GC.
```

### For Semantic Search

```bash
# Use lighter model
CORTEXGRAPH_EMBED_MODEL=all-MiniLM-L6-v2

# Or faster model (less accurate)
CORTEXGRAPH_EMBED_MODEL=paraphrase-MiniLM-L3-v2
```

### Memory Usage

Typical memory footprint:
- Base server: ~20-30MB
- With embeddings model: ~70-100MB
- Storage index in memory: ~1KB per memory (typical)

---

## Security Considerations

1. **Database**: Contains all short-term memories in plaintext
   - Store in user-only directory (`chmod 700 ~/.config/cortexgraph`)
   - Don't commit database to version control

2. **Obsidian Vault**: Promoted memories written to vault
   - Consider vault encryption if storing sensitive data

3. **MCP Communication**: Stdio transport (local only)
   - No network exposure by default

4. **Secrets**: Don't store API keys or credentials in memories
   - Use stoplist to prevent promotion of sensitive patterns
