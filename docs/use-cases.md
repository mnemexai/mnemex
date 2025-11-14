# CortexGraph Use Cases

Based on the repository documentation and architecture, here are the appropriate use cases for CortexGraph:

## 1. **Personal AI Assistant Memory**

**Scenario**: You regularly chat with Claude about various topics
- Remember your **preferences** (coding style, communication preferences, dietary restrictions)
- Recall **past decisions** and their reasoning
- Track **ongoing projects** and their status
- Remember **personal context** (family names, pet names, important dates)

**Example**: "I prefer tabs over spaces" gets saved once, reinforced over time, and Claude remembers it months later without you repeating it.

---

## 2. **Software Development Assistant**

**Scenario**: Using Claude for coding across multiple projects
- Remember **architecture decisions** and rationale
- Track **bugs you've encountered** and solutions
- Recall **library preferences** and why you chose them
- Remember **API patterns** you've established
- Track **tech debt** and future refactoring notes

**Example**: Claude remembers you prefer React hooks over class components, your ESLint config preferences, and that one weird TypeScript issue you solved last month.

---

## 3. **Context Switching for Developers**

**Scenario**: Jumping between multiple codebases/projects
- **Aggressive forgetting** for ephemeral context
- Quick recall of **project-specific conventions**
- Remember **which commands to run** for each project
- Track **environment setup quirks**

**Example**: Set shorter decay (1-day half-life) so context from Project A fades quickly when you switch to Project B, preventing confusion.

---

## 4. **Research & Learning**

**Scenario**: Using Claude to learn new topics or conduct research
- Build a **knowledge graph** of concepts and their relationships
- Remember **key insights** from papers/articles
- Track **questions to explore** later
- Link **related concepts** across domains
- **Spaced repetition** naturally surfaces concepts that need review

**Example**: Learning Rust - Claude remembers the ownership rules you struggled with and brings them up when relevant, strengthening that memory through use.

---

## 5. **Writing & Content Creation**

**Scenario**: Working on long-form content with Claude
- Remember **style guidelines** and tone preferences
- Track **character details** for fiction writing
- Recall **research findings** relevant to your topic
- Remember **audience preferences** and feedback
- Track **ideas for future articles**

**Example**: Writing a blog series - Claude remembers your target audience, writing style, and callbacks to previous posts without you re-explaining each time.

---

## 6. **Personal Knowledge Management (PKM)**

**Scenario**: Building a second brain with Obsidian integration
- **Auto-generate Obsidian notes** from conversations
- Link memories to your **existing note structure**
- Automatic **tagging and entity extraction**
- Build connections between **conversation insights** and permanent notes
- Search across both **ephemeral and permanent** knowledge

**Example**: Your Obsidian vault becomes enriched with conversation insights that auto-promote to permanent notes when they prove valuable over time.

---

## 7. **Preference-Heavy Applications**

**Scenario**: Any domain where user preferences matter a lot
- **Design preferences** (color schemes, layouts)
- **Workflow preferences** (automation preferences, tool choices)
- **Communication style** (formal vs casual, emoji usage)
- **Accessibility needs** (screen reader usage, keyboard shortcuts)

**Example**: Claude remembers you're colorblind and always suggests colorblind-friendly palettes without asking.

---

## 8. **Long-Term Projects & Planning**

**Scenario**: Multi-month projects with Claude as a collaborator
- Track **project goals** and evolution
- Remember **stakeholder feedback**
- Recall **past iterations** and why they changed
- Monitor **progress milestones**
- Link related **sub-projects** and dependencies

**Example**: Building a SaaS product over 6 months - Claude remembers your MVP scope, feature requests you've deferred, and technical constraints.

---

## 9. **Team Knowledge Sharing**

**Scenario**: Shared memory store for team AI interactions
- Document **team conventions** and decisions
- Build **institutional knowledge** graph
- Remember **common problems** and solutions
- Track **who knows what** (entity linking)
- Create searchable **decision log**

**Example**: Team members can query why certain architectural decisions were made, with memories strengthening as multiple people reference them.

---

## 10. **Domain-Specific Expertise**

**Scenario**: Using Claude in specialized domains
- **Medical/Healthcare**: Remember patient interaction patterns (anonymized)
- **Legal**: Track case precedents and reasoning
- **Education**: Remember student learning patterns
- **Finance**: Recall market analysis insights
- **Scientific Research**: Build knowledge graphs of experiments and findings

**Example**: A researcher remembers which experiments failed and why, preventing repeated mistakes.

---

## 11. **Adaptive AI Behavior**

**Scenario**: You want Claude's behavior to adapt over time
- **Natural spaced repetition** - memories in danger of forgetting surface naturally
- **Cross-context detection** - memories used in multiple domains get stronger
- **Automatic importance weighting** - frequently-used memories survive
- **Graceful forgetting** - ephemeral context naturally fades

**Example**: Claude stops asking about your Python version after the 5th conversation where it's mentioned and used.

---

## When NOT to Use CortexGraph

❌ **High-security secrets** - Use proper secret management (see `docs/security.md`)
❌ **Regulated data (PHI, PII)** - Compliance concerns unless properly configured
❌ **Real-time high-throughput** - Designed for assistant conversations, not APIs
❌ **Exact recall requirements** - Temporal decay means memories can be forgotten
❌ **Multi-user production systems** - Single-user design (as of v0.5.3)

---

## Configuration for Different Use Cases

From `docs/configuration.md` and `src/cortexgraph/config.py:1`:

### For Development (fast context switching)
```json
{
  "decay_half_life_hours": 24,
  "forget_threshold": 0.1,
  "review_lower_bound": 0.2
}
```

### For Research/Archival (long retention)
```json
{
  "decay_half_life_hours": 168,
  "forget_threshold": 0.03,
  "promote_threshold": 0.5
}
```

### For Personal Assistant (balanced)
```json
{
  "decay_half_life_hours": 72,
  "forget_threshold": 0.05,
  "promote_threshold": 0.65
}
```

---

## Bottom Line

CortexGraph is best for **individual knowledge workers** who want their AI assistant to remember context across conversations, with memory dynamics that feel natural rather than robotic. It's particularly powerful when combined with **Obsidian** for building a hybrid ephemeral/permanent knowledge base.

The temporal decay ensures Claude doesn't get confused by outdated context, while the reinforcement mechanics ensure important information naturally persists.
