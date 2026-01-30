"""Common search utilities shared between search tools.

This module consolidates shared validation and parameter handling
for STM and unified search operations to eliminate duplication.
"""

from dataclasses import dataclass

from ..config import get_config
from ..security.validators import (
    MAX_CONTENT_LENGTH,
    MAX_TAGS_COUNT,
    validate_list_length,
    validate_positive_int,
    validate_score,
    validate_status,
    validate_string_length,
    validate_tag,
)
from ..storage.models import MemoryStatus


@dataclass
class SearchParams:
    """Consolidated search parameters after validation."""

    query: str | None
    tags: list[str] | None
    status: list[MemoryStatus] | MemoryStatus
    limit: int
    window_days: int | None
    min_score: float | None
    preview_length: int
    page: int | None
    page_size: int | None
    use_embeddings: bool = False


def validate_search_params(
    query: str | None = None,
    tags: list[str] | None = None,
    status: str | list[str] | None = None,
    limit: int = 10,
    window_days: int | None = None,
    min_score: float | None = None,
    preview_length: int | None = None,
    page: int | None = None,
    page_size: int | None = None,
    use_embeddings: bool = False,
) -> SearchParams:
    """Validate and normalize search parameters.

    Consolidates validation logic shared between search.py and search_unified.py
    to eliminate duplication.

    Args:
        query: Search text (max 50k chars).
        tags: Filter by tags (max 50).
        status: Filter by status ('active', 'promoted', 'archived' or list of these).
                Defaults to ['active', 'promoted'] if None.
        limit: Max results (1-100).
        window_days: Recent memories only (1-3650 days).
        min_score: Min decay score (0.0-1.0).
        preview_length: Content chars (0-5000, default: from config).
        page: Page number (default: 1).
        page_size: Results per page (10-100, default: 10).
        use_embeddings: Enable semantic search.

    Returns:
        SearchParams with validated and normalized values.

    Raises:
        ValueError: Invalid parameters.
    """
    # Input validation
    if query is not None:
        query = validate_string_length(query, MAX_CONTENT_LENGTH, "query", allow_none=True)

    if tags is not None:
        tags = validate_list_length(tags, MAX_TAGS_COUNT, "tags")
        tags = [validate_tag(tag, f"tags[{i}]") for i, tag in enumerate(tags)]

    # Validate status
    search_status: list[MemoryStatus] | MemoryStatus
    if status is None:
        search_status = [MemoryStatus.ACTIVE, MemoryStatus.PROMOTED]
    elif isinstance(status, list):
        status = validate_list_length(status, 5, "status")
        search_status = [
            MemoryStatus(validate_status(s, f"status[{i}]")) for i, s in enumerate(status)
        ]
    else:
        search_status = MemoryStatus(validate_status(status, "status"))

    limit = validate_positive_int(limit, "limit", min_value=1, max_value=100)

    if window_days is not None:
        window_days = validate_positive_int(
            window_days,
            "window_days",
            min_value=1,
            max_value=3650,  # Max 10 years
        )

    if min_score is not None:
        min_score = validate_score(min_score, "min_score")

    # Validate preview_length
    if preview_length is not None:
        preview_length = validate_positive_int(
            preview_length, "preview_length", min_value=0, max_value=5000
        )
    else:
        # Use config default if not specified
        config = get_config()
        preview_length = config.search_default_preview_length

    return SearchParams(
        query=query,
        tags=tags,
        status=search_status,
        limit=limit,
        window_days=window_days,
        min_score=min_score,
        preview_length=preview_length,
        page=page,
        page_size=page_size,
        use_embeddings=use_embeddings,
    )


def is_pagination_requested(page: int | None, page_size: int | None) -> bool:
    """Check if pagination was explicitly requested.

    Args:
        page: Page number (None = not requested).
        page_size: Results per page (None = not requested).

    Returns:
        True if either page or page_size was provided.
    """
    return page is not None or page_size is not None
