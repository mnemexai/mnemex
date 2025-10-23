# Deployment Guide

## Production Installation (Recommended)

### Prerequisites

- Python 3.10+
- `uv` package manager

### Installation Options

**Recommended: UV Tool Install from PyPI**

```bash
# Install from PyPI (recommended - fast, isolated, automatic updates)
uv tool install mnemex
```

**Alternative Methods:**

```bash
# Using pipx (similar isolation, cross-platform)
pipx install mnemex

# Using pip (traditional, installs in current environment)
pip install mnemex

# From GitHub (latest development version)
uv tool install git+https://github.com/simplemindedbot/mnemex.git
```

All methods install `mnemex` and all 7 CLI commands. Configuration goes in `~/.config/mnemex/.env`.

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
git clone https://github.com/simplemindedbot/mnemex.git
cd mnemex

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
pytest --cov=mnemex --cov-report=html

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
    "mnemex": {
      "command": "mnemex"
    }
  }
}
```

**For development (editable install):**

```json
{
  "mcpServers": {
    "mnemex": {
      "command": "uv",
      "args": ["--directory", "/path/to/mnemex", "run", "mnemex"],
      "env": {"PYTHONPATH": "/path/to/mnemex/src"}
    }
  }
}
```

**Configuration:** All settings go in `~/.config/mnemex/.env`, not in the MCP config. See `.env.example` for options.

**Troubleshooting: Command Not Found**

If Claude Desktop shows `spawn mnemex ENOENT` errors, the `mnemex` command isn't in Claude Desktop's PATH.

GUI applications on macOS/Linux don't inherit shell PATH configurations (`.zshrc`, `.bashrc`, etc.). Claude Desktop only searches:
- `/usr/local/bin`
- `/opt/homebrew/bin` (macOS)
- `/usr/bin`, `/bin`, `/usr/sbin`, `/sbin`

If `uv tool install` placed `mnemex` in `~/.local/bin/` or another custom location, Claude Desktop can't find it.

**Solution: Use absolute path**

```bash
# Find where mnemex is installed
which mnemex
# Example output: /Users/username/.local/bin/mnemex
```

Update Claude config with the absolute path:

```json
{
  "mcpServers": {
    "mnemex": {
      "command": "/Users/username/.local/bin/mnemex"
    }
  }
}
```

**Alternative: System-wide install**

```bash
# Option 1: Symlink to system location
sudo ln -s ~/.local/bin/mnemex /usr/local/bin/mnemex

# Option 2: Install with UV to system location (requires admin)
sudo uv tool install git+https://github.com/simplemindedbot/mnemex.git
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
    "mnemex": {
      "command": "mnemex"
    }
  }
}
```

**For development:**

```json
{
  "mcpServers": {
    "mnemex": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\mnemex", "run", "mnemex"],
      "env": {"PYTHONPATH": "C:\\path\\to\\mnemex\\src"}
    }
  }
}
```

### VSCode with MCP Extension

**For UV tool install:**

```json
{
  "mcp.servers": {
    "mnemex": {
      "command": "mnemex"
    }
  }
}
```

**For development:**

```json
{
  "mcp.servers": {
    "mnemex": {
      "command": "uv",
      "args": ["--directory", "${workspaceFolder}", "run", "mnemex"],
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
MNEMEX_DECAY_LAMBDA=8.02e-6  # 1-day half-life
MNEMEX_FORGET_THRESHOLD=0.03
MNEMEX_PROMOTE_THRESHOLD=0.7
MNEMEX_PROMOTE_USE_COUNT=3
```

### Profile 2: Standard (Default)

Balanced for general use.

```bash
# .env
MNEMEX_DECAY_LAMBDA=2.673e-6  # 3-day half-life
MNEMEX_FORGET_THRESHOLD=0.05
MNEMEX_PROMOTE_THRESHOLD=0.65
MNEMEX_PROMOTE_USE_COUNT=5
```

### Profile 3: Long-Term STM (Weekly)

For information that should persist longer.

```bash
# .env
MNEMEX_DECAY_LAMBDA=1.145e-6  # 7-day half-life
MNEMEX_FORGET_THRESHOLD=0.08
MNEMEX_PROMOTE_THRESHOLD=0.6
MNEMEX_PROMOTE_USE_COUNT=7
```

### Profile 4: With Embeddings

Enable semantic search and clustering.

```bash
# .env
MNEMEX_ENABLE_EMBEDDINGS=true
MNEMEX_EMBED_MODEL=all-MiniLM-L6-v2
MNEMEX_SEMANTIC_HI=0.88
MNEMEX_SEMANTIC_LO=0.78
MNEMEX_CLUSTER_LINK_THRESHOLD=0.83
```

**Note**: First run will download the model (~50MB).

---

## Decay Model Configuration

Select decay behavior via `MNEMEX_DECAY_MODEL`:

```bash
# 1) Power-Law (default; heavier tail, most human)
MNEMEX_DECAY_MODEL=power_law
MNEMEX_PL_ALPHA=1.1              # shape (typical 1.0–1.2)
MNEMEX_PL_HALFLIFE_DAYS=3.0      # target half-life used to derive t0

# 2) Exponential (lighter tail, forgets sooner)
MNEMEX_DECAY_MODEL=exponential
MNEMEX_DECAY_LAMBDA=2.673e-6     # ~3-day half-life (ln(2)/(3*86400))

# 3) Two-Component (fast early forgetting + heavier tail)
MNEMEX_DECAY_MODEL=two_component
MNEMEX_TC_LAMBDA_FAST=1.603e-5   # ~12-hour half-life
MNEMEX_TC_LAMBDA_SLOW=1.147e-6   # ~7-day half-life
MNEMEX_TC_WEIGHT_FAST=0.7        # weight of fast component (0–1)

# Shared parameters
MNEMEX_DECAY_BETA=0.6            # sub-linear use count weight
MNEMEX_FORGET_THRESHOLD=0.05     # GC threshold
MNEMEX_PROMOTE_THRESHOLD=0.65    # promotion threshold
MNEMEX_PROMOTE_USE_COUNT=5
MNEMEX_PROMOTE_TIME_WINDOW=14
```

Tuning tips:
- Power-Law has a heavier tail; consider a slightly higher `MNEMEX_FORGET_THRESHOLD` (e.g., 0.06–0.08) or reduce `MNEMEX_PL_HALFLIFE_DAYS` to maintain GC budget.
- Two-Component forgets very recent items faster; validate promotion and GC rates and adjust thresholds as needed.

---

## Storage Management

### Location

Default directory: `~/.config/mnemex/jsonl/`

Custom location via `MNEMEX_STORAGE_PATH` environment variable.

### Backup

```bash
# Simple backup
cp ~/.config/mnemex/jsonl/memories.jsonl ~/.config/mnemex/backups/memories.jsonl.backup
cp ~/.config/mnemex/jsonl/relations.jsonl ~/.config/mnemex/backups/relations.jsonl.backup

# Timestamped backup
cp ~/.config/mnemex/jsonl/memories.jsonl ~/.config/mnemex/backups/memories.jsonl.$(date +%Y%m%d)
cp ~/.config/mnemex/jsonl/relations.jsonl ~/.config/mnemex/backups/relations.jsonl.$(date +%Y%m%d)

# Automated daily backup (cron)
0 2 * * * cp ~/.config/mnemex/jsonl/memories.jsonl ~/.config/mnemex/backups/memories.jsonl.$(date +\%Y\%m\%d) && cp ~/.config/mnemex/jsonl/relations.jsonl ~/.config/mnemex/backups/relations.jsonl.$(date +\%Y\%m\%d)
```

### Migration

Not applicable. JSONL storage requires no schema migrations.

### Reset Storage

```bash
# WARNING: This deletes all memories
rm -rf ~/.config/mnemex/jsonl

# Next run will create fresh storage files
mnemex
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
mnemex-maintenance stats

# Compact JSONL (rewrite files without tombstones/duplicates)
mnemex-maintenance compact

# With explicit path
mnemex-maintenance --storage-path ~/.config/mnemex/jsonl stats
```

### Daily Maintenance (Automated)

Create a maintenance script `~/.config/mnemex/maintenance.sh`:

```bash
#!/bin/bash
# Mnemex Server Daily Maintenance

LOG_FILE="$HOME/.config/mnemex/maintenance.log"
echo "=== Maintenance run at $(date) ===" >> "$LOG_FILE"

# Backup storage
cp "$HOME/.config/mnemex/jsonl/memories.jsonl" "$HOME/.config/mnemex/backups/memories.jsonl.$(date +%Y%m%d)"
cp "$HOME/.config/mnemex/jsonl/relations.jsonl" "$HOME/.config/mnemex/backups/relations.jsonl.$(date +%Y%m%d)"

# Log stats
echo "Storage files: $(ls -l $HOME/.config/mnemex/jsonl | wc -l)" >> "$LOG_FILE"
```

Schedule with cron:
```bash
# Run daily at 2 AM
0 2 * * * ~/.config/mnemex/maintenance.sh
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

Use `mnemex-search --verbose` or write a small script that uses `JSONLStorage.get_storage_stats()` for counts and compaction hints.

### Logs

Server logs are written to stderr. Capture with:

```bash
mnemex 2>&1 | tee ~/.config/mnemex/server.log
```

Or configure in MCP settings with log file output.

---

## Troubleshooting

### Server won't start

1. Check Python version: `python --version` (need 3.10+)
2. Check dependencies: `pip list | grep mcp`
3. Check storage path exists: `ls -la ~/.config/mnemex/jsonl`
4. Check permissions on storage files

### Embeddings not working

1. Install embeddings support: `pip install sentence-transformers`
2. Check model downloads: `~/.cache/torch/sentence_transformers/`
3. Verify `MNEMEX_ENABLE_EMBEDDINGS=true` in config
4. Check logs for model loading errors

### Promotion fails

1. Verify `BASIC_MEMORY_PATH` is set and valid
2. Check vault directory exists and is writable
3. Verify Obsidian vault path is correct
4. Check for file permission errors

### Storage issues

1. Restore from `~/.config/mnemex/backups/memories.jsonl.*` and `relations.jsonl.*`.
2. To rebuild fresh storage, remove `~/.config/mnemex/jsonl` and restart.

---

## Performance Tuning

### For Large Stores (> 5000 memories)

```bash
Use `JSONLStorage.compact()` periodically to reclaim space from tombstones and duplicates. Consider a higher `MNEMEX_FORGET_THRESHOLD` for aggressive GC.
```

### For Semantic Search

```bash
# Use lighter model
MNEMEX_EMBED_MODEL=all-MiniLM-L6-v2

# Or faster model (less accurate)
MNEMEX_EMBED_MODEL=paraphrase-MiniLM-L3-v2
```

### Memory Usage

Typical memory footprint:
- Base server: ~20-30MB
- With embeddings model: ~70-100MB
- Storage index in memory: ~1KB per memory (typical)

---

## Security Considerations

1. **Database**: Contains all short-term memories in plaintext
   - Store in user-only directory (`chmod 700 ~/.config/mnemex`)
   - Don't commit database to version control

2. **Obsidian Vault**: Promoted memories written to vault
   - Consider vault encryption if storing sensitive data

3. **MCP Communication**: Stdio transport (local only)
   - No network exposure by default

4. **Secrets**: Don't store API keys or credentials in memories
   - Use stoplist to prevent promotion of sensitive patterns
