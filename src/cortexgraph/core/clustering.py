"""Clustering logic for memory consolidation."""

import uuid

from ..storage.models import Cluster, ClusterConfig, Memory
from .similarity import calculate_centroid, cosine_similarity, text_similarity


def cluster_memories_simple(memories: list[Memory], config: ClusterConfig) -> list[Cluster]:
    """
    Cluster memories using simple similarity-based grouping.

    Uses single-linkage clustering with cosine similarity threshold.
    Automatically falls back to Jaccard text similarity when embeddings are unavailable.

    Args:
        memories: List of memories (with or without embeddings)
        config: Clustering configuration

    Returns:
        List of clusters
    """
    if not memories:
        return []

    # Detect if we should use embeddings or text similarity
    # Use embeddings ONLY if ALL memories have embeddings, otherwise fall back to text similarity
    memories_with_embed = [m for m in memories if m.embed is not None]
    use_embeddings = len(memories_with_embed) == len(memories) and len(memories_with_embed) > 0

    # Always use all memories (fallback handles mixed cases gracefully)
    active_memories = memories

    if not active_memories:
        return []

    # Early termination: if we have too few memories, return individual clusters
    if len(active_memories) < config.min_cluster_size:
        return []

    # Track which memories are in which cluster
    memory_to_cluster: dict[str, int] = {}
    clusters: list[list[Memory]] = []

    # Cache for similarity calculations to avoid recomputation
    similarity_cache: dict[tuple[str, str], float] = {}

    for memory in active_memories:
        # Find clusters similar to this memory
        similar_clusters = []
        for cluster_idx, cluster_memories in enumerate(clusters):
            # Early termination: skip if cluster is already at max size
            if len(cluster_memories) >= config.max_cluster_size:
                continue

            # Check if memory is similar to any in this cluster
            for cluster_mem in cluster_memories:
                # Use cache for similarity calculation
                cache_key: tuple[str, str] = (
                    min(memory.id, cluster_mem.id),
                    max(memory.id, cluster_mem.id),
                )
                if cache_key not in similarity_cache:
                    # Calculate similarity using appropriate method
                    if use_embeddings:
                        if memory.embed is not None and cluster_mem.embed is not None:
                            similarity_cache[cache_key] = cosine_similarity(
                                memory.embed, cluster_mem.embed
                            )
                        else:
                            similarity_cache[cache_key] = 0.0
                    else:
                        # Fallback to TF-IDF text similarity
                        similarity_cache[cache_key] = text_similarity(
                            memory.content, cluster_mem.content
                        )

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
        if use_embeddings:
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
        else:
            # Use text similarity for cohesion calculation (fallback)
            centroid = None
            if len(cluster_memories) > 1:
                similarities = []
                for i in range(len(cluster_memories)):
                    for j in range(i + 1, len(cluster_memories)):
                        sim = text_similarity(
                            cluster_memories[i].content, cluster_memories[j].content
                        )
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

    Automatically falls back to Jaccard text similarity when embeddings are unavailable.

    Args:
        memories: List of memories (with or without embeddings)
        threshold: Similarity threshold for considering duplicates

    Returns:
        List of (memory1, memory2, similarity) tuples
    """
    candidates = []

    # Detect if we should use embeddings or text similarity
    # Use embeddings ONLY if ALL memories have embeddings, otherwise fall back to text similarity
    memories_with_embed = [m for m in memories if m.embed is not None]
    use_embeddings = len(memories_with_embed) == len(memories) and len(memories_with_embed) > 0

    # Always use all memories (fallback handles mixed cases gracefully)
    active_memories = memories

    for i in range(len(active_memories)):
        for j in range(i + 1, len(active_memories)):
            mem1 = active_memories[i]
            mem2 = active_memories[j]

            # Calculate similarity using appropriate method
            if use_embeddings:
                if mem1.embed is not None and mem2.embed is not None:
                    similarity = cosine_similarity(mem1.embed, mem2.embed)
                else:
                    continue  # Skip pairs without embeddings
            else:
                # Fallback to TF-IDF text similarity
                similarity = text_similarity(mem1.content, mem2.content)

            if similarity >= threshold:
                candidates.append((mem1, mem2, similarity))

    # Sort by similarity descending
    candidates.sort(key=lambda x: x[2], reverse=True)

    return candidates
