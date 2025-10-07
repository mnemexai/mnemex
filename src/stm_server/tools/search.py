"""Search memory tool."""

import time
from typing import Any

from mcp.server import Server

from ..config import get_config
from ..core.decay import calculate_score
from ..storage.jsonl_storage import JSONLStorage
from ..storage.models import MemoryStatus, SearchResult


def _calculate_semantic_similarity(query_embed: list[float], memory_embed: list[float]) -> float:
    """Calculate cosine similarity between query and memory embeddings."""
    from ..core.clustering import cosine_similarity

    return cosine_similarity(query_embed, memory_embed)


def _generate_query_embedding(query: str) -> list[float] | None:
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


async def search_memory_handler(db: JSONLStorage, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Handle search memory requests.

    Args:
        db: Database instance
        arguments: Tool arguments

    Returns:
        Response dictionary
    """
    query = arguments.get("query")
    tags = arguments.get("tags")
    top_k = arguments.get("top_k", 10)
    window_days = arguments.get("window_days")
    min_score = arguments.get("min_score")
    use_embeddings = arguments.get("use_embeddings", False)

    config = get_config()
    now = int(time.time())

    # Get candidate memories from database
    memories = db.search_memories(
        tags=tags,
        status=MemoryStatus.ACTIVE,
        window_days=window_days,
        limit=top_k * 3,  # Get more candidates for scoring/filtering
    )

    # Generate query embedding if needed
    query_embed = None
    if use_embeddings and query and config.enable_embeddings:
        query_embed = _generate_query_embedding(query)

    # Score and filter memories
    results: list[SearchResult] = []

    for memory in memories:
        # Calculate decay score
        score = calculate_score(
            use_count=memory.use_count,
            last_used=memory.last_used,
            strength=memory.strength,
            now=now,
        )

        # Apply minimum score filter
        if min_score is not None and score < min_score:
            continue

        # Calculate semantic similarity if using embeddings
        similarity = None
        if query_embed and memory.embed:
            similarity = _calculate_semantic_similarity(query_embed, memory.embed)

        # Simple text matching if query provided and not using embeddings
        relevance = 1.0
        if query and not use_embeddings:
            query_lower = query.lower()
            content_lower = memory.content.lower()
            if query_lower in content_lower:
                relevance = 2.0  # Boost exact matches
            elif any(word in content_lower for word in query_lower.split()):
                relevance = 1.5  # Boost partial matches

        # Combine scores (semantic similarity takes precedence if available)
        final_score = score * relevance
        if similarity is not None:
            final_score = score * similarity

        results.append(SearchResult(memory=memory, score=final_score, similarity=similarity))

    # Sort by final score descending
    results.sort(key=lambda r: r.score, reverse=True)

    # Limit to top_k
    results = results[:top_k]

    # Format response
    response = {
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

    return response


def register(server: Server, db: JSONLStorage) -> None:
    """Register the search memory tool with the MCP server."""

    @server.call_tool()
    async def search_memory(arguments: dict[str, Any]) -> list[Any]:
        """
        Search for memories with optional filters and scoring.

        Args:
            query: Text query to search for (optional)
            tags: Filter by tags (optional)
            top_k: Maximum number of results (default: 10)
            window_days: Only search memories from last N days (optional)
            min_score: Minimum decay score threshold (optional)
            use_embeddings: Use semantic search with embeddings (default: false)

        Returns:
            List of matching memories with scores
        """
        result = await search_memory_handler(db, arguments)
        return [{"type": "text", "text": str(result)}]

    # Register tool metadata (this would normally be part of the server's tool list)
