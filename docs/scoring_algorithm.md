# Temporal Decay Scoring Algorithm

**Version:** 0.2.0
**Last Updated:** 2025-01-07

## Overview

CortexGraph uses a novel temporal decay algorithm that mimics human memory dynamics. Memories naturally fade over time unless reinforced through use. This document explains the mathematical model, parameter tuning, and design rationale.

## Model Selection

CortexGraph supports three decay models. Choose per use case via `CORTEXGRAPH_DECAY_MODEL`:

1. Power‑Law (default):
   $$ f(\Delta t) = \left(1 + \frac{\Delta t}{t_0}\right)^{-\alpha} $$
   - Heavier tail; retains older-but-important memories better.
   - Parameters: $\alpha$ (shape), $t_0$ (characteristic time). We derive $t_0$ from a chosen half‑life $H$ via $t_0 = H / (2^{1/\alpha} - 1)$.

2. Exponential:
   $$ f(\Delta t) = e^{-\lambda\,\Delta t} $$
   - Lighter tail; simpler and forgets sooner.
   - Parameter: $\lambda$ (from half‑life).

3. Two‑Component Exponential:
   $$ f(\Delta t) = w\,e^{-\lambda_f\,\Delta t} + (1-w)\,e^{-\lambda_s\,\Delta t} $$
   - Forgets very recent items faster (fast component) but keeps a heavier tail (slow component).
   - Parameters: $\lambda_f, \lambda_s, w$.

Combined score (all models):
$$
\text{score} = (n_{\text{use}})^\beta \cdot f(\Delta t) \cdot s
$$

## Core Formula

$$
\text{score} = (n_{\text{use}})^\beta \cdot e^{-\lambda \cdot \Delta t} \cdot s
$$

Where:
- $n_{\text{use}}$: Number of times the memory has been accessed (touches)
- $\beta$ (beta): Use count weight exponent (default: 0.6)
- $\lambda$ (lambda): Decay constant (default: $2.673 \times 10^{-6}$ for 3-day half-life)
- $\Delta t$: Time delta in seconds since last access ($t_{\text{now}} - t_{\text{last used}}$)
- $s$: Base multiplier (range: 0.0-2.0, default: 1.0)

## Parameter Reference (at a glance)

- $\beta$ (beta): Sub-linear exponent for use count.
  - Default: 0.6; Range: 0.0–1.0
  - Higher → frequent memories gain more; Lower → emphasize recency
- $\lambda$ (lambda): Exponential decay constant.
  - Computed from half-life: $\lambda = \ln(2) / t_{1/2}$
  - Example values: 1-day = $8.02\times 10^{-6}$, 3-day = $2.67\times 10^{-6}$, 7-day = $1.15\times 10^{-6}$
- $\Delta t$: Seconds since last use.
  - Larger $\Delta t$ → lower score via $e^{-\lambda\Delta t}$
- $s$ (strength): Importance multiplier.
  - Default: 1.0; Range: 0.0–2.0; Can be nudged by touch with boost
- $\tau_{\text{forget}}$: Forget threshold.
  - Default: 0.05; If score < $\tau_{\text{forget}}$ → forget
- $\tau_{\text{promote}}$: Promote threshold.
  - Default: 0.65; If score ≥ $\tau_{\text{promote}}$ → promote
- Usage promotion rule: $n_{\text{use}} \ge 5$ within 14 days (configurable)
  - Captures frequently referenced info even if not extremely recent

## Components Explained

### 1. Use Count Component: $(n_{\text{use}})^\beta$

**Purpose:** Reward frequently accessed memories.

**Why Exponent?**
- Linear growth ($\beta=1.0$) over-rewards high use counts
- Sub-linear ($\beta<1.0$) provides diminishing returns
- Default $\beta=0.6$ balances reward vs. diminishing returns

**Examples:**

| Use Count | $n^{0.6}$ | Boost Factor |
|-----------|-----------|--------------|
| 1         | 1.00      | 1.0x         |
| 5         | 2.63      | 2.6x         |
| 10        | 3.98      | 4.0x         |
| 50        | 11.45     | 11.4x        |

**Tuning Guidelines:**
- **Higher $\beta$** (0.8-1.0): Strongly favor frequently used memories
- **Lower $\beta$** (0.3-0.5): Reduce impact of use count, emphasize recency
- **$\beta=0.0$**: Disable use count entirely (pure temporal decay)

### 2. Decay Component: $e^{-\lambda \cdot \Delta t}$

**Purpose:** Exponential decay over time ([Ebbinghaus forgetting curve](https://en.wikipedia.org/wiki/Forgetting_curve)).

**Why Exponential?**
- Models human memory better than linear decay
- Creates natural "forgetting" behavior
- Continuous and smooth (no sudden drops)

**Half-Life Calculation:**

$$
\lambda = \frac{\ln(2)}{t_{1/2}}
$$

Where $t_{1/2}$ is the half-life in seconds.

For a 3-day half-life:

$$
\lambda = \frac{\ln(2)}{3 \times 86400} = 2.673 \times 10^{-6}
$$

**Decay Curves:**

```
Time Since Last Use | Score Multiplier (λ=3-day half-life)
--------------------|-------------------------------------
0 hours             | 1.000 (100%)
12 hours            | 0.917 (92%)
1 day               | 0.841 (84%)
3 days              | 0.500 (50%) ← Half-life
7 days              | 0.210 (21%)
14 days             | 0.044 (4%)
30 days             | 0.001 (0.1%)
```

**Tuning Guidelines:**
- **1-day half-life** ($\lambda=8.02 \times 10^{-6}$): Aggressive decay, forget quickly
- **3-day half-life** ($\lambda=2.67 \times 10^{-6}$): Default, balanced retention
- **7-day half-life** ($\lambda=1.15 \times 10^{-6}$): Gentle decay, longer retention
- **14-day half-life** ($\lambda=5.73 \times 10^{-7}$): Very gentle, archives slowly

### 3. Strength Multiplier

**Purpose:** Boost or dampen specific memories based on importance.

**Range:** 0.0 to 2.0
- **0.0-0.5**: Low priority, ephemeral
- **1.0**: Normal (default)
- **1.5-2.0**: High priority, critical

**Use Cases:**
```python
# Security credentials - critical
strength = 2.0

# User preferences - important
strength = 1.5

# Normal conversation context
strength = 1.0

# Tentative ideas, exploratory thoughts
strength = 0.5
```

**Strength Over Time:**
- Can be increased via `touch_memory(boost_strength=True)`
- Caps at 2.0 to prevent runaway growth
- Only way to "permanently" resist decay (besides re-touching)

## Decision Thresholds

### Forget Threshold: $\tau_{\text{forget}} = 0.05$

**Purpose:** Delete memories with very low scores.

**Rationale:**
- Below 5% of original score → likely irrelevant
- Prevents database bloat

### Threshold Summary

- Forget if $\text{score} < \tau_{\text{forget}}$ (default 0.05)
- Promote if $\text{score} \ge \tau_{\text{promote}}$ (default 0.65)
- Or promote if $n_{\text{use}}\ge 5$ within 14 days (usage-based)
- User can override by touching memory

**Example:**

For a memory with $n_{\text{use}}=1$, $s=1.0$, $\beta=0.6$, $\lambda=2.673 \times 10^{-6}$ (3-day half-life), and $\Delta t = 30$ days:

$$
\begin{align*}
\text{score} &= (1)^{0.6} \cdot e^{-2.673 \times 10^{-6} \cdot 2{,}592{,}000} \cdot 1.0 \\
&= 1.0 \cdot e^{-6.93} \cdot 1.0 \\
&= 0.001
\end{align*}
$$

Since $0.001 < 0.05$ → **FORGET**

### Promote Threshold: $\tau_{\text{promote}} = 0.65$

**Purpose:** Move high-value memories to long-term storage (LTM).

**Dual Criteria (OR logic):**
1. **Score-based:** $\text{score} \geq 0.65$
2. **Usage-based:** $n_{\text{use}} \geq 5$ within 14 days

**Rationale:**
- Score-based: Catches quickly-important info (e.g., high strength + recent)
- Usage-based: Catches frequently referenced info (even if not recent)

**Example Scenario 1:** High score (strong memory, recently used)

$$
\begin{align*}
n_{\text{use}} &= 3 \\
\Delta t &= 1 \text{ hour} = 3600 \text{ seconds} \\
s &= 2.0 \\
\\
\text{score} &= (3)^{0.6} \cdot e^{-2.673 \times 10^{-6} \cdot 3600} \cdot 2.0 \\
&= 1.93 \cdot 0.99 \cdot 2.0 \\
&= 3.82
\end{align*}
$$

Since $3.82 > 0.65$ → **PROMOTE**

**Example Scenario 2:** High use count (frequently accessed)

- $n_{\text{use}} = 5$
- $\Delta t = 7$ days
- Memory created 10 days ago

Within 14-day window **AND** $n_{\text{use}} \geq 5$ → **PROMOTE**

## Complete Decision Logic

```python
from enum import Enum

class MemoryAction(Enum):
    KEEP = "keep"        # Normal retention
    FORGET = "forget"    # Delete from STM
    PROMOTE = "promote"  # Move to LTM

def decide_action(memory, now):
    """Determine action for a memory."""
    # Calculate current score
    time_delta = now - memory.last_used
    score = (
        math.pow(memory.use_count, β) *
        math.exp(-λ * time_delta) *
        memory.strength
    )

    # Check promotion criteria
    if score >= τ_promote:
        return MemoryAction.PROMOTE, "High score"

    age_days = (now - memory.created_at) / 86400
    if memory.use_count >= 5 and age_days <= 14:
        return MemoryAction.PROMOTE, "Frequently used"

    # Check forget criteria
    if score < τ_forget:
        return MemoryAction.FORGET, "Low score"

    # Default: keep in STM
    return MemoryAction.KEEP, f"Score: {score:.3f}"
```

## Parameter Interactions

### High $\beta$ + Short Half-Life

$$
\beta = 0.8, \quad \lambda = 8.02 \times 10^{-6} \text{ (1-day half-life)}
$$

**Effect:** Strongly favor frequently used, recent memories. Aggressive forgetting.
**Use Case:** High-velocity environments, rapid context switching.

### Low $\beta$ + Long Half-Life

$$
\beta = 0.3, \quad \lambda = 5.73 \times 10^{-7} \text{ (14-day half-life)}
$$

**Effect:** Gentle decay, less emphasis on use count. Longer retention.
**Use Case:** Slow-paced projects, archival needs.

### High Strength + Normal Decay

$$
s = 2.0, \quad \beta = 0.6, \quad \lambda = 2.67 \times 10^{-6} \text{ (3-day half-life)}
$$

**Effect:** Important memories resist decay longer.
**Use Case:** Critical information (credentials, decisions) in normal workflow.

## Worked Examples

### Example A: Low-use, recent, normal strength

Given: $n_{\text{use}}=1$, $\beta=0.6$, $\lambda=2.673\times10^{-6}$ (3-day), $\Delta t=6$ hours, $s=1.0$.

1) Use factor: $(1)^{0.6}=1.00$  
2) Decay: $e^{-2.673\times10^{-6}\cdot 21600} = e^{-0.0578}=0.9439$  
3) Strength: $1.0$  
Score: $1.00\times 0.9439\times 1.0=0.944$ → Keep (between thresholds)

### Example B: Frequent-use, mildly stale, normal strength

Given: $n_{\text{use}}=6$, $\beta=0.6$, $\lambda=2.673\times10^{-6}$ (3-day), $\Delta t=2$ days, $s=1.0$.

1) Use factor: $(6)^{0.6}\approx 2.93$  
2) Decay: $e^{-2.673\times10^{-6}\cdot 172800} = e^{-0.462} = 0.629$  
3) Strength: $1.0$  
Score: $2.93\times 0.629 \approx 1.84$ → $\ge 0.65$ ⇒ Promote (score-based)

### Example C: High strength, older, modest use

Given: $n_{\text{use}}=3$, $\beta=0.6$, $\lambda=2.673\times10^{-6}$ (3-day), $\Delta t=5$ days, $s=1.5$.

1) Use factor: $(3)^{0.6}\approx 1.93$  
2) Decay: $e^{-2.673\times10^{-6}\cdot 432000} = e^{-1.156} = 0.315$  
3) Strength: $1.5$  
Score: $1.93\times 0.315 \times 1.5 \approx 0.91$ → $\ge 0.65$ ⇒ Promote (score-based)

### Example D: Rarely used, very old

Given: $n_{\text{use}}=1$, $\beta=0.6$, $\lambda=2.673\times10^{-6}$ (3-day), $\Delta t=21$ days, $s=1.0$.

1) Use factor: $1.00$  
2) Decay: $e^{-2.673\times10^{-6}\cdot 1,814,400} = e^{-4.85} = 0.0078$  
3) Strength: $1.0$  
Score: $\approx 0.0078$ → $< 0.05$ ⇒ Forget

## Visualizations

### Decay Curves ($n_{\text{use}}=1$, $s=1.0$)

```
Score
1.0 |●
    |  ●
0.8 |    ●
    |      ●
0.6 |        ●
    |          ●●
0.4 |             ●●
    |                ●●●
0.2 |                   ●●●●
    |                       ●●●●●●●
0.0 |_________________________________●●●●●●●●●●●●●●
    0   1   2   3   4   5   6   7   8   9   10  11  12  13  14 days

Legend:
● = score at each day
Horizontal line at 0.65 = promotion threshold
Horizontal line at 0.05 = forget threshold
```

### Use Count Impact ($\Delta t=1$ day, $s=1.0$, $\beta=0.6$)

```
Score
4.0 |                                              ●
    |                                          ●
3.0 |                                      ●
    |                                  ●
2.0 |                              ●
    |                          ●
1.0 |●    ●    ●    ●    ●
    |_______________________________________________
    0    5    10   15   20   use_count
```

### Strength Modulation ($n_{\text{use}}=1$, $\Delta t=1$ day)

```
Score
2.0 |                          ●  (s=2.0)
    |                     ●       (s=1.5)
1.0 |●                           (s=1.0)
    |  ●                         (s=0.5)
0.0 |_________________________________
```

## Tuning for Different Use Cases

### Personal Assistant (Balanced)
```env
CORTEXGRAPH_DECAY_LAMBDA=2.673e-6  # 3-day half-life
CORTEXGRAPH_DECAY_BETA=0.6
CORTEXGRAPH_FORGET_THRESHOLD=0.05
CORTEXGRAPH_PROMOTE_THRESHOLD=0.65
```

### Development Environment (Aggressive)
```env
CORTEXGRAPH_DECAY_LAMBDA=8.02e-6   # 1-day half-life
CORTEXGRAPH_DECAY_BETA=0.8
CORTEXGRAPH_FORGET_THRESHOLD=0.10
CORTEXGRAPH_PROMOTE_THRESHOLD=0.70
```

### Research / Archival (Conservative)
```env
CORTEXGRAPH_DECAY_LAMBDA=5.73e-7   # 14-day half-life
CORTEXGRAPH_DECAY_BETA=0.4
CORTEXGRAPH_FORGET_THRESHOLD=0.03
CORTEXGRAPH_PROMOTE_THRESHOLD=0.50
```

### Meeting Notes (High Velocity)
```env
CORTEXGRAPH_DECAY_LAMBDA=1.60e-5   # 12-hour half-life
CORTEXGRAPH_DECAY_BETA=0.9
CORTEXGRAPH_FORGET_THRESHOLD=0.15
CORTEXGRAPH_PROMOTE_THRESHOLD=0.75
```

## Implementation Notes

### Precision

Use floating-point for all calculations:
```python
# Good
time_delta = float(now - last_used)
score = math.pow(use_count, beta) * math.exp(-lambda_ * time_delta) * strength

# Bad (integer overflow risk)
time_delta = now - last_used  # int
score = use_count ** beta * math.exp(-lambda_ * time_delta) * strength
```

### Caching

Scores change over time. Either:
1. Calculate on-demand (accurate but slower)
2. Cache with TTL (faster but approximate)

STM uses on-demand calculation for accuracy.

### Batch Operations

For garbage collection, calculate scores in batch:
```python
now = int(time.time())
memories_to_delete = []

for memory in all_memories:
    score = calculate_score(memory, now)
    if score < forget_threshold:
        memories_to_delete.append(memory.id)

# Delete in batch
delete_memories(memories_to_delete)
```

## Comparison to Other Approaches

### vs. Fixed TTL (e.g., Redis)

**Redis-style:**
$$
\text{if } (t_{\text{now}} - t_{\text{created}}) > \text{TTL} \implies \text{delete}
$$

**STM-style:**
$$
\text{if } \text{score}(t) < \tau_{\text{forget}} \implies \text{delete}
$$

**Advantage:** STM rewards frequent use. Redis deletes unconditionally.

### vs. LRU (Least Recently Used)

**LRU:**
$$
\text{if cache full} \implies \text{evict(least recently used)}
$$

**STM:**
$$
\text{if } \text{score}(t) < \tau_{\text{forget}} \implies \text{forget}
$$

**Advantage:** STM uses exponential decay + use count. LRU only tracks recency.

### vs. Linear Decay

**Linear decay:**
$$
\text{score} = \max\left(0, 1.0 - \frac{t_{\text{age}}}{t_{\text{max}}}\right)
$$

**STM exponential decay:**
$$
\text{score} = e^{-\lambda \cdot \Delta t}
$$

**Advantage:** Exponential matches Ebbinghaus curve (human forgetting).

## Future Enhancements

### Adaptive Decay

Adjust $\lambda$ based on memory category:

$$
\lambda_{\text{effective}} = \begin{cases}
0.5 \cdot \lambda_{\text{base}} & \text{if category = "credentials"} \\
2.0 \cdot \lambda_{\text{base}} & \text{if category = "ephemeral"} \\
\lambda_{\text{base}} & \text{otherwise}
\end{cases}
$$

### Spaced Repetition

For stable memories with high use counts:

$$
t_{\text{next review}} = t_{\text{now}} + \Delta t_{\text{interval}}
$$

Where $\Delta t_{\text{interval}}$ increases with each successful review.

### Context-Aware Strength

Boost strength based on conversation context:

$$
s = \begin{cases}
2.0 & \text{if is security critical(content)} \\
1.5 & \text{if is decision(content)} \\
1.3 & \text{if is preference(content)} \\
1.0 & \text{otherwise}
\end{cases}
$$

---

**Note:** The combination of exponential decay, sub-linear use count, and strength modulation creates memory dynamics that closely mimic human cognition. These parameters can be tuned for different use cases and workflows.
