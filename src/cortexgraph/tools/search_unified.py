"""Unified search across STM and LTM."""

import time
from typing import Any

from ..config import get_config
from ..context import db, mcp
from ..core.decay import calculate_score
from ..core.pagination import paginate_list, validate_pagination_params
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
from ..storage.ltm_index import LTMIndex


class UnifiedSearchResult:
    """Result from unified search across STM and LTM."""

    def __init__(
        self,
        content: str,
        title: str,
        source: str,  # "stm" or "ltm"
        score: float,
        path: str | None = None,
        memory_id: str | None = None,
        tags: list[str] | None = None,
        created_at: int | None = None,
        last_used: int | None = None,
    ):
        self.content = content
        self.title = title
        self.source = source
        self.score = score
        self.path = path
        self.memory_id = memory_id
        self.tags = tags or []
        self.created_at = created_at
        self.last_used = last_used

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "title": self.title,
            "source": self.source,
            "score": self.score,
            "path": self.path,
            "memory_id": self.memory_id,
            "tags": self.tags,
            "created_at": self.created_at,
            "last_used": self.last_used,
        }


@mcp.tool()
@time_operation("search_unified")
def search_unified(
    query: str | None = None,
    tags: list[str] | None = None,
    limit: int = 10,
    stm_weight: float = 1.0,
    ltm_weight: float = 0.7,
    window_days: int | None = None,
    min_score: float | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    """
    Search across both STM and LTM with unified ranking.

    **Pagination:** Results are paginated to help you find specific memories across
    large result sets from both short-term and long-term memory. Use `page` and `page_size`
    to navigate through results. If a search term isn't found on the first page,
    increment `page` to see more results.

    Args:
        query: Text query to search for (max 50,000 chars).
        tags: Filter by tags (max 50 tags).
        limit: Maximum total results before pagination (1-100).
        stm_weight: Weight multiplier for STM results (0.0-2.0).
        ltm_weight: Weight multiplier for LTM results (0.0-2.0).
        window_days: Only include STM memories from last N days (1-3650).
        min_score: Minimum score threshold for STM memories (0.0-1.0).
        page: Page number to retrieve (1-indexed, default: 1).
        page_size: Number of memories per page (default: 10, max: 100).

    Returns:
        Dictionary with paginated results including:
        - results: List of matching memories from STM and LTM for current page
        - pagination: Metadata (page, page_size, total_count, total_pages, has_more)

    Examples:
        # Get first page (10 results)
        search_unified(query="architecture", page=1, page_size=10)

        # Get next page
        search_unified(query="architecture", page=2, page_size=10)

    Raises:
        ValueError: If any input fails validation.
    """
    # Input validation
    if query is not None:
        query = validate_string_length(query, MAX_CONTENT_LENGTH, "query", allow_none=True)

    if tags is not None:
        tags = validate_list_length(tags, MAX_TAGS_COUNT, "tags")
        tags = [validate_tag(tag, f"tags[{i}]") for i, tag in enumerate(tags)]

    limit = validate_positive_int(limit, "limit", min_value=1, max_value=100)

    # Weights can be higher than 1.0 to boost importance
    if not 0.0 <= stm_weight <= 2.0:
        raise ValueError(f"stm_weight must be between 0.0 and 2.0, got {stm_weight}")
    if not 0.0 <= ltm_weight <= 2.0:
        raise ValueError(f"ltm_weight must be between 0.0 and 2.0, got {ltm_weight}")

    if window_days is not None:
        window_days = validate_positive_int(window_days, "window_days", min_value=1, max_value=3650)

    if min_score is not None:
        min_score = validate_score(min_score, "min_score")

    # Only validate pagination if explicitly requested
    pagination_requested = page is not None or page_size is not None

    config = get_config()
    results: list[UnifiedSearchResult] = []

    # Search STM
    try:
        stm_memories = db.search_memories(tags=tags, window_days=window_days, limit=limit * 2)
        if query:
            stm_memories = [m for m in stm_memories if query.lower() in m.content.lower()]

        now = int(time.time())
        for memory in stm_memories:
            score = calculate_score(
                use_count=memory.use_count,
                last_used=memory.last_used,
                strength=memory.strength,
                now=now,
            )
            if min_score is not None and score < min_score:
                continue

            results.append(
                UnifiedSearchResult(
                    content=memory.content,
                    title=f"Memory {memory.id[:8]}",
                    source="stm",
                    score=score * stm_weight,
                    memory_id=memory.id,
                    tags=memory.meta.tags,
                    created_at=memory.created_at,
                    last_used=memory.last_used,
                )
            )
    except Exception as e:
        print(f"Warning: STM search failed: {e}")

    # Search LTM (lazy loading)
    try:
        if config.ltm_vault_path and config.ltm_vault_path.exists():
            ltm_index = LTMIndex(vault_path=config.ltm_vault_path)

            # Check if index exists and is fresh
            index_needs_rebuild = False
            if not ltm_index.index_path.exists():
                # No index exists, need to build it
                index_needs_rebuild = True
            else:
                # Check if index is stale (older than configured max age)
                index_age = time.time() - ltm_index.index_path.stat().st_mtime
                if index_age >= config.ltm_index_max_age_seconds:
                    index_needs_rebuild = True

            # Auto-rebuild stale or missing index
            if index_needs_rebuild:
                try:
                    ltm_index.build_index(force=False, verbose=False)  # Incremental rebuild
                except Exception as e:
                    print(f"Warning: Failed to rebuild LTM index: {e}")

            # Load and search index if it exists
            if ltm_index.index_path.exists():
                ltm_index.load_index()
                ltm_docs = ltm_index.search(query=query, tags=tags, limit=limit * 2)
                for doc in ltm_docs:
                    relevance_score = 0.5
                    if query:
                        title_match = 2.0 if query.lower() in doc.title.lower() else 0.0
                        content_match = 1.0 if query.lower() in doc.content.lower() else 0.0
                        relevance_score = min(1.0, (title_match + content_match) / 3.0)

                    results.append(
                        UnifiedSearchResult(
                            content=doc.content[:500],
                            title=doc.title,
                            source="ltm",
                            score=relevance_score * ltm_weight,
                            path=doc.path,
                            tags=doc.tags,
                        )
                    )
    except Exception as e:
        print(f"Warning: LTM search failed: {e}")

    results.sort(key=lambda r: r.score, reverse=True)

    seen_content = set()
    deduplicated: list[UnifiedSearchResult] = []
    for result in results:
        dedup_key = result.content[:100].lower().strip()
        if dedup_key not in seen_content:
            seen_content.add(dedup_key)
            deduplicated.append(result)
            if len(deduplicated) >= limit:
                break

    # Apply pagination only if requested
    if pagination_requested:
        # Validate and get non-None values
        valid_page, valid_page_size = validate_pagination_params(page, page_size)
        paginated = paginate_list(deduplicated, page=valid_page, page_size=valid_page_size)
        return {
            "success": True,
            "count": len(paginated.items),
            "results": [r.to_dict() for r in paginated.items],
            "pagination": paginated.to_dict(),
        }
    else:
        # No pagination - return all results
        return {
            "success": True,
            "count": len(deduplicated),
            "results": [r.to_dict() for r in deduplicated],
        }


def format_results(results: list[UnifiedSearchResult], *, verbose: bool = False) -> str:
    """Formats unified search results for display."""
    if not results:
        return "No results found."

    lines = [f"Found {len(results)} results:\n"]
    for i, result in enumerate(results, 1):
        source_label = "🧠 STM" if result.source == "stm" else "📚 LTM"
        lines.append(f"{i}. [{source_label}] {result.title} (score: {result.score:.3f})")
        if verbose:
            if result.tags:
                lines.append(f"   Tags: {', '.join(result.tags)}")
            if result.path:
                lines.append(f"   Path: {result.path}")
            if result.memory_id:
                lines.append(f"   ID: {result.memory_id}")
        preview = result.content[:150]
        if len(result.content) > 150:
            preview += "..."
        lines.append(f"   {preview}\n")
    return "\n".join(lines)


def main() -> int:
    """CLI entry point for unified search."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Search across STM and LTM")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--tags", nargs="+", help="Filter by tags")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results")
    parser.add_argument("--stm-weight", type=float, default=1.0, help="Weight for STM results")
    parser.add_argument("--ltm-weight", type=float, default=0.7, help="Weight for LTM results")
    parser.add_argument("--window-days", type=int, help="Only search STM memories from last N days")
    parser.add_argument("--min-score", type=float, help="Minimum score for STM results")
    parser.add_argument("--verbose", action="store_true", help="Show detailed metadata")

    args = parser.parse_args()
    if not args.query and not args.tags:
        parser.print_help()
        return 1

    try:
        # This is a simplified call for the CLI, so we pass a dict
        result_dict = search_unified(
            query=args.query,
            tags=args.tags,
            limit=args.limit,
            stm_weight=args.stm_weight,
            ltm_weight=args.ltm_weight,
            window_days=args.window_days,
            min_score=args.min_score,
        )
        # Reconstruct objects for formatting
        results_obj = [UnifiedSearchResult(**r) for r in result_dict["results"]]
        output = format_results(results_obj, verbose=args.verbose)
        print(output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
