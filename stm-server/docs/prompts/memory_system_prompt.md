# Smart Prompting for Memory Systems

**Version:** 0.2.0
**Last Updated:** 2025-01-07

## Overview

The STM server's true power lies not in its MCP tools alone, but in how LLMs are taught to use them naturally. This document describes the smart prompting system - patterns and techniques for making AI assistants remember things like humans do, without explicit commands.

## Core Principle

> **Memory operations should be invisible to the user.**

When you tell a friend "I prefer tea over coffee," they remember without saying "OK, I'm saving that to my memory database." The STM system enables AI assistants to do the same through carefully designed system prompts.

## Auto-Detection Patterns

### 1. Auto-Save (Capture Important Information)

**When to trigger:**
- User shares preferences or personal information
- User makes decisions or plans
- User provides corrections or feedback
- User shares factual information about themselves or their projects
- User establishes conventions or workflows

**Examples:**

```
User: "I prefer using TypeScript over JavaScript for all new projects"
→ Auto-save to STM with tags: ["preferences", "typescript", "programming"]

User: "The database password is in /home/user/.env"
→ Auto-save to STM with tags: ["credentials", "database", "security"]
   + High strength=1.5 for security-critical info

User: "I've decided to go with the monorepo approach"
→ Auto-save to STM with tags: ["decisions", "architecture", "monorepo"]
```

**Implementation Pattern:**
```python
# Detect information-sharing patterns
if is_preference(message) or is_decision(message) or is_factual(message):
    await save_memory(
        content=extract_key_info(message),
        meta={
            "tags": infer_tags(message),
            "source": "conversation",
            "context": current_topic
        },
        # Boost strength for important categories
        strength=1.5 if is_critical(message) else 1.0
    )
```

### 2. Auto-Recall (Retrieve Relevant Context)

**When to trigger:**
- User asks about past topics
- User references previous conversations ("as we discussed")
- User asks for recommendations based on preferences
- Current topic relates to past memories
- User seems to assume shared context

**Examples:**

```
User: "What did I decide about the database?"
→ Search STM for tags: ["database", "decisions"]
→ Present relevant memories

User: "Can you help me with another TypeScript project?"
→ Search STM for tags: ["typescript", "preferences", "projects"]
→ Auto-recall conventions and preferences

User: "Which approach did we agree on?"
→ Search recent STM (window_days=7) for decisions
→ Surface relevant context
```

**Implementation Pattern:**
```python
# Detect recall triggers
if is_question_about_past(message) or references_previous_context(message):
    results = await search_memory(
        query=extract_search_query(message),
        tags=infer_relevant_tags(message),
        window_days=infer_time_window(message),
        top_k=5
    )
    # Weave results into response naturally
    incorporate_memories_into_response(results)
```

### 3. Auto-Reinforce (Strengthen Frequently Used Memories)

**When to trigger:**
- User revisits a previously discussed topic
- User builds upon previous information
- User confirms or updates existing memories
- Recalled memory proves useful in conversation

**Examples:**

```
User: "Yes, we're still going with TypeScript"
→ Search for TypeScript preference memory
→ touch_memory(id) to reinforce

User: "Can you update that database location?"
→ Search for database location memory
→ touch_memory(id) then update with new info
```

**Implementation Pattern:**
```python
# After successful recall
if memory_was_helpful(recalled_memory, user_feedback):
    await touch_memory(
        memory_id=recalled_memory.id,
        boost_strength=is_very_important(context)
    )
```

### 4. Auto-Consolidate (Merge Similar Memories)

**When to trigger:**
- Cluster analysis detects high similarity (>0.85)
- User provides updated information about existing memory
- Conflicting information detected
- Memory count exceeds threshold (suggests duplicates)

**Examples:**

```
User: "Actually, I use TypeScript AND Flow types"
→ Search for existing TypeScript preference
→ Update memory instead of creating new one

System: Detected 3 similar memories about "database config"
→ Prompt LLM to review cluster
→ Suggest consolidation to user
```

**Implementation Pattern:**
```python
# Periodic consolidation check
clusters = await cluster_memories(threshold=0.85)
for cluster in clusters:
    if cluster.cohesion > 0.90:
        # Auto-merge obvious duplicates
        await consolidate_memories(cluster_id=cluster.id, mode="auto")
    else:
        # Ask user for guidance
        prompt_user_for_consolidation(cluster)
```

## System Prompt Template

### For AI Assistants Using STM

```markdown
# Memory System Instructions

You have access to a short-term memory (STM) system with temporal decay. Use it to remember important information about the user naturally.

## Automatic Behaviors

1. **Save Important Information**
   - When the user shares preferences, decisions, or facts about themselves/projects
   - Use descriptive tags for categorization
   - Mark security-critical info with higher strength

2. **Recall Context**
   - When the user asks about past topics
   - When current conversation relates to previous discussions
   - Search by tags and keywords, use time windows for recent topics

3. **Reinforce Memories**
   - When you recall a memory and it proves useful
   - When the user revisits a topic

4. **Be Natural**
   - Don't announce "I'm saving this to memory"
   - Don't say "I found 3 matching memories"
   - Weave recalled information into responses naturally
   - Act like you remember, not like you're querying a database

## Example Interactions

**Good:**
User: "I prefer using Vim for code editing"
You: "Got it. I'll keep that in mind when suggesting tools."
[Internally: save_memory with tags=["preferences", "vim", "editor"]]

**Bad:**
User: "I prefer using Vim for code editing"
You: "OK, I've saved your Vim preference to my short-term memory database with ID mem_abc123."

**Good:**
User: "What was my preferred editor again?"
You: "You mentioned you prefer Vim for code editing."
[Internally: searched STM, found preference, reinforced it]

**Bad:**
User: "What was my preferred editor again?"
You: "Let me search my memory... I found 1 result: 'I prefer using Vim for code editing' (score: 0.85, created: 2 days ago)"

## Tool Usage Guidelines

- `save_memory`: For preferences, decisions, facts, credentials
- `search_memory`: For recall and context retrieval
- `touch_memory`: After successful recall
- `promote_memory`: Let system auto-promote, or suggest promotion for very important info
- `gc`: Let system handle automatically
```

## Advanced Patterns

### Temporal Awareness

The system knows memories decay over time. Use this to your advantage:

```python
# Recent memory (< 7 days) - high confidence
if memory.age_days < 7:
    response = f"You recently mentioned {memory.content}"

# Older memory (> 30 days) - confirm with user
elif memory.age_days > 30:
    response = f"I recall you mentioned {memory.content} a while back - is that still accurate?"

# Decayed memory (low score) - tentative
if memory.score < 0.15:
    response = f"I vaguely remember something about {topic} - can you remind me?"
```

### Context-Aware Tagging

Tags should reflect user's mental model, not system categories:

```python
# Bad tagging (system-centric)
tags = ["data", "config", "string", "path"]

# Good tagging (user-centric)
tags = ["database", "credentials", "project-alpha", "security"]
```

### Strength Modulation

Adjust memory strength based on importance:

```python
# Critical information - high strength
strength = 2.0  # Security credentials, decisions with high impact

# Normal information - default strength
strength = 1.0  # Preferences, facts, discussions

# Tentative information - low strength
strength = 0.5  # Unconfirmed ideas, exploratory thoughts
```

## Integration with LTM (Long-Term Memory)

The system automatically promotes high-value memories to LTM (Obsidian vault). Configure prompts to:

1. **Suggest Promotion** - Ask user if important information should be saved permanently
2. **Reference Both** - Use unified search to pull from STM (recent) and LTM (permanent)
3. **Surface Patterns** - Notice when user frequently references LTM topics

```markdown
## Long-Term Memory Integration

When information seems particularly important or frequently referenced:
- Suggest: "This seems important - should I save it to your permanent knowledge base?"
- After promotion: Quietly reference LTM version in future recalls
```

## Anti-Patterns (What NOT to Do)

### ❌ Over-Announcing

```
Bad: "I've saved your preference to memory ID mem_12345 with tags ['vim', 'editor']"
Good: "Got it, I'll remember that."
```

### ❌ Exposing Implementation Details

```
Bad: "Searching STM with query='database' tags=['config'] window_days=7..."
Good: "Let me think... you mentioned the database config is in /home/user/.env"
```

### ❌ Asking for Explicit Permission

```
Bad: "Would you like me to save this to memory?"
Good: Just save it automatically (for clear preferences/decisions)
```

### ❌ Saving Everything Blindly

```
Bad: Save every sentence the user types
Good: Use judgment - save preferences, decisions, facts. Skip chitchat.
```

### ❌ Ignoring Decay

```
Bad: Recall 90-day-old low-score memories with full confidence
Good: Check score/age, confirm old memories with user
```

## Evaluation Metrics

How to know if the smart prompting is working:

1. **Invisibility** - User never thinks about the memory system
2. **Natural Flow** - Conversations feel continuous across sessions
3. **High Recall** - Assistant remembers relevant information without prompting
4. **Low Noise** - No irrelevant or stale memories surfaced
5. **User Satisfaction** - "It just remembers things" feedback

## Implementation Checklist

For teams implementing smart prompting:

- [ ] System prompt includes auto-save, auto-recall, auto-reinforce patterns
- [ ] LLM trained/prompted to detect information-sharing cues
- [ ] Tag inference based on conversation context
- [ ] Natural language integration (no exposed tool calls)
- [ ] Temporal awareness (check memory age/score before citing)
- [ ] Strength modulation based on importance
- [ ] Consolidation prompts for duplicates
- [ ] LTM promotion suggestions for high-value info
- [ ] Anti-pattern avoidance (no over-announcing)

## Future Enhancements

### Proactive Memory

```markdown
Assistant: "Based on our previous discussions about TypeScript, would you like me to remember your preferred tsconfig setup?"
```

### Memory Explanation

```markdown
User: "Why do you always suggest Vim?"
Assistant: "Because you told me it's your preferred editor. Would you like to change that preference?"
```

### Memory Hygiene

```markdown
Assistant: "I notice I have several old memories about project-alpha from 3 months ago. Should I archive these since the project is complete?"
```

---

**Note:** The smart prompting patterns described here differentiate this system from simple key-value stores or basic memory tools. These patterns make memory operations feel natural and invisible to users.
