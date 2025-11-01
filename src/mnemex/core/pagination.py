"""Pagination utilities for memory search and retrieval operations.

This module provides shared pagination logic for tools that return lists of memories.
Supports standard pagination patterns with page numbers and page sizes.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from ..security.validators import validate_positive_int

# Default page size for all pagination operations
DEFAULT_PAGE_SIZE = 10

# Maximum page size to prevent DoS via oversized responses
MAX_PAGE_SIZE = 100

T = TypeVar("T")


class PaginatedResult(Generic[T]):
    """Container for paginated results with metadata."""

    def __init__(
        self,
        items: list[T],
        total_count: int,
        page: int,
        page_size: int,
    ):
        """Initialize paginated result.

        Args:
            items: List of items for current page
            total_count: Total number of items across all pages
            page: Current page number (1-indexed)
            page_size: Number of items per page
        """
        self.items = items
        self.total_count = total_count
        self.page = page
        self.page_size = page_size

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size == 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size

    @property
    def has_more(self) -> bool:
        """Check if there are more pages after current page."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there are pages before current page."""
        return self.page > 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary with pagination metadata
        """
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_count": self.total_count,
            "total_pages": self.total_pages,
            "has_more": self.has_more,
            "has_previous": self.has_previous,
        }


def validate_pagination_params(
    page: int | None = None,
    page_size: int | None = None,
) -> tuple[int, int]:
    """Validate and normalize pagination parameters.

    Args:
        page: Page number (1-indexed), defaults to 1
        page_size: Number of items per page, defaults to DEFAULT_PAGE_SIZE

    Returns:
        Tuple of (validated_page, validated_page_size)

    Raises:
        ValueError: If pagination parameters are invalid
    """
    # Default to first page if not specified
    if page is None:
        page = 1

    # Default to standard page size if not specified
    if page_size is None:
        page_size = DEFAULT_PAGE_SIZE

    # Validate page number
    page = validate_positive_int(page, "page", min_value=1)

    # Validate page size
    page_size = validate_positive_int(
        page_size,
        "page_size",
        min_value=1,
        max_value=MAX_PAGE_SIZE,
    )

    return page, page_size


def paginate_list(
    items: list[T],
    page: int,
    page_size: int,
) -> PaginatedResult[T]:
    """Paginate a list of items.

    Args:
        items: Complete list of items to paginate
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        PaginatedResult containing the requested page of items

    Examples:
        >>> items = list(range(25))  # 0-24
        >>> result = paginate_list(items, page=1, page_size=10)
        >>> result.items
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        >>> result.total_count
        25
        >>> result.has_more
        True
    """
    total_count = len(items)

    # Calculate start and end indices for this page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    # Extract the page items
    page_items = items[start_idx:end_idx]

    return PaginatedResult(
        items=page_items,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )
