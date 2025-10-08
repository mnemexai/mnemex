"""Search memory tool."""

import time
from typing import Any, List, Optional

from ..config import get_config
from ..context import db, mcp
from ..core.clustering import cosine_similarity
from ..core.decay import calculate_score
from ..storage.models import MemoryStatus, SearchResult


def _generate_query_embedding(query: str) -> Optional[List[float]]:
    """Generate embedding for search query."""
    config = get_config()
    if not config.enable_embeddings:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(config.embed_model)
        embedding = model.encode(query, convert_to_numpy=True)
        return embedding.tolist()
    except (ImportError, Exception):
        return None


@mcp.tool()
def search_memory(
    query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    top_k: int = 10,
    window_days: Optional[int] = None,
    min_score: Optional[float] = None,
    use_embeddings: bool = False,
) -> dict[str, Any]:
    """
    Search for memories with optional filters and scoring.

    Args:
        query: Text query to search for.
        tags: Filter by tags.
        top_k: Maximum number of results.
        window_days: Only search memories from last N days.
        min_score: Minimum decay score threshold.
        use_embeddings: Use semantic search with embeddings.

    Returns:
        List of matching memories with scores.
    """
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
    results = results[:top_k]

    return {
        "success": True,
        "count": len(results),
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
            }
            for r in results
        ],
    }
