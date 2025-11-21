import time
from typing import Any

from ...storage.models import (
    GraphData,
    GraphFilter,
    MemoryStatus,
    memory_to_graph_node,
    relation_to_graph_edge,
)


def get_graph_data(storage: Any, filter: GraphFilter | None = None) -> GraphData:
    """
    Retrieve graph data from storage, applying optional filters.

    Args:
        storage: Storage backend instance (JSONLStorage or SQLiteStorage)
        filter: Optional filters to apply

    Returns:
        GraphData object containing nodes and edges
    """
    start_time = time.time()

    # Default filter if none provided
    if filter is None:
        filter = GraphFilter()

    # 1. Fetch memories
    # For MVP, we'll fetch all and filter in memory if storage doesn't support complex filtering
    # TODO: Push filtering down to storage layer for performance

    # Use list_memories with limit if no other filters (optimization)
    # But if we have other filters, we might need to fetch more and filter
    # For now, let's fetch all active memories (or specified status)

    statuses = filter.statuses or [MemoryStatus.ACTIVE]

    # Fetch all memories matching status (most storage backends support status filter)
    # We can't use limit/offset here yet because we need to apply other filters first
    all_memories = []
    for status in statuses:
        # We fetch a large number to ensure we have enough after filtering
        # In a real DB, we'd construct a query
        memories = storage.list_memories(status=status, limit=10000)
        all_memories.extend(memories)

    # Apply content filters
    filtered_memories = []
    for mem in all_memories:
        # Tag filter
        if filter.tags:
            if not mem.meta or not any(tag in mem.meta.tags for tag in filter.tags):
                continue

        # Entity filter
        if filter.entities:
            if not any(entity in mem.entities for entity in filter.entities):
                continue

        # Search query (simple containment)
        if filter.search_query:
            if filter.search_query.lower() not in mem.content.lower():
                continue

        # Score filters (decay score is calculated, assume 1.0 for now or implement calc)
        # For MVP, we'll skip decay score filtering unless we calculate it here
        # TODO: Implement decay score calculation

        # Time filters
        if filter.created_after and mem.created_at < filter.created_after:
            continue
        if filter.created_before and mem.created_at > filter.created_before:
            continue

        filtered_memories.append(mem)

    # Apply pagination
    total_filtered = len(filtered_memories)
    paginated_memories = filtered_memories[filter.offset : filter.offset + filter.limit]

    # 2. Convert to GraphNodes
    # We need decay score for conversion. For now, use 1.0 or a placeholder
    # TODO: Integrate decay module
    nodes = [memory_to_graph_node(m, decay_score=1.0) for m in paginated_memories]
    node_ids = {n.id for n in nodes}

    # 3. Fetch relations
    # We only want relations where BOTH source and target are in our node set
    # or maybe just one? Usually for a graph view, we want edges between visible nodes.

    all_relations = storage.get_all_relations()
    edges = []

    for rel in all_relations:
        if rel.from_memory_id in node_ids and rel.to_memory_id in node_ids:
            edges.append(relation_to_graph_edge(rel))

    # 4. Build response
    query_time = (time.time() - start_time) * 1000

    return GraphData(
        nodes=nodes,
        edges=edges,
        total_memories=storage.count_memories(),  # Total in DB
        total_relations=len(all_relations),  # Total in DB (approx)
        filtered_count=total_filtered,
        query_time_ms=query_time,
    )
