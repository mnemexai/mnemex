# Feature: Auto-Recall Related Memories During Conversation

**Status**: Backlog
**Priority**: High
**Version Target**: v0.7.0 (Natural Language Activation Phase 2)
**Created**: 2025-11-14
**Author**: Identified during GC analysis session

## Problem Statement

Natural language activation (v0.6.0) currently only works for **saving** new memories conversationally. Important memories fade from disuse because the system doesn't automatically:

1. Search for related memories when user discusses topics
2. Surface relevant context during conversation
3. Reinforce accessed memories naturally

**Real-world impact**: Research memories about STOPPER, publication strategy, e-FIT framework all decayed to near-GC threshold (score < 0.05) despite containing valuable information, because they weren't being accessed through conversation.

## Current Workarounds

Users must manually:
- Search for topics periodically (`search_memory(query="stopper")`)
- Batch-reinforce by tags (`search → touch_memory` workflow)
- Schedule "memory review" sessions

This breaks the natural flow and defeats the purpose of conversational memory.

## Proposed Solution

### Auto-Recall Pipeline

```
User message received
    ↓
Analyze for topics/entities (background)
    ↓
Search memory for related content
    ↓
[If high relevance] Surface in context
    ↓
Automatically reinforce via observe_memory_usage
    ↓
Track cross-domain usage patterns
```

### Key Components

**1. Message Analysis (Passive)**
- Extract topics, entities, concepts from user messages
- Use existing `analyze_for_recall` as foundation
- Lightweight - don't block conversation flow
- Trigger on: questions, topic shifts, sustained discussion

**2. Background Memory Search**
- Search short-term memory for related content
- Use semantic similarity (embeddings) + keyword matching
- Threshold: Only surface if relevance > 0.7
- Limit: Top 3 memories max to avoid noise

**3. Contextual Surfacing**
- **Non-intrusive**: Don't interrupt with "I remember..."
- **Options**:
  - A) Silent reinforcement (just update scores, don't surface)
  - B) Subtle injection ("Based on your earlier note about...")
  - C) Available on request ("I found 3 related memories - would you like to see them?")

**4. Automatic Reinforcement**
- Call `observe_memory_usage(memory_ids, context_tags)` automatically
- Update last_used, use_count, review_priority
- Detect cross-domain usage (Maslow effect)
- Apply strength boosts when appropriate

**5. User Controls**
```python
# Configuration options
AUTO_RECALL_ENABLED=true                    # Master switch
AUTO_RECALL_MODE=silent|subtle|interactive  # How to surface
AUTO_RECALL_RELEVANCE_THRESHOLD=0.7         # Min similarity
AUTO_RECALL_MAX_RESULTS=3                   # Limit per query
AUTO_RECALL_MIN_INTERVAL=300                # Cooldown (5 min)
```

## Implementation Phases

### Phase 1: Silent Reinforcement (MVP)
- Detect topics in user messages
- Search for related memories (background)
- Automatically reinforce via `observe_memory_usage`
- No surfacing - just prevent decay
- **Deliverable**: Important memories stop fading from disuse

### Phase 2: Subtle Surfacing
- Add "subtle" mode - inject context naturally
- Example: "Based on your earlier note about STOPPER timing windows..."
- LLM decides when/how to reference memories
- **Deliverable**: Conversations feel more contextual

### Phase 3: Interactive Mode
- Add user-controlled surfacing
- "I found 3 related memories about this topic - would you like to see them?"
- Allow inspection before surfacing
- **Deliverable**: User control over memory injection

### Phase 4: Cross-Domain Detection (Maslow Effect)
- Track when memories are accessed in different contexts
- Boost strength for cross-domain usage
- Build knowledge graph connections
- **Deliverable**: Natural spaced repetition through conversation

## Technical Architecture

### New Components

**1. ConversationAnalyzer**
```python
class ConversationAnalyzer:
    """Analyze messages for recall opportunities."""

    def extract_topics(self, message: str) -> list[str]:
        """Extract topics/entities from message."""

    def should_trigger_recall(self, message: str, history: list[str]) -> bool:
        """Decide if this message warrants memory search."""

    def get_context_tags(self, message: str) -> list[str]:
        """Extract tags representing current context."""
```

**2. AutoRecallEngine**
```python
class AutoRecallEngine:
    """Orchestrate automatic memory recall."""

    def process_message(self, message: str) -> RecallResult:
        """Main entry point - analyze and recall."""

    def search_related(self, topics: list[str]) -> list[Memory]:
        """Search for related memories."""

    def reinforce_silently(self, memories: list[Memory], context: list[str]):
        """Update scores without surfacing."""

    def should_surface(self, memories: list[Memory]) -> bool:
        """Decide if memories should be surfaced to user."""
```

**3. MCP Tool: configure_auto_recall**
```python
@mcp.tool()
def configure_auto_recall(
    enabled: bool = True,
    mode: str = "silent",
    relevance_threshold: float = 0.7,
    max_results: int = 3,
) -> dict:
    """Configure auto-recall behavior."""
```

### Integration Points

**Server-side integration** (cortexgraph/server.py):
```python
# Add middleware to process messages
async def process_message_middleware(message: str):
    if config.auto_recall_enabled:
        recall_engine.process_message(message)
    # Continue normal flow
```

**Tool response enhancement**:
```python
# Existing tools can check for related memories
def save_memory(...):
    # ... normal save logic ...

    # Check for related memories
    if config.auto_recall_mode == "subtle":
        related = recall_engine.search_related(entities)
        if related:
            return {
                **result,
                "related_memories": [m.id for m in related],
                "hint": f"Found {len(related)} related memories"
            }
```

## Success Metrics

**Quantitative**:
- Reduction in GC candidates (fewer important memories decay)
- Increase in memory reinforcement events
- Cross-domain usage detection rate
- Average score of research-tagged memories

**Qualitative**:
- Conversations feel more contextual
- Users report "it remembers what I told it"
- Reduced need for manual memory review sessions
- Natural spaced repetition working

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Over-surfacing (annoying) | User disables feature | Conservative thresholds, cooldown timers |
| Performance hit | Slow responses | Background processing, async search |
| Privacy concerns | Unexpected memory surfacing | User controls, clear settings |
| False positives | Irrelevant memories | Tune relevance threshold, user feedback |
| Token costs | Expensive for LLM | Silent mode first, batch processing |

## Dependencies

- ✅ Existing: `analyze_for_recall` tool (v0.6.0)
- ✅ Existing: `observe_memory_usage` tool (v0.5.1)
- ✅ Existing: Embedding-based similarity search
- ⏳ New: Conversation context tracking
- ⏳ New: Auto-recall configuration system
- ⏳ New: Background processing pipeline

## Related Features

- **Natural Language Activation** (v0.6.0) - Auto-save foundation
- **Spaced Repetition** (v0.5.1) - Review priority system
- **Consolidation** (v0.4.0) - Knowledge graph connections
- **Embeddings** (optional) - Semantic similarity search

## References

- Issue: #TBD
- Original discussion: GC analysis session 2025-11-14
- Related: Natural Language Activation design (docs/design/natural-activation.md)
- Research: Maslow effect, cross-domain reinforcement

## Questions to Resolve

1. **Surfacing strategy**: Silent, subtle, or interactive by default?
2. **Threshold tuning**: What relevance score prevents over-surfacing?
3. **Cooldown timing**: How often can auto-recall trigger?
4. **Context window**: How many previous messages to analyze?
5. **Performance**: Background vs. synchronous processing?

## Next Steps

1. Create GitHub issue for tracking
2. Prototype silent reinforcement (Phase 1 MVP)
3. Test with real conversations to tune thresholds
4. Gather user feedback on surfacing preferences
5. Iterate based on usage patterns

---

**Status Updates**:
- 2025-11-14: Feature specified, added to backlog
