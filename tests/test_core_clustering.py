"""Tests for core clustering module."""

import math

import pytest

from mnemex.core.clustering import (
    calculate_centroid,
    cluster_memories_simple,
    cosine_similarity,
    find_duplicate_candidates,
)
from mnemex.storage.models import ClusterConfig, Memory
from tests.conftest import make_test_uuid


class TestCosineSimilarity:
    """Test suite for cosine_similarity function."""

    def test_cosine_similarity_identical_vectors(self):
        """Test that identical vectors have similarity 1.0."""
        vec = [1.0, 2.0, 3.0]
        similarity = cosine_similarity(vec, vec)
        assert math.isclose(similarity, 1.0, abs_tol=1e-9)

    def test_cosine_similarity_orthogonal_vectors(self):
        """Test that orthogonal vectors have similarity 0.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)
        assert math.isclose(similarity, 0.0, abs_tol=1e-9)

    def test_cosine_similarity_opposite_vectors(self):
        """Test that opposite vectors have similarity -1.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)
        assert math.isclose(similarity, -1.0, abs_tol=1e-9)

    def test_cosine_similarity_similar_vectors(self):
        """Test similarity between similar vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.1, 2.1, 2.9]
        similarity = cosine_similarity(vec1, vec2)
        # Should be close to 1.0 but not exactly
        assert 0.99 < similarity < 1.0

    def test_cosine_similarity_different_vectors(self):
        """Test similarity between different vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 0.0, 1.0]
        similarity = cosine_similarity(vec1, vec2)
        assert math.isclose(similarity, 0.0, abs_tol=1e-9)

    def test_cosine_similarity_zero_vector(self):
        """Test that zero vector returns 0.0 similarity."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_cosine_similarity_both_zero_vectors(self):
        """Test that two zero vectors return 0.0 similarity."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [0.0, 0.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_cosine_similarity_different_lengths_fails(self):
        """Test that vectors of different lengths raise ValueError."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]
        with pytest.raises(ValueError, match="must have the same length"):
            cosine_similarity(vec1, vec2)

    def test_cosine_similarity_high_dimensional(self):
        """Test similarity with high-dimensional vectors."""
        vec1 = [1.0] * 100
        vec2 = [1.0] * 100
        similarity = cosine_similarity(vec1, vec2)
        assert math.isclose(similarity, 1.0, abs_tol=1e-9)


class TestCalculateCentroid:
    """Test suite for calculate_centroid function."""

    def test_centroid_basic(self):
        """Test basic centroid calculation."""
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        centroid = calculate_centroid(embeddings)
        expected = [1.0 / 3, 1.0 / 3, 1.0 / 3]
        assert len(centroid) == 3
        for i in range(3):
            assert math.isclose(centroid[i], expected[i], abs_tol=1e-9)

    def test_centroid_single_embedding(self):
        """Test centroid of single embedding returns copy."""
        embedding = [1.0, 2.0, 3.0]
        centroid = calculate_centroid([embedding])
        assert centroid == embedding
        # Verify it's a copy
        assert centroid is not embedding

    def test_centroid_empty_list(self):
        """Test centroid of empty list returns empty list."""
        centroid = calculate_centroid([])
        assert centroid == []

    def test_centroid_two_embeddings(self):
        """Test centroid of two embeddings is midpoint."""
        embeddings = [
            [1.0, 2.0, 3.0],
            [3.0, 4.0, 5.0],
        ]
        centroid = calculate_centroid(embeddings)
        expected = [2.0, 3.0, 4.0]
        assert len(centroid) == 3
        for i in range(3):
            assert math.isclose(centroid[i], expected[i], abs_tol=1e-9)

    def test_centroid_multiple_dimensions(self):
        """Test centroid with various dimensions."""
        embeddings = [
            [1.0, 2.0, 3.0, 4.0, 5.0],
            [2.0, 3.0, 4.0, 5.0, 6.0],
            [3.0, 4.0, 5.0, 6.0, 7.0],
        ]
        centroid = calculate_centroid(embeddings)
        assert len(centroid) == 5
        # Each dimension should be average
        for i in range(5):
            expected = (embeddings[0][i] + embeddings[1][i] + embeddings[2][i]) / 3
            assert math.isclose(centroid[i], expected, abs_tol=1e-9)

    def test_centroid_with_negative_values(self):
        """Test centroid calculation with negative values."""
        embeddings = [
            [1.0, -1.0, 0.0],
            [-1.0, 1.0, 0.0],
        ]
        centroid = calculate_centroid(embeddings)
        expected = [0.0, 0.0, 0.0]
        assert len(centroid) == 3
        for i in range(3):
            assert math.isclose(centroid[i], expected[i], abs_tol=1e-9)


class TestClusterMemoriesSimple:
    """Test suite for cluster_memories_simple function."""

    def test_cluster_no_embeddings(self):
        """Test clustering with no embeddings returns empty list."""
        memories = [
            Memory(id=make_test_uuid("mem-1"), content="Test 1", use_count=1),
            Memory(id=make_test_uuid("mem-2"), content="Test 2", use_count=1),
        ]
        config = ClusterConfig()
        clusters = cluster_memories_simple(memories, config)
        assert clusters == []

    def test_cluster_basic_grouping(self):
        """Test basic clustering with similar embeddings."""
        # Create similar memories
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-2"),
                content="Test 2",
                use_count=1,
                embed=[0.9, 0.1, 0.0],
            ),  # Similar to mem-1
            Memory(
                id=make_test_uuid("mem-3"),
                content="Test 3",
                use_count=1,
                embed=[0.0, 1.0, 0.0],
            ),  # Different
        ]
        config = ClusterConfig(threshold=0.5, min_cluster_size=2, max_cluster_size=10)
        clusters = cluster_memories_simple(memories, config)

        # Should have at least 1 cluster (mem-1 and mem-2)
        assert len(clusters) >= 1
        # Verify cluster has appropriate size
        for cluster in clusters:
            assert len(cluster.memories) >= 2

    def test_cluster_min_size_filtering(self):
        """Test that clusters below min_cluster_size are filtered out."""
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-2"),
                content="Test 2",
                use_count=1,
                embed=[0.0, 1.0, 0.0],
            ),  # Very different
        ]
        # High min_cluster_size means no valid clusters
        config = ClusterConfig(threshold=0.9, min_cluster_size=5, max_cluster_size=10)
        clusters = cluster_memories_simple(memories, config)
        # No clusters should meet min size
        assert len(clusters) == 0

    def test_cluster_max_size_limiting(self):
        """Test that clusters are limited to max_cluster_size."""
        # Create many similar memories
        memories = []
        for i in range(15):
            memories.append(
                Memory(
                    id=make_test_uuid(f"mem-{i}"),
                    content=f"Test {i}",
                    use_count=1,
                    embed=[1.0, 0.1 * i, 0.0],  # All similar
                )
            )

        config = ClusterConfig(threshold=0.5, min_cluster_size=2, max_cluster_size=10)
        clusters = cluster_memories_simple(memories, config)

        # Verify no cluster exceeds max size
        for cluster in clusters:
            assert len(cluster.memories) <= 10

    def test_cluster_cohesion_calculation(self):
        """Test that cluster cohesion is calculated correctly."""
        # Create highly similar memories
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-2"),
                content="Test 2",
                use_count=1,
                embed=[0.99, 0.01, 0.0],
            ),
        ]
        config = ClusterConfig(threshold=0.5, min_cluster_size=2, max_cluster_size=10)
        clusters = cluster_memories_simple(memories, config)

        if clusters:
            # Cohesion should be high for similar embeddings
            assert clusters[0].cohesion > 0.9

    def test_cluster_suggested_actions(self):
        """Test that suggested actions are assigned based on cohesion."""
        # Create highly cohesive cluster (>= 0.9)
        memories_high = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-2"),
                content="Test 2",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),  # Identical
        ]
        config = ClusterConfig(threshold=0.5, min_cluster_size=2)
        clusters_high = cluster_memories_simple(memories_high, config)

        if clusters_high:
            # High cohesion should suggest auto-merge
            assert clusters_high[0].cohesion >= 0.9
            assert clusters_high[0].suggested_action == "auto-merge"

    def test_cluster_centroid_calculated(self):
        """Test that cluster centroids are calculated."""
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-2"),
                content="Test 2",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
        ]
        config = ClusterConfig(threshold=0.9, min_cluster_size=2)
        clusters = cluster_memories_simple(memories, config)

        if clusters:
            assert clusters[0].centroid is not None
            assert len(clusters[0].centroid) == 3

    def test_cluster_single_memory(self):
        """Test clustering with single memory (below min_cluster_size)."""
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
        ]
        config = ClusterConfig(min_cluster_size=2)
        clusters = cluster_memories_simple(memories, config)
        # Single memory doesn't meet min_cluster_size
        assert len(clusters) == 0


class TestFindDuplicateCandidates:
    """Test suite for find_duplicate_candidates function."""

    def test_find_duplicates_identical_embeddings(self):
        """Test finding duplicates with identical embeddings."""
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-2"),
                content="Test 2",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),  # Identical
        ]
        candidates = find_duplicate_candidates(memories, threshold=0.88)

        assert len(candidates) == 1
        mem1, mem2, similarity = candidates[0]
        assert similarity == 1.0
        assert mem1.id in [make_test_uuid("mem-1"), make_test_uuid("mem-2")]
        assert mem2.id in [make_test_uuid("mem-1"), make_test_uuid("mem-2")]

    def test_find_duplicates_no_matches(self):
        """Test finding duplicates when none exist."""
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-2"),
                content="Test 2",
                use_count=1,
                embed=[0.0, 1.0, 0.0],
            ),  # Orthogonal
        ]
        candidates = find_duplicate_candidates(memories, threshold=0.88)
        assert len(candidates) == 0

    def test_find_duplicates_custom_threshold(self):
        """Test finding duplicates with custom threshold."""
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-2"),
                content="Test 2",
                use_count=1,
                embed=[0.7, 0.7, 0.0],
            ),  # Moderately similar (similarity ~0.70)
        ]
        # Lower threshold should find the pair
        candidates = find_duplicate_candidates(memories, threshold=0.5)
        assert len(candidates) == 1

        # Higher threshold should not find the pair
        candidates_high = find_duplicate_candidates(memories, threshold=0.95)
        assert len(candidates_high) == 0

    def test_find_duplicates_sorted_by_similarity(self):
        """Test that results are sorted by similarity descending."""
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-2"),
                content="Test 2",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),  # Perfect match
            Memory(
                id=make_test_uuid("mem-3"),
                content="Test 3",
                use_count=1,
                embed=[0.95, 0.05, 0.0],
            ),  # Good match
        ]
        candidates = find_duplicate_candidates(memories, threshold=0.5)

        # Should have multiple pairs, sorted by similarity
        assert len(candidates) >= 2
        # Verify descending order
        for i in range(len(candidates) - 1):
            assert candidates[i][2] >= candidates[i + 1][2]

    def test_find_duplicates_no_embeddings(self):
        """Test finding duplicates when no embeddings present."""
        memories = [
            Memory(id=make_test_uuid("mem-1"), content="Test 1", use_count=1),
            Memory(id=make_test_uuid("mem-2"), content="Test 2", use_count=1),
        ]
        candidates = find_duplicate_candidates(memories)
        assert len(candidates) == 0

    def test_find_duplicates_mixed_embeddings(self):
        """Test finding duplicates when some memories lack embeddings."""
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(id=make_test_uuid("mem-2"), content="Test 2", use_count=1),  # No embedding
            Memory(
                id=make_test_uuid("mem-3"),
                content="Test 3",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),  # Match with mem-1
        ]
        candidates = find_duplicate_candidates(memories, threshold=0.88)

        # Should find pair between mem-1 and mem-3, ignoring mem-2
        assert len(candidates) == 1
        mem1, mem2, similarity = candidates[0]
        assert mem1.id in [make_test_uuid("mem-1"), make_test_uuid("mem-3")]
        assert mem2.id in [make_test_uuid("mem-1"), make_test_uuid("mem-3")]

    def test_find_duplicates_multiple_pairs(self):
        """Test finding multiple duplicate pairs."""
        memories = [
            Memory(
                id=make_test_uuid("mem-1"),
                content="Test 1",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-2"),
                content="Test 2",
                use_count=1,
                embed=[1.0, 0.0, 0.0],
            ),  # Pair with mem-1
            Memory(
                id=make_test_uuid("mem-3"),
                content="Test 3",
                use_count=1,
                embed=[0.0, 1.0, 0.0],
            ),
            Memory(
                id=make_test_uuid("mem-4"),
                content="Test 4",
                use_count=1,
                embed=[0.0, 1.0, 0.0],
            ),  # Pair with mem-3
        ]
        candidates = find_duplicate_candidates(memories, threshold=0.88)

        # Should find 2 pairs: (mem-1, mem-2) and (mem-3, mem-4)
        # Plus cross-pairs within each group
        assert len(candidates) >= 2
