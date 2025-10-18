# Introduction to Mnemex: Novel Approaches to AI Memory

*Published on [simpleminded.bot](https://simpleminded.bot) - Part 1 of "Building AI Memory Systems with Mnemex"*

---

## The Memory Problem in AI

If you've used AI assistants like Claude, ChatGPT, or others, you've likely experienced this frustrating scenario:

> **You:** "I prefer TypeScript over JavaScript for all my projects"  
> *[Three days later in a new conversation]*  
> **You:** "Can you help me set up a new project?"  
> **AI:** "Sure! What language would you like to use? JavaScript, Python, Go..."  
> **You:** "Wait, didn't I tell you I prefer TypeScript?"  
> **AI:** "I don't have any memory of our previous conversations."

This isn't just annoying—it's a fundamental limitation that prevents AI assistants from building meaningful, long-term relationships with users. Traditional AI systems treat each conversation as completely isolated, forcing users to repeat themselves endlessly.

## Enter Mnemex: Human-Like Memory for AI

[Mnemex](https://github.com/simplemindedbot/mnemex) is a revolutionary Model Context Protocol (MCP) server that gives AI assistants **human-like memory dynamics**. Instead of treating memory as a simple database, Mnemex implements biologically-inspired memory patterns that closely mirror how human memory actually works.

### What Makes Mnemex Different?

Most memory systems for AI are primitive:
- **Time-based expiration (TTL)**: "Delete after 7 days" - doesn't care if you used it 100 times
- **LRU cache**: "Keep last 100 items" - dumps important stuff just because it's old
- **Simple databases**: Store everything forever until manually deleted

Mnemex is **smart**:
- **Temporal decay**: Memories fade naturally over time (like human memory)
- **Reinforcement learning**: Frequently used memories get stronger and last longer
- **Two-layer architecture**: Automatic promotion from working memory to permanent storage
- **Git-friendly storage**: Human-readable files you can inspect, edit, and version control

## Key Innovations

### 1. The Ebbinghaus Forgetting Curve

Mnemex implements a mathematical model based on the [Ebbinghaus forgetting curve](https://en.wikipedia.org/wiki/Forgetting_curve), which describes how human memory naturally decays over time. The core scoring formula is:

```
score(t) = (use_count^β) × e^(-λ × Δt) × strength
```

Where:
- **use_count**: How many times you've referenced this memory
- **β (beta)**: Sub-linear weighting (default: 0.6) - prevents over-rewarding high use counts
- **λ (lambda)**: Decay constant based on half-life (default: 3-day half-life)
- **Δt**: Time since last access
- **strength**: Importance multiplier (0.0-2.0)

This creates memory dynamics that feel natural and human-like.

### 2. Smart Reinforcement System

Unlike simple TTL systems, Mnemex rewards frequently accessed information:

| Use Count | Boost Factor | Behavior |
|-----------|--------------|----------|
| 1 | 1.0× | Fresh memory |
| 5 | 2.6× | Getting stronger |
| 10 | 4.0× | Well-established |
| 50 | 11.4× | Deeply ingrained |

**Example**: You mention "I prefer dark mode" once → weak memory that fades quickly. You reference it 5 times over two weeks → strong memory that gets promoted to permanent storage.

### 3. Two-Layer Memory Architecture

```
┌─────────────────────────────────────┐
│   Short-term memory (STM)           │
│   - JSONL storage                   │
│   - Temporal decay                  │
│   - Hours to weeks retention        │
└──────────────┬──────────────────────┘
               │ Automatic promotion
               ↓
┌─────────────────────────────────────┐
│   Long-term memory (LTM)            │
│   - Markdown files (Obsidian)       │
│   - Permanent storage               │
│   - Git version control             │
└─────────────────────────────────────┘
```

**Promotion criteria**:
- Score ≥ 0.65 (high value)
- OR used 5+ times within 14 days (frequently referenced)

### 4. Privacy-First Design

**All data stored locally** - no cloud services, no tracking, no data sharing:

- **Short-term memory**: Human-readable JSONL files in `~/.config/mnemex/jsonl/`
- **Long-term memory**: Markdown files optimized for Obsidian
- **Git-friendly**: You can version control your memories
- **Transparent**: You can read, edit, or delete any memory

## Real-World Example

Let's see Mnemex in action:

### Day 1: Initial Memory
```
You: "I'm allergic to shellfish"
→ Mnemex saves: {"content": "I'm allergic to shellfish", "strength": 1.0, "score": 1.0}
```

### Day 3: Memory Decay
```
Score drops to ~0.5 (half-life reached)
→ Still accessible, but weaker
```

### Day 5: Reinforcement
```
You: "Can you suggest a restaurant? I'm allergic to shellfish"
→ Mnemex finds the memory, reinforces it
→ Score jumps to ~1.2, use_count = 2
```

### Day 10: More Reinforcement
```
You: "What about seafood places? Remember, I'm allergic to shellfish"
→ Score increases further, use_count = 3
→ Memory getting stronger despite age
```

### Day 14: Automatic Promotion
```
use_count = 5 within 14 days → PROMOTED to LTM
→ Saved as permanent Markdown note in Obsidian vault
→ Never forgotten unless manually deleted
```

## Use Cases and Applications

### Personal Assistant (Balanced)
- **Half-life**: 3 days
- **Use case**: Remember preferences, decisions, project context
- **Example**: "I prefer 2-space indentation" gets remembered across coding sessions

### Development Environment (Aggressive)
- **Half-life**: 1 day  
- **Use case**: Fast context switching, rapid iteration
- **Example**: Current debugging session details fade quickly when you move to new features

### Research/Archival (Conservative)
- **Half-life**: 14 days
- **Use case**: Long-term knowledge preservation
- **Example**: Research findings and insights retained for months

### Meeting Notes (High Velocity)
- **Half-life**: 12 hours
- **Use case**: Rapid meeting context, quick forgetting of irrelevant details
- **Example**: Action items from yesterday's meeting fade unless referenced

## The Smart Prompting System

Mnemex includes sophisticated prompting patterns that make AI assistants use memory naturally:

**Auto-Save Pattern**:
```
User: "I prefer TypeScript over JavaScript"
→ AI automatically saves with tags: [preferences, typescript, programming]
```

**Auto-Recall Pattern**:
```
User: "Can you help with another TypeScript project?"
→ AI automatically retrieves preferences and conventions
```

**Auto-Reinforce Pattern**:
```
User: "Yes, still using TypeScript"
→ Memory strength increased, decay slowed
```

No explicit memory commands needed—just natural conversation.

## Comparison with Traditional Memory Systems

| Approach | How It Works | Problems |
|----------|--------------|----------|
| **TTL (Redis-style)** | Delete after fixed time | Ignores usage frequency |
| **LRU Cache** | Evict least recently used | No consideration of importance |
| **Simple Database** | Store everything forever | No forgetting, becomes cluttered |
| **Mnemex** | Biologically-inspired decay + reinforcement | ✅ Mimics human memory patterns |

## Getting Started

Mnemex is designed to be simple to set up and use:

### 1. Installation
```bash
uv tool install git+https://github.com/simplemindedbot/mnemex.git
```

### 2. Configuration
Add to your Claude Desktop config:
```json
{
  "mcpServers": {
    "mnemex": {
      "command": "mnemex"
    }
  }
}
```

### 3. Use Naturally
Just talk to Claude normally. Memory "just works" without explicit commands.

## What's Next?

In the next post, we'll dive deep into Mnemex's technical architecture, exploring:

- The mathematical foundations of temporal decay
- How the two-layer memory system works
- Performance characteristics and optimization strategies
- Integration patterns for different AI assistants

Mnemex represents a fundamental shift in how we think about AI memory—from simple storage to biologically-inspired cognitive patterns. It's not just about remembering things; it's about remembering them the way humans do.

---

*This is Part 1 of "Building AI Memory Systems with Mnemex." Stay tuned for Part 2: "Mnemex Architecture Deep Dive" where we'll explore the technical implementation details and mathematical foundations.*

**Resources:**
- [Mnemex GitHub Repository](https://github.com/simplemindedbot/mnemex)
- [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol)
- [Ebbinghaus Forgetting Curve](https://en.wikipedia.org/wiki/Forgetting_curve)