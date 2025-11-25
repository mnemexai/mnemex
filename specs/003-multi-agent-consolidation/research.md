# Research: Multi-Agent Memory Consolidation

**Phase**: 0 (Research) | **Date**: 2025-11-24

## Research Tasks

### 1. Beads Integration Patterns

**Question**: How should Python code interact with beads for issue creation and querying?

**Decision**: Use subprocess calls to `bd` CLI with `--json` flag for structured output

**Rationale**:
- Beads is designed as a CLI tool, not a Python library
- `--json` flag provides structured output for parsing
- Subprocess approach avoids importing beads internals
- Consistent with how other tools (git, gh) are integrated

**Alternatives Considered**:
- Direct SQLite access: Rejected - bypasses beads business logic, fragile
- Python bindings: Don't exist, would need to create/maintain
- REST API: Beads doesn't expose one

**Implementation Pattern**:
```python
import subprocess
import json

def create_beads_issue(title: str, notes: dict, labels: list[str]) -> str:
    """Create a beads issue and return its ID."""
    result = subprocess.run(
        ["bd", "create",
         "--title", title,
         "--notes", json.dumps(notes),
         "--labels", ",".join(labels),
         "--json"],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)["id"]

def query_beads_issues(labels: list[str]) -> list[dict]:
    """Query beads issues by label."""
    result = subprocess.run(
        ["bd", "list", "--labels", ",".join(labels), "--json"],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)["result"]
```

---

### 2. Agent Base Class Design

**Question**: What interface should ConsolidationAgent provide?

**Decision**: Abstract base class with `run()`, `dry_run()`, `process_item()` methods

**Rationale**:
- Consistent interface across all five agents
- Dry-run mode is a spec requirement (FR-010)
- `process_item()` enables rate limiting at item level
- Abstract base enforces implementation

**Alternatives Considered**:
- Protocol/interface only: Less enforcement, easier to miss methods
- Composition over inheritance: More complex for simple use case
- No base class: Code duplication, inconsistent behavior

**Interface Design**:
```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class ConsolidationAgent(ABC, Generic[T]):
    """Base class for all consolidation agents."""

    def __init__(self, dry_run: bool = False, rate_limit: int = 100):
        self.dry_run = dry_run
        self.rate_limit = rate_limit
        self._processed_count = 0

    @abstractmethod
    def scan(self) -> list[str]:
        """Scan for items needing processing. Returns memory IDs."""
        ...

    @abstractmethod
    def process_item(self, memory_id: str) -> T:
        """Process a single item. Returns result model."""
        ...

    def run(self) -> list[T]:
        """Run agent on all scanned items."""
        items = self.scan()
        results = []
        for item_id in items:
            if self._processed_count >= self.rate_limit:
                break
            result = self.process_item(item_id)
            self._log_to_beads(item_id, result)
            results.append(result)
            self._processed_count += 1
        return results
```

---

### 3. Existing Core Module Integration

**Question**: How should agents call existing `core/` functions?

**Decision**: Direct Python imports from `cortexgraph.core`

**Rationale**:
- Existing modules are well-tested (100% coverage on consolidation.py)
- Direct imports are fastest, no overhead
- Type hints preserved across call boundaries
- Matches existing pattern (tools import from core)

**Integration Points**:

| Agent | Core Module | Functions Used |
|-------|-------------|----------------|
| Decay Analyzer | `core.decay` | `calculate_score()`, `is_in_danger_zone()` |
| Decay Analyzer | `core.review` | `get_review_priority()` |
| Cluster Detector | `core.clustering` | `find_similar_memories()`, `calculate_cohesion()` |
| Semantic Merge | `core.consolidation` | `merge_memories()`, `create_consolidated_content()` |
| LTM Promoter | `core.scoring` | `should_promote()` |
| LTM Promoter | `vault.writer` | `write_markdown()` |
| Relationship Discovery | `core.clustering` | `calculate_similarity()` |

---

### 4. Hybrid Triggering Implementation

**Question**: How should scheduled vs event-driven triggers work?

**Decision**: Scheduler class with cron-like intervals + hook into `save_memory` for urgent checks

**Rationale**:
- Scheduled: Simple cron-like execution (hourly default)
- Event-driven: Check decay score after `save_memory`, trigger if < 0.10
- Separation of concerns: Scheduler handles timing, agents handle logic

**Alternatives Considered**:
- Pure scheduled: Misses urgent decay situations
- Pure event-driven: Complex hooks into every operation
- Background daemon: Overkill for local CLI tool

**Implementation Approach**:
```python
# Scheduled (via cron or launchd)
# crontab: 0 * * * * cortexgraph-consolidate run --all

# Event trigger (hook after save_memory)
def post_save_check(memory_id: str) -> None:
    """Check if newly saved memory needs urgent attention."""
    score = calculate_score(memory_id)
    if score < 0.10:
        create_urgent_beads_issue(memory_id, score)
```

---

### 5. Confidence-Based Processing

**Question**: How should confidence thresholds affect processing flow?

**Decision**: Three-tier system with configurable thresholds

**Rationale**:
- Matches clarification decision (≥0.9 auto, 0.7-0.9 log, <0.7 wait)
- Aligns with existing `consolidate_memories` pattern (cohesion > 0.75)
- Configurable via environment variables

**Implementation**:
```python
from enum import Enum

class ProcessingDecision(Enum):
    AUTO = "auto"        # confidence >= 0.9
    LOG_ONLY = "log"     # 0.7 <= confidence < 0.9
    WAIT_HUMAN = "wait"  # confidence < 0.7

def decide_processing(confidence: float) -> ProcessingDecision:
    if confidence >= 0.9:
        return ProcessingDecision.AUTO
    elif confidence >= 0.7:
        return ProcessingDecision.LOG_ONLY
    else:
        return ProcessingDecision.WAIT_HUMAN
```

---

### 6. Rate Limiting Strategy

**Question**: How should 100 ops/minute rate limit be enforced?

**Decision**: Token bucket algorithm with per-agent limits

**Rationale**:
- Simple, well-understood algorithm
- Per-agent allows parallelism while preventing storms
- Configurable via `CORTEXGRAPH_AGENT_RATE_LIMIT`

**Implementation**:
```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_ops: int = 100, window_seconds: int = 60):
        self.max_ops = max_ops
        self.window = window_seconds
        self.timestamps: deque[float] = deque()

    def acquire(self) -> bool:
        """Try to acquire a token. Returns True if allowed."""
        now = time.time()
        # Remove old timestamps
        while self.timestamps and self.timestamps[0] < now - self.window:
            self.timestamps.popleft()

        if len(self.timestamps) < self.max_ops:
            self.timestamps.append(now)
            return True
        return False

    def wait_and_acquire(self) -> None:
        """Block until a token is available."""
        while not self.acquire():
            time.sleep(0.1)
```

---

## Summary of Decisions

| Topic | Decision | Risk Level |
|-------|----------|------------|
| Beads integration | Subprocess `bd` CLI calls | Low |
| Agent base class | ABC with Generic result types | Low |
| Core integration | Direct Python imports | Low |
| Triggering | Hybrid (scheduled + event hooks) | Medium |
| Confidence handling | Three-tier thresholds | Low |
| Rate limiting | Token bucket per agent | Low |

**All NEEDS CLARIFICATION items resolved.** Ready for Phase 1 design.
