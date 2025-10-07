"""Unified search across STM and LTM.

Search both short-term memory (JSONL storage) and long-term memory (Obsidian vault)
with temporal ranking and result merging.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import get_config
from ..core.decay import calculate_score
from ..storage.jsonl_storage import JSONLStorage
from ..storage.ltm_index import LTMIndex
from ..storage.models import Memory, SearchResult


class UnifiedSearchResult:
    """Result from unified search across STM and LTM."""

    def __init__(
        self,
        content: str,
        title: str,
        source: str,  # "stm" or "ltm"
        score: float,
        path: Optional[str] = None,
        memory_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[int] = None,
        last_used: Optional[int] = None,
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

    def to_dict(self) -> Dict[str, Any]:
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


def search_unified(
    query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 10,
    *,
    stm_weight: float = 1.0,
    ltm_weight: float = 0.7,
    window_days: Optional[int] = None,
    min_score: Optional[float] = None,
) -> List[UnifiedSearchResult]:
    """
    Search across both STM and LTM with unified ranking.

    Args:
        query: Text query to search for
        tags: Filter by tags
        limit: Maximum total results
        stm_weight: Weight multiplier for STM results (default: 1.0)
        ltm_weight: Weight multiplier for LTM results (default: 0.7)
        window_days: Only include STM memories from last N days
        min_score: Minimum score threshold for STM memories

    Returns:
        List of UnifiedSearchResult objects, sorted by weighted score

    Strategy:
        - Query STM (recent context, temporal decay scores)
        - Query LTM index (permanent knowledge base)
        - Apply weights based on source
        - Merge and deduplicate results
        - Sort by combined score
    """
    config = get_config()
    results: List[UnifiedSearchResult] = []

    # Search STM
    try:
        storage = JSONLStorage()
        storage.connect()

        stm_memories = storage.search_memories(
            tags=tags,
            window_days=window_days,
            limit=limit * 2,  # Get more candidates for merging
        )

        # Apply text query filter if provided
        if query:
            query_lower = query.lower()
            stm_memories = [
                m for m in stm_memories
                if query_lower in m.content.lower()
            ]

        # Convert to unified results with decay scores
        now = int(time.time())
        for memory in stm_memories:
            score = calculate_score(
                use_count=memory.use_count,
                last_used=memory.last_used,
                strength=memory.strength,
                now=now,
            )

            # Apply minimum score filter
            if min_score is not None and score < min_score:
                continue

            # Apply STM weight
            weighted_score = score * stm_weight

            results.append(UnifiedSearchResult(
                content=memory.content,
                title=f"Memory {memory.id[:8]}",
                source="stm",
                score=weighted_score,
                memory_id=memory.id,
                tags=memory.meta.tags,
                created_at=memory.created_at,
                last_used=memory.last_used,
            ))

        storage.close()

    except Exception as e:
        print(f"Warning: STM search failed: {e}")

    # Search LTM
    try:
        # Check if vault path is configured
        vault_path = getattr(config, 'ltm_vault_path', None)
        if vault_path:
            vault_path = Path(vault_path).expanduser()

            if vault_path.exists():
                # Load LTM index
                ltm_index = LTMIndex(vault_path=vault_path)

                # Try to load existing index
                if ltm_index.index_path.exists():
                    ltm_index.load_index()
                else:
                    # Build index if it doesn't exist
                    ltm_index.build_index(verbose=False)

                # Search LTM
                ltm_docs = ltm_index.search(query=query, tags=tags, limit=limit * 2)

                # Convert to unified results
                for doc in ltm_docs:
                    # Simple relevance score based on query match
                    if query:
                        query_lower = query.lower()
                        title_match = 2.0 if query_lower in doc.title.lower() else 0.0
                        content_match = 1.0 if query_lower in doc.content.lower() else 0.0
                        relevance_score = min(1.0, (title_match + content_match) / 3.0)
                    else:
                        relevance_score = 0.5  # Default relevance for tag-only search

                    # Apply LTM weight
                    weighted_score = relevance_score * ltm_weight

                    results.append(UnifiedSearchResult(
                        content=doc.content[:500],  # Truncate long content
                        title=doc.title,
                        source="ltm",
                        score=weighted_score,
                        path=doc.path,
                        tags=doc.tags,
                    ))

    except Exception as e:
        print(f"Warning: LTM search failed: {e}")

    # Sort by weighted score (descending)
    results.sort(key=lambda r: r.score, reverse=True)

    # Deduplicate based on content similarity (simple approach: exact match)
    seen_content = set()
    deduplicated = []

    for result in results:
        # Use first 100 chars as dedup key
        dedup_key = result.content[:100].lower().strip()

        if dedup_key not in seen_content:
            seen_content.add(dedup_key)
            deduplicated.append(result)

            if len(deduplicated) >= limit:
                break

    return deduplicated


def format_results(results: List[UnifiedSearchResult], *, verbose: bool = False) -> str:
    """
    Format unified search results for display.

    Args:
        results: List of search results
        verbose: If True, include full metadata

    Returns:
        Formatted string
    """
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

        # Show content preview
        preview = result.content[:150]
        if len(result.content) > 150:
            preview += "..."
        lines.append(f"   {preview}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    """CLI entry point for unified search."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Search across STM and LTM")
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query",
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Filter by tags",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum results",
    )
    parser.add_argument(
        "--stm-weight",
        type=float,
        default=1.0,
        help="Weight for STM results",
    )
    parser.add_argument(
        "--ltm-weight",
        type=float,
        default=0.7,
        help="Weight for LTM results",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        help="Only search STM memories from last N days",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        help="Minimum score for STM results",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed metadata",
    )

    args = parser.parse_args()

    if not args.query and not args.tags:
        parser.print_help()
        return 1

    try:
        results = search_unified(
            query=args.query,
            tags=args.tags,
            limit=args.limit,
            stm_weight=args.stm_weight,
            ltm_weight=args.ltm_weight,
            window_days=args.window_days,
            min_score=args.min_score,
        )

        output = format_results(results, verbose=args.verbose)
        print(output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
