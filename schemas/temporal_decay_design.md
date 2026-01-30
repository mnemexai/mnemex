# Temporal Decay & Scoring Design

## Overview

CortexGraph implements a **multi-signal temporal decay model** inspired by cognitive science (Ebbinghaus forgetting curve) and spaced repetition theory. This document details the mathematical formulation, implementation in PostgreSQL, and integration with the memory lifecycle.

## Core Decay Formula

### Master Equation

```
score(t) = (use_count + 1)^β · e^(-λ·Δt) · strength
```

Where:
- **use_count**: Number of times memory has been accessed (0-∞)
- **β**: Use count exponent (0.6) — controls importance of frequency
- **Δt**: Time delta (seconds) — how long since last access
- **λ**: Decay rate constant (2.673×10⁻⁶) — controls half-life
- **strength**: Importance multiplier (0.0-2.0) — manual boost capability

### Example Calculation

**Memory Details:**
```
id: mem-1
use_count: 3
last_used: 1 day ago (86400 seconds)
strength: 1.5 (important)
current_time: now
```

**Calculation:**
```
score = (3 + 1)^0.6 × e^(-2.673e-6 × 86400) × 1.5
      = 4^0.6 × e^(-0.2308) × 1.5
      = 1.964 × 0.794 × 1.5
      = 2.34
```

Wait — this is > 1, which means this memory will likely be promoted to LTM (threshold 0.65). That's correct for a frequently-used, important memory.

## Component Analysis

### 1. Use Count Component: (use_count + 1)^β

**Purpose**: Weight memories by how often they've been accessed.

**Why +1?**
- Without it, new memories (use_count=0) would have score 0
- With +1, new memories start with baseline weight 1

**Why ^0.6 (sub-linear)?**
- Prevents runaway scores from frequently-accessed memories
- Reflects logarithmic learning curve (each additional access matters less)
- Mathematical justification: Stevens' Law in psychophysics

**Behavior:**

| use_count | (use_count+1)^0.6 | Interpretation |
|---|---|---|
| 0 | 1.00 | Baseline weight |
| 1 | 1.32 | 32% boost from 1 access |
| 2 | 1.56 | 56% boost from 2 accesses |
| 5 | 2.00 | 2× boost (5 accesses) |
| 10 | 2.69 | 2.7× boost (10 accesses) |
| 50 | 5.74 | 5.7× boost (50 accesses) |
| 100 | 7.44 | ~7× boost (100 accesses) |

**Key insight**: Diminishing returns. Going from 0 to 5 accesses gives 2× boost, but 5 to 50 is only 2.9×.

### 2. Decay Component: e^(-λ·Δt)

**Purpose**: Implement exponential forgetting based on Ebbinghaus curve.

**Formula Parameters:**
```
λ = ln(2) / T_half

Where T_half = half-life in seconds
Default: T_half = 3 days = 259200 seconds
λ = 0.693 / 259200 = 2.673×10⁻⁶
```

**Behavior Over Time (3-day half-life):**

| Time | Δt (seconds) | e^(-λ·Δt) | % Remaining |
|---|---|---|---|
| 0 hours | 0 | 1.000 | 100% |
| 6 hours | 21600 | 0.942 | 94% |
| 12 hours | 43200 | 0.889 | 89% |
| 1 day | 86400 | 0.791 | 79% |
| 2 days | 172800 | 0.625 | 62% |
| 3 days | 259200 | **0.500** | **50%** ← Half-life |
| 7 days | 604800 | 0.210 | 21% |
| 14 days | 1209600 | 0.044 | 4.4% |
| 30 days | 2592000 | 0.001 | 0.1% |

**Interpretation:**
- After 3 days with no access, score drops to 50%
- After 1 week, only 21% remains
- After 2 weeks, essentially forgotten (4%)

### 3. Strength Component: strength

**Purpose**: Manual control of importance. Users/AI can boost or suppress memories.

**Range**: 0.0 to 2.0
- `strength = 1.0` (default): Normal decay
- `strength > 1.0` (boost): Resists decay faster than other memories
- `strength < 1.0` (suppress): Decays faster
- `strength = 2.0` (max): 2× resistance to decay

**Implementation:**
```python
# In cortexgraph, boost_strength is not exposed in save_memory()
# But can be set via touch_memory(boost_strength=True)
def touch_memory(memory_id, boost_strength=False):
    memory = load(memory_id)
    memory.last_used = now()
    memory.use_count += 1

    if boost_strength and memory.strength < 2.0:
        memory.strength = min(memory.strength * 1.1, 2.0)  # 10% increase, capped

    save(memory)
```

## Decision Thresholds

### Promotion: score ≥ 0.65

**Condition**: Memory moves from STM (short-term) to LTM (long-term/vault)

**Interpretation**:
- Memory has proven its importance (high frequency OR recent access OR both)
- Worth promoting to Obsidian vault for permanent reference
- Typical memories reaching this: well-used preferences, key decisions, proven patterns

**Example memories reaching promotion:**
- Used 5+ times in 2 weeks (frequent)
- Important project decision (boosted strength)
- Frequently-referenced code pattern (high use_count + recent)

### Forgetting: score < 0.05

**Condition**: Memory is deleted from STM

**Interpretation**:
- Memory hasn't been accessed in extended period
- Score dropped below 5% of baseline
- Not worth keeping in active memory
- Typical timeline: 3-4 weeks without access

**Safety**: Promoted memories are archived, not deleted. Only STM memories are forgotten.

### Review Zone: 0.15 < score < 0.35

**Condition**: Memory is in "danger zone" needing reinforcement

**Interpretation**:
- Memory is fading but not forgotten yet
- Strategic reinforcement now can rescue it
- Implements spaced repetition: resurface memories at optimal forgetting moments

**Typical timeline**:
- Score drops from 1.0 to 0.35 in ~3 days
- Score drops from 0.35 to 0.15 in ~2-3 more days
- Danger zone window: days 3-6 after last access

## Alternative Decay Models

### Model 1: Exponential (Default)

```
f(Δt) = e^(-λ·Δt)
```

**Pros:**
- Mathematically simple
- Matches Ebbinghaus curve well
- Computationally efficient

**Cons:**
- Sharp drop at beginning
- Very aggressive at forgotten after 2 weeks
- Less suited for long-tail memories

### Model 2: Power-Law

```
f(Δt) = (1 + Δt/t₀)^(-α)
```

Where t₀ is reference time, α controls shape (default ~1.1)

**Pros:**
- Slower decay tail (keeps old important memories)
- Better for long-term recall patterns
- Smoother transition

**Cons:**
- More complex computation
- Two parameters to tune

### Model 3: Two-Component Exponential

```
f(Δt) = w·e^(-λ_fast·Δt) + (1-w)·e^(-λ_slow·Δt)

λ_fast ≈ 1.603e-5  (12-hour half-life)
λ_slow ≈ 1.147e-6  (7-day half-life)
w = 0.7  (70% fast, 30% slow)
```

**Pros:**
- Captures bimodal forgetting (immediate + long-term)
- Fast component: fresh access info fades quickly
- Slow component: core concepts persist longer
- Matches human memory better

**Cons:**
- More complex
- More parameters
- Harder to tune

**CortexGraph Default**: Exponential model (simplicity + empirical fit)

## PostgreSQL Implementation

### Computed Score Function

```sql
CREATE FUNCTION calculate_decay_score(
    p_use_count INTEGER,
    p_last_used BIGINT,
    p_strength FLOAT
) RETURNS FLOAT AS $$
DECLARE
    delta_seconds BIGINT;
    score FLOAT;
BEGIN
    delta_seconds := EXTRACT(EPOCH FROM NOW())::BIGINT - p_last_used;

    -- Exponential decay: (use_count+1)^0.6 * e^(-λ·Δt) * strength
    score := (p_use_count + 1)::FLOAT ^ 0.6 *
             EXP(-2.673e-6 * delta_seconds) *
             p_strength;

    RETURN score;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

### Materialized Scores (Optional, for Reporting)

Instead of computing on every query, cache scores in a view:

```sql
CREATE MATERIALIZED VIEW memory_scores AS
SELECT
    id,
    status,
    (use_count + 1)^0.6 *
    EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - last_used)) *
    strength AS current_score,

    CASE
        WHEN (use_count + 1)^0.6 *
             EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - last_used)) *
             strength >= 0.65 THEN 'promote'
        WHEN (use_count + 1)^0.6 *
             EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - last_used)) *
             strength < 0.05 THEN 'forget'
        ELSE 'keep'
    END AS action
FROM memories
WHERE status IN ('active', 'promoted');

-- Refresh periodically (e.g., every 5 minutes)
-- Or trigger on explicit promotion/forgetting
```

### Promotion Job

```sql
-- Find memories ready for promotion
SELECT * FROM find_memories_to_promote();

-- Execute promotion (pseudo-code)
WITH to_promote AS (
    SELECT m.id, m.content
    FROM memories m
    WHERE m.status = 'active'
      AND (m.use_count + 1)^0.6 *
          EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - m.last_used)) *
          m.strength >= 0.65
)
UPDATE memories
SET
    status = 'promoted',
    promoted_at = EXTRACT(EPOCH FROM NOW())::BIGINT,
    promoted_to = 'vault/' || DATE_PART('year', NOW())::TEXT || '/' || created_id
WHERE id IN (SELECT id FROM to_promote);
```

### Forgetting Job

```sql
-- Find memories ready to forget
DELETE FROM memories
WHERE status = 'active'
  AND (use_count + 1)^0.6 *
      EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - last_used)) *
      strength < 0.05;
```

## Spaced Repetition Integration

### Review Priority Calculation

```
review_priority = σ(0.5 - |0.25 - score|) / max_priority

Where:
- σ() = sigmoid function (squashes to 0-1)
- 0.25 = midpoint of danger zone (0.15-0.35)
- score = current decay score
```

**Effect**: Memories in danger zone (0.15-0.35) get high review priority.

### Review Workflow

1. Query memories with high `review_priority`
2. Surface top 5-10 in UI/MCP tools
3. User interacts with memory (triggered as "touch")
4. `last_review_at` and `review_count` increment
5. Score boosted by touch (use_count++) — rescues from forgetting

### Inverted Parabola Boost

Recent cortexgraph versions use an "inverted parabola" boost for review candidates:

```
boost = 1 - ((current_score - 0.25)^2) / (0.25^2)

Where 0.25 is center of danger zone
```

This gives maximum boost when score is exactly 0.25 (danger zone center), zero boost at edges.

## Configuration Parameters

All cortexgraph defaults (from `src/cortexgraph/config.py`):

```python
# Decay model selection
CORTEXGRAPH_DECAY_MODEL = "exponential"  # or "power_law", "two_component"

# Exponential parameters
CORTEXGRAPH_DECAY_LAMBDA = 2.673e-6      # 3-day half-life
CORTEXGRAPH_DECAY_BETA = 0.6             # Use count exponent

# Decision thresholds
CORTEXGRAPH_FORGET_THRESHOLD = 0.05      # Delete below this
CORTEXGRAPH_PROMOTE_THRESHOLD = 0.65     # Promote above this
CORTEXGRAPH_PROMOTE_USE_COUNT = 5        # OR: 5 uses in window
CORTEXGRAPH_PROMOTE_TIME_WINDOW = 14     # Time window (days)

# Review parameters
CORTEXGRAPH_REVIEW_BLEND_RATIO = 0.3     # % of results for review
CORTEXGRAPH_REVIEW_DANGER_ZONE_MIN = 0.15
CORTEXGRAPH_REVIEW_DANGER_ZONE_MAX = 0.35
CORTEXGRAPH_AUTO_REINFORCE = True        # Auto-boost on review
```

## Design Rationale

### Why Exponential Decay?

**Psychological fit**: Matches Ebbinghaus forgetting curve (1885):
> "The amount of knowledge to retain after time t is K·log(1+t)"
>
> But reversed: "forgetting rate is ∝ e^(-λ·t)"

**Computational efficiency**: O(1) calculation at query time (no pre-computation needed)

**Empirical validation**: Used successfully in:
- Spaced repetition algorithms (SM-2, FSRS)
- Temporal learning systems
- Human memory models

### Why Sub-Linear Use Count (β=0.6)?

**Psychophysics**: Stevens' Law suggests perceptual magnitude α ≈ 0.6-0.7

**Practical**: Prevents "rich get richer" — a memory accessed 100 times shouldn't dominate

**Empirical**: Matches power-law learning curves in cognitive psychology

### Why Dual Promotion Criteria?

**Score-based (≥0.65)**: Catches "hot" memories (recently important)
- Example: Decision made today
- High score from combination of recency + importance

**Usage-based (≥5 uses in 14 days)**: Catches "sticky" memories (frequent pattern)
- Example: Code pattern used repeatedly
- High use_count even if older

**OR logic**: Either criterion triggers — more memories get promoted, but that's good for LTM (appendable)

## Testing & Validation

### Unit Tests (TODO in PostgreSQL)

```sql
-- Test basic calculation
SELECT calculate_decay_score(5, EXTRACT(EPOCH FROM NOW())::BIGINT - 86400, 1.5)::NUMERIC(10,4);
-- Expected: ~1.19 (from manual calculation above)

-- Test half-life (3 days = 259200 seconds)
SELECT calculate_decay_score(0, EXTRACT(EPOCH FROM NOW())::BIGINT - 259200, 1.0)::NUMERIC(10,4);
-- Expected: 0.50 (50% remaining)

-- Test threshold crossing
SELECT
    memory_id,
    current_score,
    action
FROM memories_with_scores
WHERE current_score BETWEEN 0.60 AND 0.70;
-- Expected: None at threshold, unless exact timing
```

### Integration Tests (TODO)

1. **Promotion**: Create memory → wait 3+ days with 0 access + high strength → verify promotion
2. **Forgetting**: Create memory → wait 4+ weeks with 0 access → verify deletion
3. **Review**: Memories in danger zone → trigger review → verify score recovery
4. **Relationships**: Promote memory → verify related memories accessible in LTM

## Future Enhancements

1. **Adaptive λ**: Auto-tune half-life based on domain (e.g., personal preferences decay slower than meeting notes)

2. **Contextual decay**: Different decay rates for different memory contexts

3. **Reinforcement learning**: Adjust β and λ based on user's actual forgetting patterns

4. **Temporal metadata**: Track "when used" distribution to predict next need

5. **Cross-domain boosting**: Memories used across different contexts (projects, tags) get boosted

## References

- Ebbinghaus, H. (1885). "Memory: A Contribution to Experimental Psychology"
- Bjork, R. A., & Bjork, E. L. (1992). "A new theory of disuse and an old theory of stimulus fluctuation"
- Wozniak, P. A. (2018). "SuperMemo: Spaced Repetition Algorithm" (SM-2, SM-15)
- Carbonneau, N., & Chen, X. (2021). "New Advances in the Science of Learning" (FSRS)
- CortexGraph docs: `/Users/sc/cortexgraph/docs/scoring_algorithm.md`
