"""Search memory tool."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, cast

from ..config import get_config
from ..context import db, mcp
from ..core.clustering import cosine_similarity
from ..core.decay import calculate_score
from ..core.pagination import paginate_list, validate_pagination_params
from ..core.review import blend_search_results, get_memories_due_for_review
from ..performance import time_operation
from ..security.validators import (
    MAX_CONTENT_LENGTH,
    MAX_TAGS_COUNT,
    validate_list_length,
    validate_positive_int,
    validate_score,
    validate_string_length,
    validate_tag,
)
from ..storage.models import MemoryStatus, SearchResult

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

# Optional dependency for embeddings
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Global model cache to avoid reloading on every request
_model_cache: dict[str, Any] = {}


def _get_embedding_model(model_name: str) -> SentenceTransformer | None:
    """Get cached embedding model or create new one."""
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None

    if model_name not in _model_cache:
        try:
            _model_cache[model_name] = SentenceTransformer(model_name)
        except Exception:
            return None

    return _model_cache[model_name]


def _generate_query_embedding(query: str) -> list[float] | None:
    """Generate embedding for search query."""
    config = get_config()
    if not config.enable_embeddings or not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None

    model = _get_embedding_model(config.embed_model)
    if model is None:
        return None

    try:
        embedding = model.encode(query, convert_to_numpy=True)
        return cast(list[float], embedding.tolist())
    except Exception:
        return None


@mcp.tool()
@time_operation("search_memory")
def search_memory(
    query: str | None = None,
    tags: list[str] | None = None,
    top_k: int = 10,
    window_days: int | None = None,
    min_score: float | None = None,
    use_embeddings: bool = False,
    include_review_candidates: bool = True,
    page: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    """
    Search for memories with optional filters and scoring.

    This tool implements natural spaced repetition by blending memories due
    for review into results when they're relevant. This creates the "Maslow
    effect" - natural reinforcement through conversation.

    **Pagination:** Results are paginated to help you find specific memories across
    large result sets. Use `page` and `page_size` to navigate through results.
    If a search term isn't found on the first page, increment `page` to see more results.

    Args:
        query: Text query to search for (max 50,000 chars).
        tags: Filter by tags (max 50 tags).
        top_k: Maximum number of results before pagination (1-100).
        window_days: Only search memories from last N days (1-3650).
        min_score: Minimum decay score threshold (0.0-1.0).
        use_embeddings: Use semantic search with embeddings.
        include_review_candidates: Blend in memories due for review (default True).
        page: Page number to retrieve (1-indexed, default: 1).
        page_size: Number of memories per page (default: 10, max: 100).

    Returns:
        Dictionary with paginated results including:
        - results: List of matching memories with scores for current page
        - pagination: Metadata (page, page_size, total_count, total_pages, has_more)

        Some results may be review candidates that benefit from reinforcement.

    Examples:
        # Get first page (10 results)
        search_memory(query="authentication", page=1, page_size=10)

        # Get next page
        search_memory(query="authentication", page=2, page_size=10)

        # Larger page size
        search_memory(query="authentication", page=1, page_size=25)

    Raises:
        ValueError: If any input fails validation.
    """
    # Input validation
    if query is not None:
        query = validate_string_length(query, MAX_CONTENT_LENGTH, "query", allow_none=True)

    if tags is not None:
        tags = validate_list_length(tags, MAX_TAGS_COUNT, "tags")
        tags = [validate_tag(tag, f"tags[{i}]") for i, tag in enumerate(tags)]

    top_k = validate_positive_int(top_k, "top_k", min_value=1, max_value=100)

    if window_days is not None:
        window_days = validate_positive_int(
            window_days,
            "window_days",
            min_value=1,
            max_value=3650,  # Max 10 years
        )

    if min_score is not None:
        min_score = validate_score(min_score, "min_score")

    # Only validate pagination if explicitly requested
    pagination_requested = page is not None or page_size is not None

    config = get_config()
    now = int(time.time())

    memories = db.search_memories(
        tags=tags,
        status=MemoryStatus.ACTIVE,
        window_days=window_days,
        limit=top_k * 3,
    )

    query_embed = None
    if use_embeddings and query and config.enable_embeddings:
        query_embed = _generate_query_embedding(query)

    results: list[SearchResult] = []
    for memory in memories:
        score = calculate_score(
            use_count=memory.use_count,
            last_used=memory.last_used,
            strength=memory.strength,
            now=now,
        )

        if min_score is not None and score < min_score:
            continue

        similarity = None
        if query_embed and memory.embed:
            similarity = cosine_similarity(query_embed, memory.embed)

        relevance = 1.0
        if query and not use_embeddings:
            if query.lower() in memory.content.lower():
                relevance = 2.0
            elif any(word in memory.content.lower() for word in query.lower().split()):
                relevance = 1.5

        final_score = score * relevance
        if similarity is not None:
            final_score = score * similarity

        results.append(SearchResult(memory=memory, score=final_score, similarity=similarity))

    results.sort(key=lambda r: r.score, reverse=True)

    # Natural spaced repetition: blend in review candidates
    final_memories = [r.memory for r in results[:top_k]]

    if include_review_candidates and query:
        # Get all active memories for review queue
        all_active = db.search_memories(status=MemoryStatus.ACTIVE, limit=10000)

        # Get memories due for review
        review_queue = get_memories_due_for_review(all_active, min_priority=0.3, limit=20)

        # Filter review candidates for relevance to query
        relevant_reviews = []
        for mem in review_queue:
            # Simple relevance check
            if query.lower() in mem.content.lower():
                relevant_reviews.append(mem)
            elif any(word in mem.content.lower() for word in query.lower().split()):
                relevant_reviews.append(mem)
            # Also check semantic similarity if available
            elif query_embed and mem.embed:
                sim = cosine_similarity(query_embed, mem.embed)
                if sim and sim > 0.6:  # Somewhat relevant
                    relevant_reviews.append(mem)

        # Blend primary results with review candidates
        if relevant_reviews:
            final_memories = blend_search_results(
                final_memories,
                relevant_reviews,
                blend_ratio=config.review_blend_ratio,
            )

    # Convert back to SearchResult format for final output
    final_results = []
    for mem in final_memories:
        # Find the original SearchResult if it exists
        original = next((r for r in results if r.memory.id == mem.id), None)
        if original:
            final_results.append(original)
        else:
            # It's a review candidate, calculate fresh score
            score = calculate_score(
                use_count=mem.use_count,
                last_used=mem.last_used,
                strength=mem.strength,
                now=now,
            )
            final_results.append(SearchResult(memory=mem, score=score, similarity=None))

    # Apply pagination only if requested
    if pagination_requested:
        # Validate and get non-None values
        valid_page, valid_page_size = validate_pagination_params(page, page_size)
        paginated = paginate_list(final_results, page=valid_page, page_size=valid_page_size)
        return {
            "success": True,
            "count": len(paginated.items),
            "results": [
                {
                    "id": r.memory.id,
                    "content": r.memory.content,
                    "tags": r.memory.meta.tags,
                    "score": round(r.score, 4),
                    "similarity": round(r.similarity, 4) if r.similarity else None,
                    "use_count": r.memory.use_count,
                    "last_used": r.memory.last_used,
                    "age_days": round((now - r.memory.created_at) / 86400, 1),
                    "review_priority": round(r.memory.review_priority, 4)
                    if r.memory.review_priority > 0
                    else None,
                }
                for r in paginated.items
            ],
            "pagination": paginated.to_dict(),
        }
    else:
        # No pagination - return all results
        return {
            "success": True,
            "count": len(final_results),
            "results": [
                {
                    "id": r.memory.id,
                    "content": r.memory.content,
                    "tags": r.memory.meta.tags,
                    "score": round(r.score, 4),
                    "similarity": round(r.similarity, 4) if r.similarity else None,
                    "use_count": r.memory.use_count,
                    "last_used": r.memory.last_used,
                    "age_days": round((now - r.memory.created_at) / 86400, 1),
                    "review_priority": round(r.memory.review_priority, 4)
                    if r.memory.review_priority > 0
                    else None,
                }
                for r in final_results
            ],
        }
