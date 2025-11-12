"""Unit tests for ActivationGraph index."""

import numpy as np

from cortexgraph.storage.activation_index import ActivationGraph, build_activation_graph
from cortexgraph.storage.models import Memory, MemoryMetadata, Relation


class TestActivationGraph:
    """Test ActivationGraph model and methods."""

    def test_find_by_keywords_single_match(self) -> None:
        """Test finding memories by single keyword."""
        graph = ActivationGraph(last_updated=1234567890)
        graph.keyword_to_memories = {
            "python": ["mem1", "mem2"],
            "typescript": ["mem3"],
        }

        result = graph.find_by_keywords(["python"])
        assert result == {"mem1", "mem2"}

    def test_find_by_keywords_multiple_matches(self) -> None:
        """Test finding memories by multiple keywords (union)."""
        graph = ActivationGraph(last_updated=1234567890)
        graph.keyword_to_memories = {
            "python": ["mem1", "mem2"],
            "typescript": ["mem2", "mem3"],
            "react": ["mem4"],
        }

        result = graph.find_by_keywords(["python", "react"])
        assert result == {"mem1", "mem2", "mem4"}

    def test_find_by_keywords_no_match(self) -> None:
        """Test finding memories when no keywords match."""
        graph = ActivationGraph(last_updated=1234567890)
        graph.keyword_to_memories = {"python": ["mem1"]}

        result = graph.find_by_keywords(["rust", "go"])
        assert result == set()

    def test_find_by_entities(self) -> None:
        """Test finding memories by entities."""
        graph = ActivationGraph(last_updated=1234567890)
        graph.entity_to_memories = {
            "jwt": ["mem1", "mem2"],
            "oauth": ["mem3"],
        }

        result = graph.find_by_entities(["jwt"])
        assert result == {"mem1", "mem2"}

        result = graph.find_by_entities(["jwt", "oauth"])
        assert result == {"mem1", "mem2", "mem3"}

    def test_find_by_tags(self) -> None:
        """Test finding memories by tags."""
        graph = ActivationGraph(last_updated=1234567890)
        graph.tag_to_memories = {
            "authentication": ["mem1", "mem2"],
            "security": ["mem2", "mem3"],
        }

        result = graph.find_by_tags(["authentication"])
        assert result == {"mem1", "mem2"}

        result = graph.find_by_tags(["authentication", "security"])
        assert result == {"mem1", "mem2", "mem3"}

    def test_get_related_memories(self) -> None:
        """Test getting related memories via outgoing relations."""
        graph = ActivationGraph(last_updated=1234567890)
        graph.outgoing_relations = {
            "mem1": ["mem2", "mem3"],
            "mem2": ["mem4"],
        }

        assert graph.get_related_memories("mem1") == ["mem2", "mem3"]
        assert graph.get_related_memories("mem2") == ["mem4"]
        assert graph.get_related_memories("mem999") == []

    def test_activation_graph_empty(self) -> None:
        """Test ActivationGraph with empty indexes."""
        graph = ActivationGraph(last_updated=1234567890)

        assert graph.find_by_keywords(["python"]) == set()
        assert graph.find_by_entities(["jwt"]) == set()
        assert graph.find_by_tags(["auth"]) == set()
        assert graph.get_related_memories("mem1") == []


class TestBuildActivationGraph:
    """Test build_activation_graph function."""

    def test_build_graph_with_keywords(self) -> None:
        """Test building graph with keyword extraction."""

        def mock_extractor(text: str) -> list[str]:
            """Mock keyword extractor."""
            return ["python", "testing"] if "python" in text.lower() else ["web", "api"]

        memories = [
            Memory(
                id="mem1",
                content="Python testing framework",
                meta=MemoryMetadata(tags=["python", "testing"]),
                entities=["pytest"],
            ),
            Memory(
                id="mem2",
                content="Web API development",
                meta=MemoryMetadata(tags=["web", "api"]),
                entities=["fastapi"],
            ),
        ]
        relations: list[Relation] = []

        graph = build_activation_graph(memories, relations, extract_keywords_fn=mock_extractor)

        assert graph.memory_count == 2
        assert graph.relation_count == 0
        assert "python" in graph.keyword_to_memories
        assert "web" in graph.keyword_to_memories
        assert "mem1" in graph.keyword_to_memories["python"]
        assert "mem2" in graph.keyword_to_memories["web"]

    def test_build_graph_entities(self) -> None:
        """Test building entity index."""
        memories = [
            Memory(
                id="mem1",
                content="Using JWT for authentication",
                meta=MemoryMetadata(),
                entities=["JWT", "OAuth"],
            ),
            Memory(
                id="mem2",
                content="JWT best practices",
                meta=MemoryMetadata(),
                entities=["JWT"],
            ),
        ]
        relations: list[Relation] = []

        graph = build_activation_graph(memories, relations)

        # Entities should be lowercase in index
        assert "jwt" in graph.entity_to_memories
        assert "oauth" in graph.entity_to_memories
        assert set(graph.entity_to_memories["jwt"]) == {"mem1", "mem2"}
        assert graph.entity_to_memories["oauth"] == ["mem1"]

    def test_build_graph_tags(self) -> None:
        """Test building tag index."""
        memories = [
            Memory(
                id="mem1",
                content="Content 1",
                meta=MemoryMetadata(tags=["Auth", "Security"]),
            ),
            Memory(
                id="mem2",
                content="Content 2",
                meta=MemoryMetadata(tags=["Security", "API"]),
            ),
        ]
        relations: list[Relation] = []

        graph = build_activation_graph(memories, relations)

        # Tags should be lowercase in index
        assert "auth" in graph.tag_to_memories
        assert "security" in graph.tag_to_memories
        assert "api" in graph.tag_to_memories
        assert graph.tag_to_memories["auth"] == ["mem1"]
        assert set(graph.tag_to_memories["security"]) == {"mem1", "mem2"}

    def test_build_graph_relations(self) -> None:
        """Test building relation graph."""
        memories = [
            Memory(id="mem1", content="First"),
            Memory(id="mem2", content="Second"),
            Memory(id="mem3", content="Third"),
        ]
        relations = [
            Relation(
                id="rel1",
                from_memory_id="mem1",
                to_memory_id="mem2",
                relation_type="related",
            ),
            Relation(
                id="rel2",
                from_memory_id="mem1",
                to_memory_id="mem3",
                relation_type="related",
            ),
            Relation(
                id="rel3",
                from_memory_id="mem2",
                to_memory_id="mem3",
                relation_type="supports",
            ),
        ]

        graph = build_activation_graph(memories, relations)

        assert graph.relation_count == 3
        assert set(graph.outgoing_relations["mem1"]) == {"mem2", "mem3"}
        assert graph.outgoing_relations["mem2"] == ["mem3"]
        assert "mem3" not in graph.outgoing_relations  # No outgoing relations

    def test_build_graph_with_embeddings(self) -> None:
        """Test building graph with memory embeddings."""
        embed1 = [0.1, 0.2, 0.3]
        embed2 = [0.4, 0.5, 0.6]

        memories = [
            Memory(id="mem1", content="First", embed=embed1),
            Memory(id="mem2", content="Second", embed=embed2),
            Memory(id="mem3", content="Third"),  # No embedding
        ]
        relations: list[Relation] = []

        graph = build_activation_graph(memories, relations)

        assert graph.memory_embeddings is not None
        assert "mem1" in graph.memory_embeddings
        assert "mem2" in graph.memory_embeddings
        assert "mem3" not in graph.memory_embeddings

        # Check embedding values
        np.testing.assert_array_equal(graph.memory_embeddings["mem1"], np.array(embed1))
        np.testing.assert_array_equal(graph.memory_embeddings["mem2"], np.array(embed2))

    def test_build_graph_empty_inputs(self) -> None:
        """Test building graph with empty inputs."""
        graph = build_activation_graph([], [])

        assert graph.memory_count == 0
        assert graph.relation_count == 0
        assert len(graph.keyword_to_memories) == 0
        assert len(graph.entity_to_memories) == 0
        assert len(graph.tag_to_memories) == 0
        assert len(graph.outgoing_relations) == 0
        assert graph.memory_embeddings is None

    def test_build_graph_no_keyword_extractor(self) -> None:
        """Test building graph without keyword extractor."""
        memories = [
            Memory(id="mem1", content="Python testing", meta=MemoryMetadata(tags=["python"]))
        ]
        relations: list[Relation] = []

        graph = build_activation_graph(memories, relations, extract_keywords_fn=None)

        # Keyword index should be empty (no extractor provided)
        assert len(graph.keyword_to_memories) == 0
        # But tag and entity indexes should still work
        assert "python" in graph.tag_to_memories

    def test_build_graph_comprehensive(self) -> None:
        """Test building a comprehensive graph with all index types."""

        def mock_extractor(text: str) -> list[str]:
            return text.lower().split()[:3]  # First 3 words

        memories = [
            Memory(
                id="mem1",
                content="Python machine learning frameworks",
                meta=MemoryMetadata(tags=["python", "ml"]),
                entities=["TensorFlow", "PyTorch"],
                embed=[0.1, 0.2, 0.3],
            ),
            Memory(
                id="mem2",
                content="Deep learning neural networks",
                meta=MemoryMetadata(tags=["ml", "dl"]),
                entities=["PyTorch"],
                embed=[0.4, 0.5, 0.6],
            ),
        ]
        relations = [
            Relation(
                id="rel1", from_memory_id="mem1", to_memory_id="mem2", relation_type="related"
            ),
        ]

        graph = build_activation_graph(memories, relations, extract_keywords_fn=mock_extractor)

        # Verify all indexes populated
        assert graph.memory_count == 2
        assert graph.relation_count == 1
        assert len(graph.keyword_to_memories) > 0  # Keywords extracted
        assert len(graph.entity_to_memories) == 2  # tensorflow, pytorch
        assert len(graph.tag_to_memories) == 3  # python, ml, dl
        assert "mem1" in graph.outgoing_relations
        assert graph.memory_embeddings is not None
        assert len(graph.memory_embeddings) == 2

    def test_build_graph_timestamp(self) -> None:
        """Test that graph has valid timestamp."""
        import time

        before = int(time.time())
        graph = build_activation_graph([], [])
        after = int(time.time())

        assert before <= graph.last_updated <= after
