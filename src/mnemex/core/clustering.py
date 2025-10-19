"""Clustering logic for memory consolidation."""

import math
import uuid

from ..storage.models import Cluster, ClusterConfig, Memory


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity (0 to 1)
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have the same length")

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


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


def cluster_memories_simple(memories: list[Memory], config: ClusterConfig) -> list[Cluster]:
    """
    Cluster memories using simple similarity-based grouping.

    Uses single-linkage clustering with cosine similarity threshold.

    Args:
        memories: List of memories with embeddings
        config: Clustering configuration

    Returns:
        List of clusters
    """
    # Filter memories that have embeddings
    memories_with_embed = [m for m in memories if m.embed is not None]

    if not memories_with_embed:
        return []

    # Early termination: if we have too few memories, return individual clusters
    if len(memories_with_embed) < config.min_cluster_size:
        return []

    # Track which memories are in which cluster
    memory_to_cluster: dict[str, int] = {}
    clusters: list[list[Memory]] = []

    # Cache for similarity calculations to avoid recomputation
    similarity_cache: dict[tuple[str, str], float] = {}

    for memory in memories_with_embed:
        if memory.embed is None:
            continue

        # Find clusters similar to this memory
        similar_clusters = []
        for cluster_idx, cluster_memories in enumerate(clusters):
            # Early termination: skip if cluster is already at max size
            if len(cluster_memories) >= config.max_cluster_size:
                continue

            # Check if memory is similar to any in this cluster
            for cluster_mem in cluster_memories:
                if cluster_mem.embed is None:
                    continue

                # Use cache for similarity calculation
                cache_key: tuple[str, str] = (
                    min(memory.id, cluster_mem.id),
                    max(memory.id, cluster_mem.id),
                )
                if cache_key not in similarity_cache:
                    similarity_cache[cache_key] = cosine_similarity(memory.embed, cluster_mem.embed)

                similarity = similarity_cache[cache_key]
                if similarity >= config.threshold:
                    similar_clusters.append(cluster_idx)
                    break  # Found a match in this cluster

        if not similar_clusters:
            # Start new cluster
            clusters.append([memory])
            memory_to_cluster[memory.id] = len(clusters) - 1
        else:
            # Merge into first similar cluster
            # (and potentially merge similar clusters together)
            target_idx = similar_clusters[0]
            clusters[target_idx].append(memory)
            memory_to_cluster[memory.id] = target_idx

            # Merge other similar clusters into target
            for idx in sorted(similar_clusters[1:], reverse=True):
                clusters[target_idx].extend(clusters[idx])
                for mem in clusters[idx]:
                    memory_to_cluster[mem.id] = target_idx
                del clusters[idx]

    # Convert to Cluster objects
    result_clusters = []
    for cluster_memories in clusters:
        # Filter by size constraints
        if len(cluster_memories) < config.min_cluster_size:
            continue
        if len(cluster_memories) > config.max_cluster_size:
            # Split large clusters (simplified: just take first max_size)
            cluster_memories = cluster_memories[: config.max_cluster_size]

        # Calculate centroid and cohesion
        embeddings = [m.embed for m in cluster_memories if m.embed is not None]
        centroid = calculate_centroid(embeddings) if embeddings else None

        # Calculate average pairwise similarity (cohesion)
        if len(embeddings) > 1:
            similarities = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    sim = cosine_similarity(embeddings[i], embeddings[j])
                    similarities.append(sim)
            cohesion = sum(similarities) / len(similarities)
        else:
            cohesion = 1.0

        # Determine suggested action based on cohesion
        if cohesion >= 0.9:
            suggested_action = "auto-merge"
        elif cohesion >= 0.75:
            suggested_action = "llm-review"
        else:
            suggested_action = "keep-separate"

        cluster = Cluster(
            id=str(uuid.uuid4()),
            memories=cluster_memories,
            centroid=centroid,
            cohesion=cohesion,
            suggested_action=suggested_action,
        )
        result_clusters.append(cluster)

    return result_clusters


def find_duplicate_candidates(
    memories: list[Memory], threshold: float = 0.88
) -> list[tuple[Memory, Memory, float]]:
    """
    Find pairs of memories that are likely duplicates based on similarity.

    Args:
        memories: List of memories with embeddings
        threshold: Similarity threshold for considering duplicates

    Returns:
        List of (memory1, memory2, similarity) tuples
    """
    candidates = []

    memories_with_embed = [m for m in memories if m.embed is not None]

    for i in range(len(memories_with_embed)):
        for j in range(i + 1, len(memories_with_embed)):
            mem1 = memories_with_embed[i]
            mem2 = memories_with_embed[j]

            if mem1.embed is None or mem2.embed is None:
                continue

            similarity = cosine_similarity(mem1.embed, mem2.embed)
            if similarity >= threshold:
                candidates.append((mem1, mem2, similarity))

    # Sort by similarity descending
    candidates.sort(key=lambda x: x[2], reverse=True)

    return candidates
