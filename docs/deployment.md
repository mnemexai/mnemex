# Deployment Guide

## Local Development Setup

### Prerequisites

- Python 3.10+
- `uv` (recommended) or `pip`
- Git

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd stm-server

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
pytest --cov=stm_server --cov-report=html

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

Add STM server:

```json
{
  "mcpServers": {
    "stm": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/your-username/path/to/stm-server",
        "run",
        "stm-server"
      ],
      "env": {
        "STM_DB_PATH": "/Users/your-username/.stm/memories.db",
        "BASIC_MEMORY_PATH": "/Users/your-username/Documents/Obsidian/Vault",
        "STM_ENABLE_EMBEDDINGS": "false"
      }
    }
  }
}
```

Restart Claude Desktop after configuration.

### Claude Desktop (Windows)

Configuration file location:
```
%APPDATA%\Claude\claude_desktop_config.json
```

Configuration (adjust paths):

```json
{
  "mcpServers": {
    "stm": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\YourName\\stm-server",
        "run",
        "stm-server"
      ],
      "env": {
        "STM_DB_PATH": "C:\\Users\\YourName\\.stm\\memories.db",
        "BASIC_MEMORY_PATH": "C:\\Users\\YourName\\Documents\\Obsidian\\Vault"
      }
    }
  }
}
```

### VSCode with MCP Extension

Configuration in `.vscode/settings.json`:

```json
{
  "mcp.servers": {
    "stm": {
      "command": "uv",
      "args": ["--directory", "${workspaceFolder}/stm-server", "run", "stm-server"],
      "env": {
        "STM_DB_PATH": "${env:HOME}/.stm/memories.db"
      }
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
STM_DECAY_LAMBDA=8.02e-6  # 1-day half-life
STM_FORGET_THRESHOLD=0.03
STM_PROMOTE_THRESHOLD=0.7
STM_PROMOTE_USE_COUNT=3
```

### Profile 2: Standard (Default)

Balanced for general use.

```bash
# .env
STM_DECAY_LAMBDA=2.673e-6  # 3-day half-life
STM_FORGET_THRESHOLD=0.05
STM_PROMOTE_THRESHOLD=0.65
STM_PROMOTE_USE_COUNT=5
```

### Profile 3: Long-Term STM (Weekly)

For information that should persist longer.

```bash
# .env
STM_DECAY_LAMBDA=1.145e-6  # 7-day half-life
STM_FORGET_THRESHOLD=0.08
STM_PROMOTE_THRESHOLD=0.6
STM_PROMOTE_USE_COUNT=7
```

### Profile 4: With Embeddings

Enable semantic search and clustering.

```bash
# .env
STM_ENABLE_EMBEDDINGS=true
STM_EMBED_MODEL=all-MiniLM-L6-v2
STM_SEMANTIC_HI=0.88
STM_SEMANTIC_LO=0.78
STM_CLUSTER_LINK_THRESHOLD=0.83
```

**Note**: First run will download the model (~50MB).

---

## Database Management

### Location

Default: `~/.stm/memories.db`

Custom location via `STM_DB_PATH` environment variable.

### Backup

```bash
# Simple backup
cp ~/.stm/memories.db ~/.stm/memories.db.backup

# Timestamped backup
cp ~/.stm/memories.db ~/.stm/memories.db.$(date +%Y%m%d)

# Automated daily backup (cron)
0 2 * * * cp ~/.stm/memories.db ~/.stm/backups/memories.db.$(date +\%Y\%m\%d)
```

### Migration

Schema migrations are handled automatically on startup.

To force a specific version:

```python
from stm_server.storage.database import Database
from stm_server.storage.migrations import apply_migrations

db = Database()
db.connect()
apply_migrations(db.conn, backup_path="backup.db")
```

### Reset Database

```bash
# WARNING: This deletes all memories
rm ~/.stm/memories.db

# Next run will create fresh database
stm-server
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

### Daily Maintenance (Automated)

Create a maintenance script `~/.stm/maintenance.sh`:

```bash
#!/bin/bash
# STM Server Daily Maintenance

LOG_FILE="$HOME/.stm/maintenance.log"
echo "=== Maintenance run at $(date) ===" >> "$LOG_FILE"

# Backup database
cp "$HOME/.stm/memories.db" "$HOME/.stm/backups/memories.db.$(date +%Y%m%d)"

# Log stats
echo "Total memories: $(sqlite3 ~/.stm/memories.db 'SELECT COUNT(*) FROM memories')" >> "$LOG_FILE"
echo "Active memories: $(sqlite3 ~/.stm/memories.db "SELECT COUNT(*) FROM memories WHERE status='active'")" >> "$LOG_FILE"
```

Schedule with cron:
```bash
# Run daily at 2 AM
0 2 * * * ~/.stm/maintenance.sh
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

### Database Stats

```bash
# Count memories
sqlite3 ~/.stm/memories.db "SELECT COUNT(*) FROM memories"

# Count by status
sqlite3 ~/.stm/memories.db "SELECT status, COUNT(*) FROM memories GROUP BY status"

# Recent memories
sqlite3 ~/.stm/memories.db "SELECT id, content, use_count FROM memories ORDER BY created_at DESC LIMIT 10"
```

### Logs

Server logs are written to stderr. Capture with:

```bash
stm-server 2>&1 | tee ~/.stm/server.log
```

Or configure in MCP settings with log file output.

---

## Troubleshooting

### Server won't start

1. Check Python version: `python --version` (need 3.10+)
2. Check dependencies: `pip list | grep mcp`
3. Check database path exists: `ls -la ~/.stm/`
4. Check permissions on database file

### Embeddings not working

1. Install embeddings support: `pip install sentence-transformers`
2. Check model downloads: `~/.cache/torch/sentence_transformers/`
3. Verify `STM_ENABLE_EMBEDDINGS=true` in config
4. Check logs for model loading errors

### Promotion fails

1. Verify `BASIC_MEMORY_PATH` is set and valid
2. Check vault directory exists and is writable
3. Verify Obsidian vault path is correct
4. Check for file permission errors

### Database corruption

1. Restore from backup:
   ```bash
   cp ~/.stm/backups/memories.db.YYYYMMDD ~/.stm/memories.db
   ```

2. Or rebuild:
   ```bash
   rm ~/.stm/memories.db
   # Next startup creates fresh database
   ```

---

## Performance Tuning

### For Large Databases (> 5000 memories)

```bash
# Increase SQLite cache
export STM_SQLITE_CACHE_SIZE=10000

# Regular VACUUM
sqlite3 ~/.stm/memories.db "VACUUM"

# More aggressive GC
STM_FORGET_THRESHOLD=0.08
```

### For Semantic Search

```bash
# Use lighter model
STM_EMBED_MODEL=all-MiniLM-L6-v2

# Or faster model (less accurate)
STM_EMBED_MODEL=paraphrase-MiniLM-L3-v2
```

### Memory Usage

Typical memory footprint:
- Base server: ~20-30MB
- With embeddings model: ~70-100MB
- Database in memory: ~1KB per memory (typical)

---

## Security Considerations

1. **Database**: Contains all short-term memories in plaintext
   - Store in user-only directory (`chmod 700 ~/.stm`)
   - Don't commit database to version control

2. **Obsidian Vault**: Promoted memories written to vault
   - Consider vault encryption if storing sensitive data

3. **MCP Communication**: Stdio transport (local only)
   - No network exposure by default

4. **Secrets**: Don't store API keys or credentials in memories
   - Use stoplist to prevent promotion of sensitive patterns
