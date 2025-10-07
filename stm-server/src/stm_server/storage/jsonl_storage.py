"""JSONL-based storage interface for STM server.

Human-readable, git-friendly storage with in-memory indexing for fast queries.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..config import get_config
from .models import KnowledgeGraph, Memory, MemoryStatus, Relation


class JSONLStorage:
    """JSONL-based storage with in-memory indexing."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """
        Initialize JSONL storage.

        Args:
            storage_path: Path to storage directory. If None, uses config default.
        """
        config = get_config()

        # Storage directory (contains memories.jsonl and relations.jsonl)
        if storage_path is None:
            # Use db_path but change extension to directory
            self.storage_dir = config.db_path.parent / "jsonl"
        else:
            self.storage_dir = storage_path if isinstance(storage_path, Path) else Path(storage_path)

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.memories_path = self.storage_dir / "memories.jsonl"
        self.relations_path = self.storage_dir / "relations.jsonl"

        # In-memory indexes
        self._memories: Dict[str, Memory] = {}
        self._relations: Dict[str, Relation] = {}
        self._deleted_memory_ids: Set[str] = set()
        self._deleted_relation_ids: Set[str] = set()

        # Track if connected
        self._connected = False

    def connect(self) -> None:
        """Load JSONL files into memory and build indexes."""
        if self._connected:
            return

        # Load memories
        if self.memories_path.exists():
            with open(self.memories_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    data = json.loads(line)

                    # Check if this is a deletion marker
                    if data.get("_deleted"):
                        self._deleted_memory_ids.add(data["id"])
                        self._memories.pop(data["id"], None)
                    else:
                        memory = Memory(**data)
                        self._memories[memory.id] = memory

        # Load relations
        if self.relations_path.exists():
            with open(self.relations_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    data = json.loads(line)

                    # Check if this is a deletion marker
                    if data.get("_deleted"):
                        self._deleted_relation_ids.add(data["id"])
                        self._relations.pop(data["id"], None)
                    else:
                        relation = Relation(**data)
                        self._relations[relation.id] = relation

        self._connected = True

    def close(self) -> None:
        """Close storage (no-op for JSONL, everything is already persisted)."""
        self._connected = False

    def __enter__(self) -> "JSONLStorage":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def _append_memory(self, memory: Memory) -> None:
        """Append memory to JSONL file."""
        with open(self.memories_path, "a") as f:
            # Convert to JSON-serializable dict
            data = memory.model_dump(mode="json")
            f.write(json.dumps(data) + "\n")

    def _append_relation(self, relation: Relation) -> None:
        """Append relation to JSONL file."""
        with open(self.relations_path, "a") as f:
            data = relation.model_dump(mode="json")
            f.write(json.dumps(data) + "\n")

    def _append_deletion_marker(self, memory_id: str, is_relation: bool = False) -> None:
        """Append a deletion marker to JSONL file."""
        marker = {"id": memory_id, "_deleted": True}

        if is_relation:
            with open(self.relations_path, "a") as f:
                f.write(json.dumps(marker) + "\n")
        else:
            with open(self.memories_path, "a") as f:
                f.write(json.dumps(marker) + "\n")

    def save_memory(self, memory: Memory) -> None:
        """
        Save or update a memory.

        Args:
            memory: Memory object to save
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        # Update in-memory index
        self._memories[memory.id] = memory

        # Append to JSONL file
        self._append_memory(memory)

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        Retrieve a memory by ID.

        Args:
            memory_id: ID of the memory to retrieve

        Returns:
            Memory object or None if not found
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        return self._memories.get(memory_id)

    def update_memory(
        self,
        memory_id: str,
        last_used: Optional[int] = None,
        use_count: Optional[int] = None,
        strength: Optional[float] = None,
        status: Optional[MemoryStatus] = None,
        promoted_at: Optional[int] = None,
        promoted_to: Optional[str] = None,
    ) -> bool:
        """
        Update specific fields of a memory.

        Args:
            memory_id: ID of the memory to update
            last_used: New last_used timestamp
            use_count: New use_count value
            strength: New strength value
            status: New status
            promoted_at: New promoted_at timestamp
            promoted_to: New promoted_to path

        Returns:
            True if memory was updated, False if not found
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        memory = self._memories.get(memory_id)
        if memory is None:
            return False

        # Update fields
        if last_used is not None:
            memory.last_used = last_used
        if use_count is not None:
            memory.use_count = use_count
        if strength is not None:
            memory.strength = strength
        if status is not None:
            memory.status = status
        if promoted_at is not None:
            memory.promoted_at = promoted_at
        if promoted_to is not None:
            memory.promoted_to = promoted_to

        # Append updated memory to JSONL
        self._append_memory(memory)

        return True

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory.

        Args:
            memory_id: ID of the memory to delete

        Returns:
            True if memory was deleted, False if not found
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        if memory_id not in self._memories:
            return False

        # Remove from in-memory index
        del self._memories[memory_id]
        self._deleted_memory_ids.add(memory_id)

        # Append deletion marker
        self._append_deletion_marker(memory_id)

        return True

    def list_memories(
        self,
        status: Optional[MemoryStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Memory]:
        """
        List memories with optional filtering.

        Args:
            status: Filter by memory status
            limit: Maximum number of memories to return
            offset: Number of memories to skip

        Returns:
            List of Memory objects
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        # Filter by status
        memories = list(self._memories.values())

        if status is not None:
            memories = [m for m in memories if m.status == status]

        # Sort by last_used DESC
        memories.sort(key=lambda m: m.last_used, reverse=True)

        # Apply pagination
        if offset > 0:
            memories = memories[offset:]

        if limit is not None:
            memories = memories[:limit]

        return memories

    def search_memories(
        self,
        tags: Optional[List[str]] = None,
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE,
        window_days: Optional[int] = None,
        limit: int = 10,
    ) -> List[Memory]:
        """
        Search memories with filters.

        Args:
            tags: Filter by tags (any match)
            status: Filter by status
            window_days: Only return memories from last N days
            limit: Maximum results

        Returns:
            List of Memory objects
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        memories = list(self._memories.values())

        # Filter by status
        if status is not None:
            memories = [m for m in memories if m.status == status]

        # Filter by time window
        if window_days is not None:
            cutoff = int(time.time()) - (window_days * 86400)
            memories = [m for m in memories if m.last_used >= cutoff]

        # Filter by tags (any match)
        if tags:
            memories = [
                m for m in memories
                if any(tag in m.meta.tags for tag in tags)
            ]

        # Sort by last_used DESC
        memories.sort(key=lambda m: m.last_used, reverse=True)

        return memories[:limit]

    def count_memories(self, status: Optional[MemoryStatus] = None) -> int:
        """
        Count memories with optional status filter.

        Args:
            status: Filter by memory status

        Returns:
            Number of memories
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        if status is None:
            return len(self._memories)

        return sum(1 for m in self._memories.values() if m.status == status)

    def get_all_embeddings(self) -> Dict[str, List[float]]:
        """
        Get all memory embeddings for clustering/similarity search.

        Returns:
            Dictionary mapping memory IDs to embedding vectors
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        embeddings = {}
        for memory_id, memory in self._memories.items():
            if memory.embed is not None and memory.status == MemoryStatus.ACTIVE:
                embeddings[memory_id] = memory.embed

        return embeddings

    # Relation methods

    def create_relation(self, relation: Relation) -> None:
        """
        Create a new relation between memories.

        Args:
            relation: Relation object to create
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        # Update in-memory index
        self._relations[relation.id] = relation

        # Append to JSONL file
        self._append_relation(relation)

    def get_relations(
        self,
        from_memory_id: Optional[str] = None,
        to_memory_id: Optional[str] = None,
        relation_type: Optional[str] = None,
    ) -> List[Relation]:
        """
        Get relations with optional filtering.

        Args:
            from_memory_id: Filter by source memory
            to_memory_id: Filter by target memory
            relation_type: Filter by relation type

        Returns:
            List of Relation objects
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        relations = list(self._relations.values())

        if from_memory_id:
            relations = [r for r in relations if r.from_memory_id == from_memory_id]

        if to_memory_id:
            relations = [r for r in relations if r.to_memory_id == to_memory_id]

        if relation_type:
            relations = [r for r in relations if r.relation_type == relation_type]

        return relations

    def get_all_relations(self) -> List[Relation]:
        """
        Get all relations in the database.

        Returns:
            List of all Relation objects
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        return list(self._relations.values())

    def delete_relation(self, relation_id: str) -> bool:
        """
        Delete a relation.

        Args:
            relation_id: ID of relation to delete

        Returns:
            True if deleted, False if not found
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        if relation_id not in self._relations:
            return False

        # Remove from in-memory index
        del self._relations[relation_id]
        self._deleted_relation_ids.add(relation_id)

        # Append deletion marker
        self._append_deletion_marker(relation_id, is_relation=True)

        return True

    def get_knowledge_graph(
        self, status: Optional[MemoryStatus] = MemoryStatus.ACTIVE
    ) -> KnowledgeGraph:
        """
        Get the complete knowledge graph of memories and relations.

        Args:
            status: Filter memories by status (default: ACTIVE)

        Returns:
            KnowledgeGraph with memories, relations, and statistics
        """
        from ..core.decay import calculate_score

        memories = self.list_memories(status=status)
        relations = self.get_all_relations()

        # Calculate statistics
        now = int(time.time())
        scores = [
            calculate_score(
                use_count=m.use_count,
                last_used=m.last_used,
                strength=m.strength,
                now=now,
            )
            for m in memories
        ]

        stats = {
            "total_memories": len(memories),
            "total_relations": len(relations),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "avg_use_count": sum(m.use_count for m in memories) / len(memories) if memories else 0,
            "status_filter": status.value if status else "all",
        }

        return KnowledgeGraph(
            memories=memories,
            relations=relations,
            stats=stats,
        )

    # Maintenance operations

    def compact(self) -> Dict[str, int]:
        """
        Compact JSONL files by removing deletion markers and duplicates.

        This rewrites the JSONL files to include only the latest version of each
        memory/relation, excluding deleted entries.

        Returns:
            Statistics about the compaction (lines_before, lines_after, etc.)
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        stats = {
            "memories_before": 0,
            "memories_after": len(self._memories),
            "relations_before": 0,
            "relations_after": len(self._relations),
        }

        # Count lines before compaction
        if self.memories_path.exists():
            with open(self.memories_path, "r") as f:
                stats["memories_before"] = sum(1 for line in f if line.strip())

        if self.relations_path.exists():
            with open(self.relations_path, "r") as f:
                stats["relations_before"] = sum(1 for line in f if line.strip())

        # Rewrite memories file
        temp_memories = self.memories_path.with_suffix(".jsonl.tmp")
        with open(temp_memories, "w") as f:
            for memory in self._memories.values():
                data = memory.model_dump(mode="json")
                f.write(json.dumps(data) + "\n")

        temp_memories.replace(self.memories_path)

        # Rewrite relations file
        temp_relations = self.relations_path.with_suffix(".jsonl.tmp")
        with open(temp_relations, "w") as f:
            for relation in self._relations.values():
                data = relation.model_dump(mode="json")
                f.write(json.dumps(data) + "\n")

        temp_relations.replace(self.relations_path)

        # Clear deletion tracking
        self._deleted_memory_ids.clear()
        self._deleted_relation_ids.clear()

        return stats

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about storage usage and efficiency.

        Returns:
            Dictionary with storage statistics
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        mem_lines = 0
        rel_lines = 0
        mem_bytes = 0
        rel_bytes = 0

        if self.memories_path.exists():
            mem_bytes = self.memories_path.stat().st_size
            with open(self.memories_path, "r") as f:
                mem_lines = sum(1 for line in f if line.strip())

        if self.relations_path.exists():
            rel_bytes = self.relations_path.stat().st_size
            with open(self.relations_path, "r") as f:
                rel_lines = sum(1 for line in f if line.strip())

        # Calculate compaction potential
        active_memories = len(self._memories)
        active_relations = len(self._relations)

        compaction_savings = {
            "memories": mem_lines - active_memories,
            "relations": rel_lines - active_relations,
        }

        return {
            "memories": {
                "active": active_memories,
                "total_lines": mem_lines,
                "file_size_bytes": mem_bytes,
                "compaction_savings": compaction_savings["memories"],
            },
            "relations": {
                "active": active_relations,
                "total_lines": rel_lines,
                "file_size_bytes": rel_bytes,
                "compaction_savings": compaction_savings["relations"],
            },
            "should_compact": (
                compaction_savings["memories"] > 100 or compaction_savings["relations"] > 100
            ),
        }
