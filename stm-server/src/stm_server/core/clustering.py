"""Clustering logic for memory consolidation."""

import math
import uuid
from typing import Dict, List, Tuple

from ..storage.models import Cluster, ClusterConfig, Memory


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
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

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


def calculate_centroid(embeddings: List[List[float]]) -> List[float]:
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


def cluster_memories_simple(
    memories: List[Memory], config: ClusterConfig
) -> List[Cluster]:
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

    # Track which memories are in which cluster
    memory_to_cluster: Dict[str, int] = {}
    clusters: List[List[Memory]] = []

    for memory in memories_with_embed:
        if memory.embed is None:
            continue

        # Find clusters similar to this memory
        similar_clusters = []
        for cluster_idx, cluster_memories in enumerate(clusters):
            # Check if memory is similar to any in this cluster
            for cluster_mem in cluster_memories:
                if cluster_mem.embed is None:
                    continue

                similarity = cosine_similarity(memory.embed, cluster_mem.embed)
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
    memories: List[Memory], threshold: float = 0.88
) -> List[Tuple[Memory, Memory, float]]:
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
