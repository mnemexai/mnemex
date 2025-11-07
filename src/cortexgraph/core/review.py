"""Natural spaced repetition for memories.

This module implements natural reinforcement through conversation rather than
explicit quizzing. Memories due for review are blended into search results,
creating the "Maslow effect" - natural repetition across contexts.
"""

import time

from cortexgraph.config import get_config
from cortexgraph.core.decay import calculate_score
from cortexgraph.storage.models import Memory


def calculate_review_priority(memory: Memory) -> float:
    """Calculate review priority for a memory.

    Priority is based on the "danger zone" - memories that are fading but not
    yet forgotten. These benefit most from natural reinforcement.

    Args:
        memory: The memory to evaluate

    Returns:
        Priority score from 0.0 (not needed) to 1.0 (urgent)

    Algorithm:
        - Score < danger_zone_min (0.15): Too far gone, priority = 0.0
        - Score > danger_zone_max (0.35): Still fresh, priority = 0.0
        - Score in danger zone: Linear mapping to [0.0, 1.0]
        - Peak priority at midpoint of danger zone (score ~0.25)
    """
    config = get_config()
    score = calculate_score(
        use_count=memory.use_count,
        last_used=memory.last_used,
        strength=memory.strength,
    )

    danger_min = config.review_danger_zone_min
    danger_max = config.review_danger_zone_max

    # Outside danger zone
    if score < danger_min or score > danger_max:
        return 0.0

    # Map score to priority using inverted parabola
    # Peak priority at midpoint, tapering off at edges
    midpoint = (danger_min + danger_max) / 2
    range_half = (danger_max - danger_min) / 2

    # Normalize to [-1, 1] around midpoint
    normalized = (score - midpoint) / range_half

    # Inverted parabola: 1 - x^2
    priority = 1.0 - (normalized**2)

    return max(0.0, min(1.0, priority))


def get_memories_due_for_review(
    all_memories: list[Memory],
    min_priority: float = 0.3,
    limit: int = 50,
) -> list[Memory]:
    """Get memories that would benefit from natural reinforcement.

    Args:
        all_memories: All active memories to consider
        min_priority: Minimum priority threshold (default 0.3)
        limit: Maximum number to return

    Returns:
        List of memories sorted by priority (highest first)
    """
    # Calculate priority for each memory and filter
    candidates = []
    for mem in all_memories:
        priority = calculate_review_priority(mem)
        if priority >= min_priority:
            # Update the memory's review_priority field
            mem.review_priority = priority
            candidates.append(mem)

    # Sort by priority (highest first)
    candidates.sort(key=lambda m: m.review_priority, reverse=True)

    return candidates[:limit]


def blend_search_results(
    primary_results: list[Memory],
    review_candidates: list[Memory],
    blend_ratio: float = 0.3,
) -> list[Memory]:
    """Blend search results with review candidates.

    Creates natural spaced repetition by injecting memories due for review
    into search results when they're relevant.

    Args:
        primary_results: Main search results (by relevance)
        review_candidates: Memories due for review
        blend_ratio: Fraction of results that should be review candidates (0.0-1.0)

    Returns:
        Blended list maintaining roughly the target ratio

    Example:
        If top_k=10 and blend_ratio=0.3, return ~7 primary + ~3 review
    """
    if not review_candidates or blend_ratio <= 0:
        return primary_results

    total_slots = len(primary_results)
    review_slots = int(total_slots * blend_ratio)
    primary_slots = total_slots - review_slots

    # Interleave them for better distribution
    result = []
    primary_iter = iter(primary_results[:primary_slots])
    review_iter = iter(review_candidates[:review_slots])

    # Alternate between primary and review
    try:
        while True:
            # Add 2-3 primary results
            for _ in range(2):
                result.append(next(primary_iter))
            # Add 1 review candidate
            result.append(next(review_iter))
    except StopIteration:
        # Exhaust remaining
        result.extend(primary_iter)
        result.extend(review_iter)

    return result[:total_slots]


def reinforce_memory(memory: Memory, cross_domain: bool = False) -> Memory:
    """Reinforce a memory through natural usage.

    This is called when a memory is actually used in conversation, not just
    retrieved. Updates usage stats and potentially boosts strength.

    Args:
        memory: Memory to reinforce
        cross_domain: Whether this usage was in a different context than usual

    Returns:
        Updated memory with reinforcement applied
    """
    now = int(time.time())

    # Update basic usage stats
    memory.last_used = now
    memory.use_count += 1
    memory.last_review_at = now
    memory.review_count += 1

    # Cross-domain usage is particularly valuable
    if cross_domain:
        memory.cross_domain_count += 1
        # Small strength boost for cross-domain reinforcement (max 2.0)
        memory.strength = min(2.0, memory.strength + 0.05)

    # Reset review priority (will be recalculated next time)
    memory.review_priority = 0.0

    return memory


def detect_cross_domain_usage(
    memory: Memory,
    current_context_tags: list[str],
) -> bool:
    """Detect if memory is being used in a different context than usual.

    Cross-domain usage (like seeing "Maslow's hierarchy" in history, econ, and
    sociology classes) is particularly valuable for retention.

    Args:
        memory: The memory being used
        current_context_tags: Tags representing current conversation context

    Returns:
        True if this appears to be cross-domain usage
    """
    memory_tags = set(memory.meta.tags)
    context_tags = set(current_context_tags)

    # If no tags, can't determine
    if not memory_tags or not context_tags:
        return False

    # Calculate tag overlap
    overlap = len(memory_tags & context_tags)
    total = len(memory_tags | context_tags)

    if total == 0:
        return False

    jaccard_similarity = overlap / total

    # Low similarity = cross-domain usage
    # Threshold: <30% tag overlap
    return jaccard_similarity < 0.3
