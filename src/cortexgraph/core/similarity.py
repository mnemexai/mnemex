"""Similarity calculation utilities for memory clustering and search.

This module consolidates various similarity metrics used across the system:
- Cosine similarity (vector-based, for embeddings)
- Jaccard similarity (set-based, for token overlap)
- TF-IDF similarity (weighted term frequency)
- Text similarity (high-level convenience wrapper)

Pre-compiles regex patterns for efficient tokenization.
"""

import math
import re
from collections import Counter

# Pre-compile regex pattern for tokenization (avoid recompilation on each call)
_CLEAN_PATTERN = re.compile(r"[^\w\s]")

# Pre-compile commonly used patterns for efficiency
_WHITESPACE_PATTERN = re.compile(r"\s+")


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Optimized with fast paths for edge cases and early termination.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity (0 to 1)
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have the same length")

    # Fast path: empty vectors
    if not vec1:
        return 0.0

    # Calculate dot product and magnitudes in one pass
    dot_product = 0.0
    mag1_sq = 0.0
    mag2_sq = 0.0

    for a, b in zip(vec1, vec2, strict=False):
        dot_product += a * b
        mag1_sq += a * a
        mag2_sq += b * b

    # Fast path: zero magnitude vectors
    if mag1_sq == 0 or mag2_sq == 0:
        return 0.0

    # Calculate magnitudes from squared values
    mag1 = math.sqrt(mag1_sq)
    mag2 = math.sqrt(mag2_sq)

    return dot_product / (mag1 * mag2)


def tokenize_text(text: str) -> list[str]:
    """
    Tokenize text into words for similarity calculation.

    Uses pre-compiled regex patterns for efficiency.
    Optimized with early termination for very short text.

    Args:
        text: Input text

    Returns:
        List of lowercase tokens (length > 2)
    """
    # Early exit for very short text
    if not text or len(text) < 3:
        return []

    # Remove punctuation and normalize whitespace using pre-compiled patterns
    text = _CLEAN_PATTERN.sub(" ", text.lower())
    tokens = _WHITESPACE_PATTERN.split(text.strip())

    # Filter out empty strings and very short tokens
    return [t for t in tokens if len(t) > 2]


def compute_tf(tokens: list[str]) -> dict[str, float]:
    """
    Compute term frequency for tokens.

    Args:
        tokens: List of tokens

    Returns:
        Dictionary mapping term to frequency
    """
    if not tokens:
        return {}

    counter = Counter(tokens)
    total = len(tokens)
    return {term: count / total for term, count in counter.items()}


def compute_idf(documents: list[list[str]]) -> dict[str, float]:
    """
    Compute inverse document frequency across documents.

    Args:
        documents: List of tokenized documents

    Returns:
        Dictionary mapping term to IDF score
    """
    if not documents:
        return {}

    num_docs = len(documents)
    doc_freq: dict[str, int] = Counter()

    for doc in documents:
        unique_terms = set(doc)
        for term in unique_terms:
            doc_freq[term] += 1

    return {term: math.log(num_docs / freq) for term, freq in doc_freq.items()}


def tfidf_similarity(text1: str, text2: str, idf_scores: dict[str, float] | None = None) -> float:
    """
    Calculate TF-IDF cosine similarity between two texts.

    Args:
        text1: First text
        text2: Second text
        idf_scores: Pre-computed IDF scores (optional, computed if not provided)

    Returns:
        Cosine similarity (0 to 1)
    """
    tokens1 = tokenize_text(text1)
    tokens2 = tokenize_text(text2)

    if not tokens1 or not tokens2:
        return 0.0

    # Compute TF for each document
    tf1 = compute_tf(tokens1)
    tf2 = compute_tf(tokens2)

    # If IDF scores not provided, compute them from these two documents
    if idf_scores is None:
        idf_scores = compute_idf([tokens1, tokens2])

    # Get all unique terms
    all_terms = set(tf1.keys()) | set(tf2.keys())

    # Compute TF-IDF vectors
    vec1 = [tf1.get(term, 0) * idf_scores.get(term, 0) for term in all_terms]
    vec2 = [tf2.get(term, 0) * idf_scores.get(term, 0) for term in all_terms]

    # Compute cosine similarity
    return cosine_similarity(vec1, vec2)


def jaccard_similarity(tokens1: set[str], tokens2: set[str]) -> float:
    """
    Calculate Jaccard similarity between two sets of tokens.

    Optimized with fast paths for edge cases.

    Args:
        tokens1: First set of tokens
        tokens2: Second set of tokens

    Returns:
        Jaccard similarity (0 to 1)
    """
    # Fast path: empty sets
    if not tokens1 or not tokens2:
        return 0.0

    # Fast path: identical sets
    if tokens1 is tokens2:
        return 1.0

    # Calculate intersection and union
    intersection = tokens1 & tokens2

    # Fast path: no intersection
    if not intersection:
        return 0.0

    union = tokens1 | tokens2
    return len(intersection) / len(union)


def text_similarity(text1: str, text2: str) -> float:
    """
    Calculate text similarity using Jaccard similarity on tokens (fallback when embeddings unavailable).

    This method works well for duplicate detection and similar content clustering,
    avoiding the TF-IDF edge case where identical documents get 0 similarity.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score (0 to 1)
    """
    tokens1 = set(tokenize_text(text1))
    tokens2 = set(tokenize_text(text2))
    return jaccard_similarity(tokens1, tokens2)


def calculate_centroid(embeddings: list[list[float]]) -> list[float]:
    """
    Calculate the centroid (average) of multiple embedding vectors.

    Args:
        embeddings: List of embedding vectors

    Returns:
        Centroid vector
    """
    if not embeddings:
        return []

    dim = len(embeddings[0])
    centroid = [0.0] * dim

    for embed in embeddings:
        for i, val in enumerate(embed):
            centroid[i] += val

    for i in range(dim):
        centroid[i] /= len(embeddings)

    return centroid
