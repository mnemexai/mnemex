"""Tests for pagination utilities."""

import pytest

from cortexgraph.core.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    PaginatedResult,
    paginate_list,
    validate_pagination_params,
)


class TestValidatePaginationParams:
    """Tests for pagination parameter validation."""

    def test_default_values(self):
        """Test that default values are applied correctly."""
        page, page_size = validate_pagination_params()
        assert page == 1
        assert page_size == DEFAULT_PAGE_SIZE

    def test_explicit_values(self):
        """Test explicit parameter values."""
        page, page_size = validate_pagination_params(page=3, page_size=25)
        assert page == 3
        assert page_size == 25

    def test_minimum_page(self):
        """Test that page must be >= 1."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            validate_pagination_params(page=0)

        with pytest.raises(ValueError, match="page must be >= 1"):
            validate_pagination_params(page=-1)

    def test_minimum_page_size(self):
        """Test that page_size must be >= 1."""
        with pytest.raises(ValueError, match="page_size must be >= 1"):
            validate_pagination_params(page_size=0)

        with pytest.raises(ValueError, match="page_size must be >= 1"):
            validate_pagination_params(page_size=-1)

    def test_maximum_page_size(self):
        """Test that page_size cannot exceed MAX_PAGE_SIZE."""
        with pytest.raises(ValueError, match=f"page_size must be <= {MAX_PAGE_SIZE}"):
            validate_pagination_params(page_size=MAX_PAGE_SIZE + 1)

    def test_valid_ranges(self):
        """Test various valid page and page_size combinations."""
        # Edge cases
        page, page_size = validate_pagination_params(page=1, page_size=1)
        assert page == 1
        assert page_size == 1

        page, page_size = validate_pagination_params(page=100, page_size=MAX_PAGE_SIZE)
        assert page == 100
        assert page_size == MAX_PAGE_SIZE

    def test_invalid_types(self):
        """Test that invalid types are rejected."""
        with pytest.raises(ValueError):
            validate_pagination_params(page="1")  # type: ignore

        with pytest.raises(ValueError):
            validate_pagination_params(page_size="10")  # type: ignore


class TestPaginatedResult:
    """Tests for PaginatedResult class."""

    def test_basic_properties(self):
        """Test basic properties of paginated result."""
        items = [1, 2, 3, 4, 5]
        result = PaginatedResult(items=items, total_count=25, page=1, page_size=5)

        assert result.items == items
        assert result.total_count == 25
        assert result.page == 1
        assert result.page_size == 5

    def test_total_pages_calculation(self):
        """Test total_pages is calculated correctly."""
        # Exact division
        result = PaginatedResult(items=[], total_count=20, page=1, page_size=10)
        assert result.total_pages == 2

        # Partial page
        result = PaginatedResult(items=[], total_count=25, page=1, page_size=10)
        assert result.total_pages == 3

        # Single page
        result = PaginatedResult(items=[], total_count=5, page=1, page_size=10)
        assert result.total_pages == 1

        # Empty
        result = PaginatedResult(items=[], total_count=0, page=1, page_size=10)
        assert result.total_pages == 0

    def test_has_more(self):
        """Test has_more flag."""
        # Has more pages
        result = PaginatedResult(items=[], total_count=25, page=1, page_size=10)
        assert result.has_more is True

        result = PaginatedResult(items=[], total_count=25, page=2, page_size=10)
        assert result.has_more is True

        # Last page
        result = PaginatedResult(items=[], total_count=25, page=3, page_size=10)
        assert result.has_more is False

        # Only page
        result = PaginatedResult(items=[], total_count=5, page=1, page_size=10)
        assert result.has_more is False

    def test_has_previous(self):
        """Test has_previous flag."""
        # First page
        result = PaginatedResult(items=[], total_count=25, page=1, page_size=10)
        assert result.has_previous is False

        # Second page
        result = PaginatedResult(items=[], total_count=25, page=2, page_size=10)
        assert result.has_previous is True

        # Third page
        result = PaginatedResult(items=[], total_count=25, page=3, page_size=10)
        assert result.has_previous is True

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = PaginatedResult(items=[1, 2, 3], total_count=25, page=2, page_size=10)
        dict_result = result.to_dict()

        assert dict_result == {
            "page": 2,
            "page_size": 10,
            "total_count": 25,
            "total_pages": 3,
            "has_more": True,
            "has_previous": True,
        }


class TestPaginateList:
    """Tests for paginate_list function."""

    def test_first_page(self):
        """Test retrieving first page."""
        items = list(range(25))  # 0-24
        result = paginate_list(items, page=1, page_size=10)

        assert result.items == list(range(10))  # 0-9
        assert result.total_count == 25
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 3
        assert result.has_more is True
        assert result.has_previous is False

    def test_middle_page(self):
        """Test retrieving middle page."""
        items = list(range(25))  # 0-24
        result = paginate_list(items, page=2, page_size=10)

        assert result.items == list(range(10, 20))  # 10-19
        assert result.total_count == 25
        assert result.page == 2
        assert result.page_size == 10
        assert result.total_pages == 3
        assert result.has_more is True
        assert result.has_previous is True

    def test_last_page(self):
        """Test retrieving last page (partial)."""
        items = list(range(25))  # 0-24
        result = paginate_list(items, page=3, page_size=10)

        assert result.items == list(range(20, 25))  # 20-24
        assert result.total_count == 25
        assert result.page == 3
        assert result.page_size == 10
        assert result.total_pages == 3
        assert result.has_more is False
        assert result.has_previous is True

    def test_page_beyond_end(self):
        """Test requesting page beyond available data."""
        items = list(range(25))  # 0-24
        result = paginate_list(items, page=10, page_size=10)

        assert result.items == []
        assert result.total_count == 25
        assert result.page == 10
        assert result.page_size == 10
        assert result.total_pages == 3
        assert result.has_more is False
        assert result.has_previous is True

    def test_empty_list(self):
        """Test paginating empty list."""
        items: list[int] = []
        result = paginate_list(items, page=1, page_size=10)

        assert result.items == []
        assert result.total_count == 0
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 0
        assert result.has_more is False
        assert result.has_previous is False

    def test_single_item(self):
        """Test paginating single item."""
        items = [42]
        result = paginate_list(items, page=1, page_size=10)

        assert result.items == [42]
        assert result.total_count == 1
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 1
        assert result.has_more is False
        assert result.has_previous is False

    def test_exact_page_size(self):
        """Test when items exactly match page size."""
        items = list(range(10))  # 0-9
        result = paginate_list(items, page=1, page_size=10)

        assert result.items == list(range(10))
        assert result.total_count == 10
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 1
        assert result.has_more is False
        assert result.has_previous is False

    def test_different_page_sizes(self):
        """Test various page sizes."""
        items = list(range(100))

        # Page size 1
        result = paginate_list(items, page=1, page_size=1)
        assert result.items == [0]
        assert result.total_pages == 100

        # Page size 25
        result = paginate_list(items, page=1, page_size=25)
        assert result.items == list(range(25))
        assert result.total_pages == 4

        # Page size 100
        result = paginate_list(items, page=1, page_size=100)
        assert result.items == list(range(100))
        assert result.total_pages == 1

    def test_with_complex_objects(self):
        """Test paginating list of dictionaries."""
        items = [{"id": i, "name": f"Item {i}"} for i in range(25)]
        result = paginate_list(items, page=2, page_size=10)

        assert len(result.items) == 10
        assert result.items[0] == {"id": 10, "name": "Item 10"}
        assert result.items[-1] == {"id": 19, "name": "Item 19"}
        assert result.total_count == 25

    def test_page_size_larger_than_list(self):
        """Test when page_size exceeds list length."""
        items = list(range(5))
        result = paginate_list(items, page=1, page_size=100)

        assert result.items == list(range(5))
        assert result.total_count == 5
        assert result.total_pages == 1
        assert result.has_more is False
