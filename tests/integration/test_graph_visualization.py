from cortexgraph.storage.models import Memory, MemoryStatus, Relation
from cortexgraph.web.services.graph_service import GraphFilter, get_graph_data


def test_graph_service_integration(temp_storage):
    """Verify graph service works with storage backend."""
    with temp_storage as storage:
        # Create data
        mem1 = Memory(id="m1", content="Node 1", status=MemoryStatus.ACTIVE)
        mem2 = Memory(id="m2", content="Node 2", status=MemoryStatus.ACTIVE)
        storage.save_memory(mem1)
        storage.save_memory(mem2)

        rel = Relation(
            id="r1",
            from_memory_id="m1",
            to_memory_id="m2",
            relation_type="related_to",
            strength=0.9,
        )
        storage.create_relation(rel)

        # Test service
        graph_data = get_graph_data(storage)

        assert len(graph_data.nodes) == 2
        assert len(graph_data.edges) == 1
        assert graph_data.total_memories == 2
        assert graph_data.total_relations == 1


def test_graph_service_filtering(temp_storage):
    """Verify graph service filtering logic."""
    with temp_storage as storage:
        mem1 = Memory(id="m1", content="Alpha", status=MemoryStatus.ACTIVE)
        mem2 = Memory(id="m2", content="Beta", status=MemoryStatus.ARCHIVED)
        storage.save_memory(mem1)
        storage.save_memory(mem2)

        # Filter by content
        filter = GraphFilter(search_query="Alpha")
        data = get_graph_data(storage, filter)
        assert len(data.nodes) == 1
        assert data.nodes[0].id == "m1"

        # Filter by status
        filter = GraphFilter(statuses=[MemoryStatus.ARCHIVED])
        data = get_graph_data(storage, filter)
        assert len(data.nodes) == 1
        assert data.nodes[0].id == "m2"
