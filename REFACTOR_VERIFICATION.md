# Refactor Verification Report: mnemex → cortexgraph

**Date**: 2025-11-14
**Commit**: 48a8934

## Summary

Comprehensive refactor completed with 60 files changed. Tests passing (pytest verified).

## ✅ Successfully Updated

- [x] Package name and module paths (`src/cortexgraph/`)
- [x] MCP server name in example configs
- [x] Domain name (`mnemex.dev` → `cortexgraph.dev`)
- [x] Logo assets (renamed with git detection)
- [x] Config directory paths (`.config/mnemex` → `.config/cortexgraph`)
- [x] Default index filename (`.mnemex-index.jsonl` → `.cortexgraph-index.jsonl`)
- [x] Documentation (most files)
- [x] Import statements (no `import mnemex` found)

## ❌ Remaining Issues to Fix

### 1. Environment Variable Names

**Issue**: Documentation still references `MNEMEX_*` prefix instead of `CORTEXGRAPH_*`

**Files affected**:
- CLAUDE.md (15+ occurrences)
- README.md (20+ occurrences)
- CHANGELOG.md
- CONTRIBUTING.md
- GEMINI.md
- AGENTS.md
- docs/CHANGELOG.md
- docs/prompt_injection.md
- .github/ISSUE_TEMPLATE/bug_report.yml

**Examples**:
```bash
# Current (wrong):
MNEMEX_STORAGE_PATH=~/.config/cortexgraph/jsonl
MNEMEX_DECAY_MODEL=power_law
MNEMEX_FORGET_THRESHOLD=0.05

# Should be:
CORTEXGRAPH_STORAGE_PATH=~/.config/cortexgraph/jsonl
CORTEXGRAPH_DECAY_MODEL=power_law
CORTEXGRAPH_FORGET_THRESHOLD=0.05
```

**Action required**: Global search-replace `MNEMEX_` → `CORTEXGRAPH_` in documentation files

### 2. VSCode Launch Configuration

**File**: `.vscode/launch.json`

**Issues**:
```json
// Line 8: Wrong module path
"module": "mnemex.server"
// Should be: "module": "cortexgraph.server"

// Line 47: Wrong coverage path
"--cov=mnemex"
// Should be: "--cov=cortexgraph"

// Line 59: Wrong module path
"module": "mnemex.tools.search_unified"
// Should be: "module": "cortexgraph.tools.search_unified"

// Line 71: Wrong module path
"module": "mnemex.storage.maintenance"
// Should be: "module": "cortexgraph.storage.maintenance"
```

**Action required**: Update all module paths and coverage arguments

### 3. GitHub Issue Templates

**File**: `.github/ISSUE_TEMPLATE/bug_report.yml`

**Issues**:
```yaml
# Line 26: Installation instructions reference old package
1. Install mnemex with 'uv tool install git+https://github.com/simplemindedbot/mnemex.git'

# Line 79: Version check references old command
description: Run `mnemex --version` or check your installation
```

**Action required**: Update to `cortexgraph` package/command

**File**: `.github/ISSUE_TEMPLATE/config.yml`

Contains `mnemex` reference (need to check content)

### 4. Claude MCP Config

**File**: `claude.json`

**Issue**:
```json
{
  "mnemex": {
    "command": "mnemex"
  }
}
```

**Should be**:
```json
{
  "cortexgraph": {
    "command": "cortexgraph"
  }
}
```

**Action required**: Update server name and command

### 5. Config Description String

**File**: `src/cortexgraph/config.py` (line 200)

**Issue**:
```python
description="Path to LTM index file (default: vault/.mnemex-index.jsonl)"
```

**Should be**:
```python
description="Path to LTM index file (default: vault/.cortexgraph-index.jsonl)"
```

**Action required**: Update description to match new default

## ✅ Legitimate References (Keep)

These files correctly reference "mnemex" as historical context:

1. **README.md** - Section explaining rename from mnemex to cortexgraph (lines 21-28)
2. **scripts/README_CONVERTER.md** - Legacy converter documentation

## Critical Integration Points Verified

### ✅ Import Paths
- No `import mnemex` found anywhere
- All imports use `cortexgraph`

### ⚠️ Environment Variables
- Code uses correct `CORTEXGRAPH_*` prefix (in `config.py`)
- Documentation NOT updated (see issue #1 above)

### ✅ MCP Server Name
- Example config updated (`examples/claude_desktop_config.json`)
- Personal config NOT updated (`claude.json`) - see issue #4

### ✅ Storage Paths
- Default paths correctly use `~/.config/cortexgraph/`
- Index filename default correctly `.cortexgraph-index.jsonl`

## Recommended Next Steps

1. **Fix environment variable documentation** - Global replace `MNEMEX_` → `CORTEXGRAPH_*`
2. **Update VSCode config** - Fix module paths and coverage arguments
3. **Update GitHub templates** - Fix installation instructions
4. **Update claude.json** - Fix MCP server config
5. **Fix config.py description** - Update default path in docstring
6. **Verify .env.example** - If exists, ensure it uses new prefixes
7. **Check for any .env files** - User configs may need migration notes

## Testing Checklist

- [x] pytest passes (verified by user)
- [ ] VSCode debugger works (after fixing launch.json)
- [ ] MCP server registers with new name
- [ ] Environment variables load correctly
- [ ] Documentation examples work when copy-pasted

## Notes

- Pre-commit hooks passed (ruff, mypy, filesystem checks)
- Git intelligently detected logo renames
- 60 files changed, 376 insertions, 385 deletions
- WARP.md added as symlink
- Dockerfile removed
