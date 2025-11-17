# Smart Prompt Interpretation for Memory Systems

**Version:** 0.2.0
**Last Updated:** 2025-01-07

## Overview

CortexGraph’s true power lies not in its MCP tools alone, but in how LLMs are taught to use them naturally. This document describes the smart prompt interpretation system — patterns and techniques for making AI assistants remember things like humans do, without explicit commands.

## Core Principle

> **Memory operations should be invisible to the user.**

When you tell a friend "I prefer tea over coffee," they remember without saying "OK, I'm saving that to my memory database." CortexGraph enables AI assistants to do the same through carefully designed system prompts.

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

### 5. Explicit Memory Requests (User-Initiated)

**When to trigger:**
- User explicitly asks you to remember something
- User wants to ensure something is saved
- User requests recall of specific information

**Examples:**

```
User: "Remember that I prefer tabs over spaces"
→ Save with high strength (user explicitly requested)

User: "Don't forget I'm allergic to shellfish"
→ Save with strength=2.0 (critical health info, explicit)

User: "Keep in mind that we use Python 3.11"
→ Save as normal preference

User: "What did I tell you about my database setup?"
→ Search for database memories, surface all relevant info
```

**Implementation Pattern:**
```python
# Detect explicit memory requests
explicit_save_phrases = [
    "remember that", "don't forget", "keep in mind",
    "save this", "make a note", "store this"
]

explicit_recall_phrases = [
    "what did i tell you about", "what do you remember about",
    "recall", "do you remember"
]

if matches_explicit_save(message):
    await save_memory(
        content=extract_content(message),
        strength=1.5,  # User-requested = important
        meta={"source": "explicit_request"}
    )
    # Acknowledge naturally: "Got it, I'll remember that."

if matches_explicit_recall(message):
    results = await search_memory(query=extract_query(message))
    # Present findings naturally
```

**Key Points:**
- Honor explicit requests immediately
- Use higher strength (1.5-2.0) for explicit saves
- Acknowledge briefly: "Got it" or "I'll remember that"
- Don't over-explain: No "I've saved this to memory ID..."

### 6. Direct to Long-Term Storage (Permanent Memory)

**When to trigger:**
- User explicitly requests permanent/permanent storage
- User uses emphatic language about never forgetting
- User wants to make a formal note for future reference
- Critical information that should never decay

**Trigger Phrases:**

```
"Never forget this..."
"Make a note..."
"Write this down..."
"Document this..."
"Record this permanently..."
"Add to my permanent notes..."
"Save to my knowledge base..."
```

**Examples:**

```
User: "Never forget that the API key rotation happens on the 1st of each month"
→ Save directly to LTM (Obsidian vault)
→ Folder: cortexgraph-promoted or appropriate category
→ No STM decay - permanent immediately

User: "Make a note: Sarah prefers she/her pronouns"
→ Save directly to LTM
→ Tag: [personal, preferences, pronouns]
→ Acknowledge: "Noted."

User: "Write this down - the production server IP is 192.168.1.100"
→ Save directly to LTM
→ High importance permanent record
→ Acknowledge briefly
```

**Implementation Pattern:**

```python
# Detect direct-to-LTM phrases
direct_ltm_phrases = [
    "never forget", "make a note", "write this down",
    "document this", "record this permanently",
    "add to my permanent notes", "save to my knowledge base"
]

if matches_direct_ltm(message):
    # Skip STM entirely - go straight to vault
    await write_to_vault(
        content=extract_content(message),
        folder=infer_folder(message),  # e.g., "cortexgraph-promoted", "critical-info"
        tags=infer_tags(message),
        frontmatter={
            "source": "direct_user_request",
            "priority": "permanent",
            "created": datetime.now().isoformat()
        }
    )
    # Acknowledge briefly: "Noted." or "Got it, recorded permanently."
```

**Key Differences from Regular Explicit Saves:**

| Phrase Type | Destination | Decay | Strength | Use Case |
|-------------|-------------|-------|----------|----------|
| Auto-save ("I prefer...") | STM | Yes (3-day half-life) | 1.0 | Normal context |
| Explicit ("Remember that...") | STM | Yes (slower decay) | 1.5-2.0 | Important info |
| Direct to LTM ("Never forget...") | LTM vault | No decay | N/A (permanent) | Critical/permanent |

**Acknowledgment Patterns:**

```
Good:
- "Noted."
- "Recorded."
- "Got it, saved permanently."
- "I've made a note of that."

Bad:
- "I've written this to file://vault/notes/mem_123.md with YAML frontmatter..."
- "Should I also save this to short-term memory?"
```

### 4. Auto-Observe (Natural Spaced Repetition) **NEW in v0.5.1**

**When to trigger:**
- After retrieving memories via search
- When you **actually use** memories to inform your response
- After incorporating memory content into your answer

**The "Maslow Effect":**

Just like humans remember Maslow's hierarchy better when it appears across multiple classes (history, economics, sociology), CortexGraph reinforces memories through natural cross-domain usage.

**Key Principle:** Only observe memories you actually **use**, not just retrieve.

**Examples:**

```
User: "Can you help with authentication in my API?"
→ Search for relevant memories: finds JWT preference (tags: [security, jwt, preferences])
→ Use memory to inform response: "Based on your JWT preferences..."
→ Observe memory usage: observe_memory_usage(["jwt-123"], ["api", "authentication", "backend"])
→ Cross-domain detected (0% tag overlap) → strength boosted 1.0 → 1.1
→ Next search naturally surfaces this memory if in danger zone

User: "What's my TypeScript convention for error handling?"
→ Search for memories: finds error handling pattern (tags: [typescript, error-handling, conventions])
→ Use memory in response: "You prefer using Result types for error handling..."
→ Observe usage: observe_memory_usage(["err-456"], ["typescript", "coding-style"])
→ Same domain (high tag overlap) → standard reinforcement
→ Memory review count incremented, review priority updated

User: "Remind me about the database setup?"
→ Search and retrieve database info
→ Present information to user
→ Observe usage: observe_memory_usage(["db-789"], ["database", "infrastructure"])
→ Memory reinforced through access
```

**Implementation Pattern:**

```python
# 1. Search for relevant memories
memories = await search_memory(
    query="authentication API",
    tags=["api", "auth"],
    limit=5
)

# 2. Use memories to inform response
response = generate_response_using_memories(memories)

# 3. Observe which memories were actually used
used_memory_ids = [m.id for m in memories if was_used_in_response(m, response)]

# 4. Record usage with context tags for cross-domain detection
if used_memory_ids:
    await observe_memory_usage(
        memory_ids=used_memory_ids,
        context_tags=extract_tags_from_query("authentication API")
    )
```

**When to Observe:**
- ✅ After using memory content in your response
- ✅ After building on previous context
- ✅ After confirming user preferences still apply
- ❌ NOT after every search (only when actually used)
- ❌ NOT for speculative retrieval
- ❌ NOT when memory wasn't relevant to answer

**Benefits:**
- **Cross-domain reinforcement:** Memories used in different contexts get stronger
- **Natural review:** Search automatically includes review candidates (30% of results)
- **No interruptions:** No "flashcard" style review sessions
- **Danger zone targeting:** Memories at risk (0.15-0.35 score) surface naturally

**Configuration:**
```bash
CORTEXGRAPH_AUTO_REINFORCE=true              # Enable auto-reinforcement (default)
CORTEXGRAPH_REVIEW_BLEND_RATIO=0.3           # 30% review candidates in search
CORTEXGRAPH_REVIEW_DANGER_ZONE_MIN=0.15      # Lower bound
CORTEXGRAPH_REVIEW_DANGER_ZONE_MAX=0.35      # Upper bound
```

## System Prompt Template

### For AI Assistants Using CortexGraph

```markdown
# Memory System Instructions

You have access to CortexGraph short‑term memory (STM) with temporal decay. Use it to remember important information about the user naturally.

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

4. **Observe Memory Usage (Natural Spaced Repetition - v0.5.1+)**
   - After using memories to inform your response
   - Record which memories you actually used (not just retrieved)
   - Provide context tags for cross-domain detection
   - Enables automatic reinforcement and natural review
   - Use `observe_memory_usage(memory_ids, context_tags)`

5. **Promote to Long-Term**
   - System automatically promotes high-value memories to permanent storage
   - No user notification needed - happens invisibly
   - Use unified search to access both STM and LTM seamlessly

5. **Direct to Permanent Storage**
   - When user says "Never forget...", "Make a note...", "Write this down..."
   - Save directly to LTM (Obsidian vault) bypassing STM
   - No decay, permanent immediately
   - Acknowledge briefly: "Noted." or "Recorded."

6. **Be Natural**
   - Don't announce "I'm saving this to memory"
   - Don't say "I found 3 matching memories"
   - Don't ask "Should I save this permanently?"
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

- `save_memory`: For preferences, decisions, facts, credentials (to STM)
- `search_memory`: Search with temporal filtering (auto-includes review candidates)
- `observe_memory_usage`: Record when memories are used in responses (enables natural spaced repetition)
- `touch_memory`: Explicitly reinforce a memory
- `write_note`: For permanent storage when user says "never forget", "make a note" (to LTM)
- `search_memory`: For recall and context retrieval (searches both STM and LTM)
- `touch_memory`: After successful recall to reinforce
- `promote_memory`: System handles automatically based on score/usage
- `gc`: System handles automatically (garbage collection)

## Memory Operation Tiers

**Tier 1 - Auto-save (Invisible):**
- User: "I prefer dark mode"
- Action: `save_memory(content="prefers dark mode", strength=1.0)`
- Destination: STM with 3-day half-life decay

**Tier 2 - Explicit (High Priority):**
- User: "Remember that I'm allergic to peanuts"
- Action: `save_memory(content="allergic to peanuts", strength=2.0)`
- Destination: STM with slower decay (higher strength)

**Tier 3 - Direct to Permanent:**
- User: "Never forget: production deploy is Fridays at 3pm"
- Action: `write_note(title="Production Deploy Schedule", content="...")`
- Destination: LTM vault (permanent, no decay)
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

The system automatically promotes high-value memories to LTM (Obsidian vault). This happens invisibly based on:

1. **Auto-Promote** - Memories meeting criteria (score ≥ 0.65 OR use_count ≥ 5) move to LTM automatically
2. **Unified Search** - Search pulls from both STM (recent) and LTM (permanent) seamlessly
3. **Natural References** - Cite LTM content as if you naturally remember it

```markdown
## Long-Term Memory Integration

Promotion happens automatically and invisibly:
- High-score memories (≥ 0.65): Promoted immediately
- Frequently accessed (≥ 5 touches in 14 days): Promoted automatically
- No announcement to user - just works
- Use unified search to pull from both STM and LTM
- Reference promoted content naturally in conversations
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

- [ ] System prompt includes auto-save, auto-recall, auto-reinforce, auto-promote patterns
- [ ] LLM trained/prompted to detect information-sharing cues
- [ ] Direct-to-LTM phrase detection ("never forget", "make a note", "write this down")
- [ ] Tag inference based on conversation context
- [ ] Natural language integration (no exposed tool calls)
- [ ] Temporal awareness (check memory age/score before citing)
- [ ] Strength modulation based on importance
- [ ] Consolidation prompts for duplicates
- [ ] Automatic LTM promotion for high-value info (invisible to user)
- [ ] Anti-pattern avoidance (no over-announcing or asking permission)

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
