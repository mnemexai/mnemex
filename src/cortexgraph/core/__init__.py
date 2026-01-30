"""Core logic for temporal decay, scoring, clustering, and pagination."""

from .decay import calculate_decay_lambda, calculate_score
from .pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    PaginatedResult,
    paginate_list,
    validate_pagination_params,
)
from .scoring import should_forget, should_promote
from .search_common import SearchParams, is_pagination_requested, validate_search_params
from .similarity import (
    calculate_centroid,
    cosine_similarity,
    jaccard_similarity,
    text_similarity,
    tfidf_similarity,
    tokenize_text,
)
from .text_utils import truncate_content

__all__ = [
    "calculate_score",
    "calculate_decay_lambda",
    "should_promote",
    "should_forget",
    "PaginatedResult",
    "paginate_list",
    "validate_pagination_params",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "truncate_content",
    "SearchParams",
    "validate_search_params",
    "is_pagination_requested",
    "cosine_similarity",
    "jaccard_similarity",
    "tfidf_similarity",
    "text_similarity",
    "tokenize_text",
    "calculate_centroid",
]
