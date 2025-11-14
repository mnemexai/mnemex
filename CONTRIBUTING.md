# Contributing to Mnemex

Thank you for your interest in contributing to Mnemex! This guide will help you get started with development on Windows, Linux, or macOS.

## Table of Contents

- [🚨 Help Needed: Windows & Linux Testers](#help-needed-windows-linux-testers)
- [Prerequisites](#prerequisites)
- [Platform-Specific Setup](#platform-specific-setup)
  - [Windows](#windows)
  - [Linux](#linux)
  - [macOS](#macos)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

---

## 🚨 Help Needed: Windows & Linux Testers

**I develop Mnemex on macOS and need help testing on Windows and Linux!**

### Why This Matters

While I've written platform-specific instructions based on best practices, **I can't personally test**:
- Windows installation and setup
- Windows path handling and environment variables
- Linux distributions (Ubuntu, Fedora, Arch, etc.)
- Platform-specific edge cases and bugs

### What I Need Help With

#### High Priority 🔥

1. **Installation Testing**
   - Does `uv tool install` work smoothly?
   - Are the setup instructions clear and accurate?
   - Do the paths work correctly (`~/.config/cortexgraph/` on Linux, `C:/Users/.../` on Windows)?

2. **Running the Server**
   - Does `cortexgraph` command work after installation?
   - Do all 7 CLI commands work (`cortexgraph-search`, `cortexgraph-maintenance`, etc.)?
   - Can you connect via Claude Desktop or other MCP clients?

3. **Testing Suite**
   - Do all tests pass? (`uv run python -m pytest`)
   - Does coverage reporting work?
   - Are there any platform-specific test failures?

4. **File Operations**
   - Does JSONL storage work correctly?
   - Do file paths with spaces or special characters work?
   - Does the maintenance CLI (`cortexgraph-maintenance`) work?

#### Medium Priority

5. **Development Workflow**
   - Can you clone and set up for development?
   - Do `ruff` and `mypy` work correctly?
   - Can you run tests in your IDE/editor?

6. **Edge Cases**
   - Long file paths (Windows issue)
   - Non-ASCII characters in paths
   - Different filesystem types
   - Permission issues

### How to Help

**Quick Testing (30 minutes):**

```bash
# Install and verify
uv tool install git+https://github.com/simplemindedbot/cortexgraph.git
cortexgraph --version

# Run basic tests
cd $(mktemp -d)
cortexgraph-maintenance stats
cortexgraph-search "test" --verbose
```

Then report:
- ✅ What worked
- ❌ What failed (with error messages)
- ⚠️ Any warnings or unexpected behavior
- 💡 Suggestions for improving the docs

**Full Testing (1-2 hours):**

Follow the platform-specific setup guide in this file, then:

1. Install from source
2. Run the full test suite
3. Try creating memories and searching
4. Test consolidation feature
5. Report your findings

### Where to Report

**[Open an issue](https://github.com/simplemindedbot/cortexgraph/issues/new)** with:

```markdown
**Platform:** [Windows 11 / Ubuntu 22.04 / etc.]
**Test Type:** [Quick / Full]

**What I Tested:**
- [ ] Installation
- [ ] Running server
- [ ] CLI commands
- [ ] Test suite
- [ ] File operations

**Results:**
✅ Working: [list what worked]
❌ Failed: [list failures with errors]
⚠️ Issues: [list concerns or warnings]

**Logs:**
```
[paste relevant error messages or logs]
```

**Suggestions:**
[any improvements to docs or setup]
```

### Current Status

| Platform | Installation | Tests | CLI Tools | File Ops | Status |
|----------|--------------|-------|-----------|----------|---------|
| **macOS** | ✅ Tested | ✅ Passing | ✅ Working | ✅ Working | Fully tested |
| **Windows** | ❓ Untested | ❓ Unknown | ❓ Unknown | ❓ Unknown | **Need testers!** |
| **Linux (Ubuntu)** | ❓ Untested | ❓ Unknown | ❓ Unknown | ❓ Unknown | **Need testers!** |
| **Linux (Fedora)** | ❓ Untested | ❓ Unknown | ❓ Unknown | ❓ Unknown | **Need testers!** |
| **Linux (Arch)** | ❓ Untested | ❓ Unknown | ❓ Unknown | ❓ Unknown | **Need testers!** |

**Thank you for helping make Mnemex work reliably across all platforms!** 🙏

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10 or higher**
- **Git**
- **UV package manager** (recommended) or pip

---

## Platform-Specific Setup

### Windows

#### 1. Install Python

Download and install Python from [python.org](https://www.python.org/downloads/):

```powershell
# Verify installation
python --version
# Should show Python 3.10 or higher
```

**Important:** During installation, check "Add Python to PATH"

#### 2. Install Git

Download and install from [git-scm.com](https://git-scm.com/download/win)

```powershell
# Verify installation
git --version
```

#### 3. Install UV Package Manager

```powershell
# Using PowerShell (recommended)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip
pip install uv

# Verify installation
uv --version
```

#### 4. Clone the Repository

```powershell
# Using Command Prompt or PowerShell
git clone https://github.com/simplemindedbot/cortexgraph.git
cd cortexgraph
```

#### 5. Set Up Development Environment

```powershell
# Install dependencies (including dev dependencies)
uv sync --all-extras

# Verify installation
uv run python -c "import cortexgraph; print('Mnemex installed successfully!')"
```

#### 6. Configure Environment

```powershell
# Copy example config
copy .env.example .env

# Edit .env with your preferred text editor
notepad .env
```

**Windows-specific config (`~/.config/cortexgraph/.env` or project `.env`):**

```bash
# Use Windows paths with forward slashes or escaped backslashes
CORTEXGRAPH_STORAGE_PATH=C:/Users/YourUsername/.config/cortexgraph/jsonl
# Or with escaped backslashes
# CORTEXGRAPH_STORAGE_PATH=C:\\Users\\YourUsername\\.config\\cortexgraph\\jsonl

# Optional: LTM vault path
LTM_VAULT_PATH=C:/Users/YourUsername/Documents/Obsidian/Vault
```

#### 7. Running Tests on Windows

```powershell
# Run all tests
uv run python -m pytest

# Run with coverage
uv run python -m pytest --cov=cortexgraph --cov-report=html

# Open coverage report
start htmlcov\index.html

# Run specific test file
uv run python -m pytest tests/test_consolidation.py -v

# Run tests matching a pattern
uv run python -m pytest -k "test_merge" -v
```

#### Common Windows Issues

**Issue: `ModuleNotFoundError`**
```powershell
# Ensure you're in the project directory
cd path\to\cortexgraph

# Reinstall dependencies
uv sync --all-extras
```

**Issue: Path too long errors**
```powershell
# Enable long paths in Windows 10/11
# Run as Administrator:
reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f
```

**Issue: Permission errors**
```powershell
# Run PowerShell as Administrator or use:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### Linux

#### 1. Install Python

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip git

# Verify installation
python3 --version
```

**Fedora/RHEL:**
```bash
sudo dnf install python3.10 python3-pip git

# Verify installation
python3 --version
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip git

# Verify installation
python --version
```

#### 2. Install UV Package Manager

```bash
# Using curl (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv

# Add to PATH (if needed)
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
uv --version
```

#### 3. Clone the Repository

```bash
git clone https://github.com/simplemindedbot/cortexgraph.git
cd cortexgraph
```

#### 4. Set Up Development Environment

```bash
# Install dependencies (including dev dependencies)
uv sync --all-extras

# Verify installation
uv run python -c "import cortexgraph; print('Mnemex installed successfully!')"
```

#### 5. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit with your preferred editor
nano .env
# or
vim .env
# or
code .env  # VS Code
```

**Linux-specific config (`~/.config/cortexgraph/.env` or project `.env`):**

```bash
# Standard XDG paths
CORTEXGRAPH_STORAGE_PATH=~/.config/cortexgraph/jsonl

# Optional: LTM vault path
LTM_VAULT_PATH=~/Documents/Obsidian/Vault

# Decay parameters
CORTEXGRAPH_DECAY_MODEL=power_law
CORTEXGRAPH_PL_ALPHA=1.1
CORTEXGRAPH_PL_HALFLIFE_DAYS=3.0
CORTEXGRAPH_DECAY_BETA=0.6

# Thresholds
CORTEXGRAPH_FORGET_THRESHOLD=0.05
CORTEXGRAPH_PROMOTE_THRESHOLD=0.65
```

#### 6. Running Tests on Linux

```bash
# Run all tests
uv run python -m pytest

# Run with coverage
uv run python -m pytest --cov=cortexgraph --cov-report=html

# Open coverage report
xdg-open htmlcov/index.html

# Run specific test file
uv run python -m pytest tests/test_consolidation.py -v

# Run tests matching a pattern
uv run python -m pytest -k "test_merge" -v

# Run tests in parallel (faster for large test suites)
uv run python -m pytest -n auto
```

#### Common Linux Issues

**Issue: Permission denied**
```bash
# Make sure scripts are executable
chmod +x .venv/bin/*

# Or use uv run instead
uv run cortexgraph --help
```

**Issue: `ModuleNotFoundError`**
```bash
# Ensure you're in the project directory
cd /path/to/cortexgraph

# Reinstall dependencies
uv sync --all-extras
```

**Issue: Can't find Python 3.10+**
```bash
# Ubuntu: Use deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10 python3.10-venv

# Or use pyenv
curl https://pyenv.run | bash
pyenv install 3.10.13
pyenv local 3.10.13
```

---

### macOS

#### 1. Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Python and Git

```bash
brew install python@3.10 git

# Verify installation
python3 --version
git --version
```

#### 3. Install UV Package Manager

```bash
# Using curl (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using Homebrew
brew install uv

# Verify installation
uv --version
```

#### 4. Clone the Repository

```bash
git clone https://github.com/simplemindedbot/cortexgraph.git
cd cortexgraph
```

#### 5. Set Up Development Environment

```bash
# Install dependencies (including dev dependencies)
uv sync --all-extras

# Verify installation
uv run python -c "import cortexgraph; print('Mnemex installed successfully!')"
```

#### 6. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit with your preferred editor
nano .env
# or
open -e .env  # TextEdit
```

**macOS-specific config (`~/.config/cortexgraph/.env` or project `.env`):**

```bash
# Standard macOS paths
CORTEXGRAPH_STORAGE_PATH=~/.config/cortexgraph/jsonl

# Optional: LTM vault path
LTM_VAULT_PATH=~/Documents/Obsidian/Vault
```

#### 7. Running Tests on macOS

```bash
# Run all tests
uv run python -m pytest

# Run with coverage
uv run python -m pytest --cov=cortexgraph --cov-report=html

# Open coverage report
open htmlcov/index.html

# Run specific test file
uv run python -m pytest tests/test_consolidation.py -v
```

---

## Development Workflow

### Note on documentation publishing

- Do not merge `gh-pages` into `main`. The `gh-pages` branch is a deployment branch containing built site artifacts only. Documentation is built from `main` by CI and force‑pushed to `gh-pages`.
- Any pull request that adds top‑level `index.html`, `assets/`, or `search/` to `main` will be rejected. If you need to preview docs locally, run `mkdocs serve` instead of committing built files.

### Making Changes

1. **Create a new branch:**

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

2. **Make your changes** following the code style guidelines below

3. **Run tests** to ensure nothing broke:

```bash
# All tests
uv run python -m pytest

# With coverage
uv run python -m pytest --cov=cortexgraph
```

4. **Run linters:**

```bash
# Check code style
uv run ruff check src/cortexgraph tests

# Format code
uv run ruff format src/cortexgraph tests

# Type checking
uv run mypy src/cortexgraph
```

5. **Commit your changes:**

```bash
git add .
git commit -m "feat: add new feature"
# or
git commit -m "fix: resolve bug in consolidation"
```

### Commit Message Format

Use conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks
- `perf:` - Performance improvements

**Examples:**
```
feat: add spaced repetition scheduling
fix: handle empty cluster in consolidation
docs: update installation guide for Windows
test: add tests for decay calculation edge cases
```

---

## Testing

### Test Structure

Tests are organized in the `tests/` directory:

```
tests/
├── test_consolidation.py    # Consolidation logic tests
├── test_decay.py             # Decay algorithm tests
├── test_decay_models.py      # Decay model tests
├── test_ltm_index.py         # LTM index tests
├── test_search_unified.py    # Unified search tests
└── test_storage.py           # Storage layer tests
```

### Writing Tests

Follow these guidelines when writing tests:

1. **Use descriptive names:**
```python
def test_merge_content_preserves_unique_information():
    """Test that content merging keeps unique info from all memories."""
    # Test implementation
```

2. **Use fixtures for common setup:**
```python
@pytest.fixture
def sample_memories():
    """Create sample memories for testing."""
    return [
        Memory(id="mem-1", content="Test content 1"),
        Memory(id="mem-2", content="Test content 2"),
    ]

def test_something(sample_memories):
    # Use the fixture
    assert len(sample_memories) == 2
```

3. **Test edge cases:**
```python
def test_merge_content_empty():
    """Test merging with empty list."""
    result = merge_content_smart([])
    assert result == ""

def test_merge_content_single():
    """Test merging with single memory."""
    memories = [Memory(id="1", content="Single")]
    result = merge_content_smart(memories)
    assert result == "Single"
```

4. **Use parametrize for multiple cases:**
```python
@pytest.mark.parametrize("use_count,expected", [
    (1, 1.0),
    (5, 2.6),
    (10, 4.0),
])
def test_use_count_boost(use_count, expected):
    boost = calculate_boost(use_count)
    assert abs(boost - expected) < 0.1
```

### Running Specific Tests

```bash
# Run a specific test file
uv run python -m pytest tests/test_consolidation.py

# Run a specific test
uv run python -m pytest tests/test_consolidation.py::test_merge_tags

# Run tests matching a pattern
uv run python -m pytest -k "consolidation"

# Run with verbose output
uv run python -m pytest -v

# Run with detailed output on failures
uv run python -m pytest -vv

# Stop on first failure
uv run python -m pytest -x

# Show local variables on failure
uv run python -m pytest -l

# Run tests in parallel (requires pytest-xdist)
uv run python -m pytest -n auto
```

### Coverage Requirements

- Aim for **80%+ code coverage** for new features
- Critical paths (decay, storage, consolidation) should have **95%+ coverage**
- Check coverage with:

```bash
uv run python -m pytest --cov=cortexgraph --cov-report=term-missing
```

---

## Code Style

### Python Style Guidelines

We use **Ruff** for linting and formatting (no Black):

```bash
# Check for style issues
uv run ruff check src/cortexgraph tests

# Auto-fix issues
uv run ruff check --fix src/cortexgraph tests

# Format code
uv run ruff format src/cortexgraph tests
```

### Pre-commit Hook

Install pre-commit (one time):

```bash
pipx install pre-commit  # or: pip install pre-commit
```

Enable hooks in this repo:

```bash
pre-commit install
```

Run on all files locally:

```bash
pre-commit run --all-files
```

You can also run individual hooks:

```bash
# Run ruff only
pre-commit run ruff --all-files

# Run mypy on src via pre-commit
pre-commit run mypy --all-files
```

### Type Hints

All functions must have type hints:

```python
# Good ✓
def calculate_score(use_count: int, last_used: int, strength: float) -> float:
    """Calculate memory score."""
    return (use_count ** 0.6) * math.exp(-0.0001 * time.time()) * strength

# Bad ✗
def calculate_score(use_count, last_used, strength):
    return (use_count ** 0.6) * math.exp(-0.0001 * time.time()) * strength
```

Run type checker:

```bash
uv run mypy src/cortexgraph
```

### Docstrings

Use Google-style docstrings:

```python
def merge_content_smart(memories: list[Memory]) -> str:
    """
    Intelligently merge content from multiple memories.

    Strategy:
    - If very similar (duplicates), keep the longest/most detailed version
    - If related but distinct, combine with clear separation
    - Preserve unique information from each memory

    Args:
        memories: List of memories to merge

    Returns:
        Merged content string

    Example:
        >>> memories = [Memory(id="1", content="Python is great")]
        >>> merge_content_smart(memories)
        'Python is great'
    """
    # Implementation
```

### Code Organization

- **4-space indentation** (no tabs)
- **Line length: 100 characters max**
- **Module organization:**
  ```python
  # Standard library imports
  import time
  from pathlib import Path

  # Third-party imports
  from pydantic import BaseModel

  # Local imports
  from ..storage.models import Memory
  from ..config import get_config
  ```

---

### Pre-commit Hooks (Recommended)

Install pre-commit to catch issues locally before CI:

```bash
uv run pre-commit install
# or
pre-commit install

# Run on all files
pre-commit run --all-files
```

Hooks configured in `.pre-commit-config.yaml`:
- `ruff` — lint with autofix (`--fix`)
- `ruff-format` — enforce formatting
- `mypy (src)` — type-check `src/cortexgraph` only
- `check-toml` — validates `pyproject.toml` parses
- `fs-sanity-duplicates` — blocks filenames with trailing numbers (e.g., `file 2.md`)

Notes:
- The filesystem sanity hook prevents committing duplicate/copy artifacts (common on macOS/Windows).
- If you hit a hook failure, address the message and re-run `pre-commit run --all-files`.
- CI mirrors these checks via the Gate job (tests, lint/format, types, TOML parse, fs sanity).

## Submitting Changes

### Before Submitting

1. **Ensure all tests pass:**
```bash
uv run python -m pytest
```

2. **Check code style:**
```bash
uv run ruff check src/cortexgraph tests
uv run ruff format src/cortexgraph tests
uv run mypy src/cortexgraph
```

3. **Update documentation** if you:
   - Added a new feature
   - Changed an API
   - Modified configuration options

4. **Add tests** for new functionality

### PR Checklist (Operating Principles)

Before opening a PR, confirm:

- [ ] Root cause stated; verified env/config/deps (see `AGENTS.md#operating-principles`).
- [ ] Verification steps and findings included in PR description.
- [ ] Local checks pass: `pytest`, `ruff check`, `ruff format`, `mypy`.
- [ ] No import-time side effects; config/storage paths remain injectable.
- [ ] Docs and examples updated if behavior or config changed.

### Creating a Pull Request

1. **Push your branch:**
```bash
git push origin feature/your-feature-name
```

2. **Create PR on GitHub**

3. **PR Description should include:**
   - **What** changed
   - **Why** the change was needed
   - **How** to test it
   - Any **breaking changes**

**Example PR template:**

```markdown
## Description
Implement spaced repetition scheduling for memory review.

## Motivation
Users requested a way to get reminders for reviewing important memories
before they decay too much.

## Changes
- Add `calculate_next_review()` function to core/scheduling.py
- Add `get_review_queue()` MCP tool
- Add tests in tests/test_scheduling.py (100% coverage)
- Update README.md with usage examples

## Testing
- All existing tests pass
- Added 12 new tests for scheduling logic
- Tested manually with 100+ memories

## Breaking Changes
None - this is a new feature with no API changes.
```

### Code Review Process

- Maintainers will review your PR
- Address any feedback
- Once approved, your PR will be merged

---

## Reporting Issues

### Before Opening an Issue

1. **Search existing issues** to avoid duplicates
2. **Try the latest version** - your issue might be fixed
3. **Gather information:**
   - Mnemex version (`cortexgraph --version` or check `pyproject.toml`)
   - Python version (`python --version`)
   - Operating system and version
   - Steps to reproduce

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Install Mnemex with `uv tool install...`
2. Configure with these settings: ...
3. Run command `...`
4. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment:**
- OS: [e.g., Windows 11, Ubuntu 22.04, macOS 14]
- Python version: [e.g., 3.10.13]
- Mnemex version: [e.g., 1.0.0]
- Installation method: [uv tool install / editable]

**Logs/Screenshots**
```
[Paste any error messages or logs here]
```

**Additional context**
Any other information that might help.
```

### Feature Requests

```markdown
**Feature description**
A clear description of the feature you'd like.

**Use case**
Why would this feature be useful? What problem does it solve?

**Proposed solution**
If you have ideas on how to implement it.

**Alternatives considered**
Other approaches you've thought about.
```

---

## Getting Help

- **Documentation:** [docs/](docs/) directory
- **Issues:** [GitHub Issues](https://github.com/simplemindedbot/cortexgraph/issues)
- **Roadmap:** [future_roadmap.md](future_roadmap.md)

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to Mnemex! 🎉
