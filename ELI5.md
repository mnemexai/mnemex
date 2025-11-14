# What Is This? (ELI5)

## The Problem

You're chatting with Claude. You tell it "I prefer TypeScript over JavaScript" or "I'm working on a project called BlueSky." Then, three days later in a new conversation, Claude has completely forgotten. You have to repeat yourself over and over.

**This is annoying.**

## What This Repo Does

This is **CortexGraph** - a **memory system for AI assistants like Claude**. It makes Claude remember things you tell it, but in a smart, human-like way:

- 🧠 **Remembers important stuff** - Preferences, decisions, facts about you
- ⏰ **Forgets naturally** - Old, unused memories fade away (just like human memory)
- 💪 **Gets stronger with use** - The more you reference something, the longer Claude remembers it
- 📦 **Saves important things permanently** - Frequently used memories get promoted to long-term storage

## A Simple Analogy

Think of it like your own memory:

- **Short-term memory** is like remembering what you had for breakfast this morning. If it's not important, you'll forget it in a few days.
- **Long-term memory** is like remembering your best friend's name. You use it all the time, so it never fades.

This system works the same way:
- New memories start in **short-term storage** with a 3-day "half-life"
- If you keep using them, they get **stronger and last longer**
- Really important memories get **promoted to permanent storage** (your Obsidian notes)

## How It Actually Works (Simple Version)

### 1. You Talk to Claude

```
You: "I prefer dark mode in all my apps"
```

Claude automatically saves this as a memory with tags like `[preferences, ui, dark-mode]`.

### 2. Time Passes

After 3 days, this memory is at "half strength." After a week, it's fading. After two weeks, it might get forgotten completely.

### 3. You Mention It Again

```
You: "Can you make this app in dark mode?"
```

Claude searches its memory, finds your preference, and **reinforces it** (makes it stronger). Now it'll last longer.

### 4. Automatic Promotion

If you reference dark mode preferences 5 times in two weeks, Claude thinks "this is important!" and saves it to your **Obsidian vault** as a permanent note. Now it'll never be forgotten.

### 5. Manual Promotion

You can also just tell Claude directly:

```
You: "Never forget this: I'm allergic to peanuts"
You: "Make a note that I prefer 2-space indentation"
```

Claude will save these with high importance and promote them to permanent storage immediately.

## What Makes This Different?

Most memory systems are dumb:
- **Time-based expiration (TTL)**: "Delete after 7 days" - doesn't care if you used it 100 times
- **LRU cache**: "Keep last 100 items" - dumps important stuff just because it's old

This system is **smart**:
- Combines **recency** (when did I last use this?), **frequency** (how often do I use this?), and **importance** (did I mark this as critical?)
- Memories fade naturally over time (like human memory)
- Frequently used memories stick around longer
- You can manually boost important things by asking Claude to "never forget" or "make a note"

## How to Use It

### Step 1: Install

```bash
# Install CortexGraph from PyPI (recommended - fast and easy!)
uv tool install cortexgraph

# Or using pipx
pipx install cortexgraph

# Or using pip (traditional)
pip install cortexgraph
```

This installs `cortexgraph` and all 7 CLI commands in one step!

### Step 2: Configure (Optional)

Create `~/.config/cortexgraph/.env` if you want custom settings:

```bash
# Where to store memories (default: ~/.config/cortexgraph/jsonl)
CORTEXGRAPH_STORAGE_PATH=~/.config/cortexgraph/jsonl

# How fast memories fade (3 days = default)
CORTEXGRAPH_PL_HALFLIFE_DAYS=3.0

# Where to save important memories permanently (optional)
LTM_VAULT_PATH=~/Documents/Obsidian/MyVault
```

**Note**: Configuration goes in `~/.config/cortexgraph/.env` - create it if it doesn't exist!

### Step 3: Connect to Claude

Add this to your Claude Desktop config file:

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "cortexgraph"
    }
  }
}
```

That's it! Just one line - no paths, no environment variables.

**Troubleshooting: Command Not Found**

If Claude Desktop shows errors like `spawn cortexgraph ENOENT`, it can't find the `cortexgraph` command.

This happens because GUI apps on macOS/Linux don't see your shell's PATH. To fix it:

```bash
# 1. Find where cortexgraph is installed
which cortexgraph
# Example: /Users/username/.local/bin/cortexgraph

# 2. Use the absolute path in your config
{
  "mcpServers": {
    "cortexgraph": {
      "command": "/Users/username/.local/bin/cortexgraph"
    }
  }
}
```

Replace with your actual path from step 1.

### Step 4: Restart Claude Desktop

Now Claude has memory.

## What Happens Now?

Claude will automatically:
- **Save** things you tell it (preferences, decisions, project info)
- **Recall** them when relevant to the conversation
- **Reinforce** memories you use frequently
- **Forget** old, unused stuff
- **Promote** important memories to permanent storage

You don't have to think about it. It just works.

You can also **manually save** things permanently:
```
You: "Make a note: I'm allergic to shellfish"
You: "Never forget this: my API key rotation schedule is monthly"
You: "Remember permanently: I prefer functional programming style"
```

## Under the Hood (Slightly More Technical)

### The Scoring Formula

Every memory gets a "score" that determines whether it stays or gets forgotten:

```
score = (use_count ^ 0.6) × (decay_over_time) × importance
```

- **use_count**: How many times you've referenced this
- **decay_over_time**: Exponential decay (half-life = 3 days by default)
- **importance**: 1.0 for normal stuff, up to 2.0 for critical things

### Thresholds

- **Score < 0.05**: Memory gets deleted (forgotten)
- **Score ≥ 0.65**: Memory gets promoted to permanent storage
- **OR used 5+ times in 14 days**: Also gets promoted

### Example: Watch a Memory Fade

Let's say you tell Claude "I'm learning Rust" but never mention it again:

| Time | Score | Status |
|------|-------|--------|
| Right now | 1.00 | Fresh memory |
| 1 day later | 0.84 | Still strong |
| 3 days later | 0.50 | Half-life reached |
| 7 days later | 0.21 | Fading |
| 14 days later | 0.04 | **Forgotten** (score < 0.05) |

### Example: Watch a Memory Get Stronger

Now let's say you mention "I prefer TypeScript" and then reference it 5 times over 2 weeks:

| Action | Use Count | Score |
|--------|-----------|-------|
| Initial save | 1 | 1.00 |
| Mention #2 | 2 | 1.55 |
| Mention #3 | 3 | 1.93 |
| Mention #4 | 4 | 2.23 |
| Mention #5 | 5 | 2.49 |

After use #5, the score is way above 0.65, so it gets **promoted to your Obsidian vault** as a permanent note.

## Storage: Where Are My Memories?

### Short-term (JSONL files)
- **Location**: `~/.config/cortexgraph/jsonl/` (or whatever you set in `.env`)
- **Files**: `memories.jsonl`, `relations.jsonl`
- **Format**: Human-readable JSON, one memory per line
- **Git-friendly**: You can version control these files!

Example memory:
```json
{"id":"mem-abc123","content":"I prefer TypeScript over JavaScript","tags":["preferences","typescript"],"created_at":"2025-10-07T10:00:00Z","last_used":"2025-10-07T10:00:00Z","use_count":1,"strength":1.0,"entities":["TypeScript","JavaScript"]}
```

### Long-term (Markdown files)
- **Location**: Your Obsidian vault (configurable in `.env`)
- **Format**: Markdown files with YAML frontmatter
- **Permanent**: Never forgotten unless you delete them

Example promoted memory:
```markdown
---
created: 2025-10-07
tags: [preferences, typescript, programming]
entities: [TypeScript, JavaScript]
---

# TypeScript Preference

I prefer TypeScript over JavaScript for all new projects.

**Related memories:**
- [[Modern JavaScript Frameworks]]
- [[Type Safety Best Practices]]
```

## Commands You Can Use

```bash
# Run the memory server for Claude
cortexgraph

# Search your memories from command line
cortexgraph-search "typescript preferences" --tags preferences

# Index your Obsidian vault for search
cortexgraph-index-ltm

# Check storage stats
cortexgraph-maintenance stats

# Clean up old memories (compact storage)
cortexgraph-maintenance compact

# Backup memories to git
cortexgraph-backup snapshot
```

## Tuning: Make It Work Your Way

### Fast-paced work (forget quickly)
```bash
CORTEXGRAPH_PL_HALFLIFE_DAYS=1.0  # 1-day half-life
CORTEXGRAPH_FORGET_THRESHOLD=0.10  # More aggressive forgetting
```

### Research/archival (remember longer)
```bash
CORTEXGRAPH_PL_HALFLIFE_DAYS=7.0  # 7-day half-life
CORTEXGRAPH_FORGET_THRESHOLD=0.02  # Keep things longer
```

### Preference-heavy assistant
```bash
# Save preferences with higher importance
# In your code: save_memory(..., strength=1.5)
```

## FAQ

**Q: Does this work with ChatGPT or other AI assistants?**
A: This uses the Model Context Protocol (MCP), which is supported by most modern AI clients:
- ✅ **Claude Desktop** - Full support
- ✅ **CLI clients** (like Cline, Aider, etc.) - Full support
- ✅ **Most desktop clients** - Full support
- ⚠️ **ChatGPT** - Experimental MCP support only (not recommended yet)

**Q: Will my memories get shared with Anthropic?**
A: No. Everything is stored locally on your computer. Anthropic never sees your memories.

**Q: What if I want to keep something forever?**
A: Three ways:
1. **Use it frequently** so it gets auto-promoted
2. **Ask Claude directly**: "Never forget this..." or "Make a note that..."
3. **Set high strength manually** when saving (strength=1.5-2.0)

**Q: Can I delete memories?**
A: Yes. They're just JSONL files. Edit them manually or use the maintenance tools.

**Q: What's this "knowledge graph" thing?**
A: Memories can link to each other (like "TypeScript Preference" → "relates to" → "React Component Style"). You can query these relationships and find connections.

**Q: Do I need Obsidian?**
A: No! Obsidian integration is optional. You can use just short-term memory without any vault.

**Q: This sounds complicated...**
A: It's actually simple once it's set up:
1. Clone the repo
2. Install it
3. Add it to Claude's config (just the command, paths go in `.env`)
4. Restart Claude
5. Talk normally - memory "just works"

## What's Actually Novel Here?

This isn't just "save stuff to a database." The key innovations:

1. **Temporal decay algorithm** - Mathematically modeled on how human memory works (Ebbinghaus forgetting curve)
2. **Smart prompting patterns** - Teaching Claude *when* to save/recall without explicit commands
3. **Two-layer architecture** - Automatic promotion from working memory to permanent storage
4. **Git-friendly storage** - Human-readable JSONL that you can version control

Most importantly: **It feels natural.** You don't think about memory management. Claude just remembers things like a human would.

## Still Confused?

Read the examples in the `examples/` directory or check out:
- [docs/scoring_algorithm.md](docs/scoring_algorithm.md) - The math behind memory decay
- [docs/architecture.md](docs/architecture.md) - How the system is built
- [docs/api.md](docs/api.md) - All available commands

## TL;DR

**One sentence**: CortexGraph makes Claude remember things you tell it, with memories that fade naturally over time unless you use them frequently, just like human memory.

**Quick start**:
```bash
# Install from PyPI
uv tool install cortexgraph

# Add to Claude config: {"command": "cortexgraph"}
# Or use absolute path if needed: {"command": "/path/to/cortexgraph"}
```

Then restart Claude Desktop. Done.
