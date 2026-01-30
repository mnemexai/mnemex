"""JSONL-based storage interface for CortexGraph.

Human-readable, git-friendly storage with in-memory indexing for fast queries.

.. warning::
    This storage backend loads all memories into RAM. It is not suitable for
    datasets larger than available memory. Consider migrating to a database
    backend for large-scale usage.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from ..config import get_config
from ..security.permissions import secure_file
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
            # Default to configured storage_path (human-readable JSONL)
            self.storage_dir = config.storage_path
        else:
            self.storage_dir = (
                storage_path if isinstance(storage_path, Path) else Path(storage_path)
            )

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.memories_path = self.storage_dir / config.stm_memories_filename
        self.relations_path = self.storage_dir / config.stm_relations_filename

        # In-memory indexes
        self._memories: dict[str, Memory] = {}
        self._relations: dict[str, Relation] = {}
        self._deleted_memory_ids: set[str] = set()
        self._deleted_relation_ids: set[str] = set()

        # Performance optimization: tag index for faster filtering
        self._tag_index: dict[str, set[str]] = {}
        self._last_indexed_memory_count = 0

        # Track if connected
        self._connected = False

    @property
    def storage_path(self) -> Path:
        """Get current storage directory path.

        Exposed for tests to redirect the global storage instance before connect().
        """
        return self.storage_dir

    @storage_path.setter
    def storage_path(self, value: Path | str) -> None:
        """Set storage directory path and update file paths.

        Can be used prior to connect() to point the global instance at a temp dir.
        """
        path = value if isinstance(value, Path) else Path(value)
        self.storage_dir = path
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        config = get_config()
        self.memories_path = self.storage_dir / config.stm_memories_filename
        self.relations_path = self.storage_dir / config.stm_relations_filename

    @property
    def memories(self) -> dict[str, "Memory"]:
        """Access to in-memory memories dict.

        Used by consolidation agents for direct iteration.
        For filtered queries, prefer list_memories() or search_memories().
        """
        return self._memories

    @memories.setter
    def memories(self, value: dict[str, "Memory"]) -> None:
        """Set memories dict (primarily for testing)."""
        self._memories = value

    @property
    def relations(self) -> dict[str, "Relation"]:
        """Access to in-memory relations dict.

        Used by consolidation agents for direct iteration.
        For filtered queries, prefer get_relations().
        """
        return self._relations

    @relations.setter
    def relations(self, value: dict[str, "Relation"]) -> None:
        """Set relations dict (primarily for testing)."""
        self._relations = value

    def connect(self) -> None:
        """Load JSONL files into memory and build indexes."""
        if self._connected:
            return

        # Load memories
        if self.memories_path.exists():
            with open(self.memories_path) as f:
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
            with open(self.relations_path) as f:
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
        self._rebuild_tag_index()

    def _rebuild_tag_index(self) -> None:
        """Rebuild the tag index for faster filtering."""
        self._tag_index.clear()
        for memory_id, memory in self._memories.items():
            for tag in memory.meta.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(memory_id)
        self._last_indexed_memory_count = len(self._memories)

    def _update_tag_index(self, memory: Memory, old_memory: Memory | None = None) -> None:
        """Update tag index for a single memory."""
        old_tags = set(old_memory.meta.tags) if old_memory else set()
        new_tags = set(memory.meta.tags)

        # Remove from tags that are no longer present
        for tag in old_tags - new_tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(memory.id)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

        # Add to new tags
        for tag in new_tags - old_tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(memory.id)

    def _ensure_tag_index_current(self) -> None:
        """Ensure tag index is current (rebuild if needed)."""
        if len(self._memories) != self._last_indexed_memory_count:
            self._rebuild_tag_index()

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
        """Append memory to JSONL file and secure permissions."""
        file_created = not self.memories_path.exists()

        # Use buffered writing for better performance
        with open(self.memories_path, "a", buffering=8192) as f:
            # Convert to JSON-serializable dict
            data = memory.model_dump(mode="json")
            f.write(json.dumps(data) + "\n")

        # Secure file permissions if newly created
        if file_created:
            try:
                secure_file(self.memories_path)
            except Exception:
                # Don't fail if permissions can't be set (log warning in production)
                pass

    def _append_relation(self, relation: Relation) -> None:
        """Append relation to JSONL file and secure permissions."""
        file_created = not self.relations_path.exists()

        # Use buffered writing for better performance
        with open(self.relations_path, "a", buffering=8192) as f:
            data = relation.model_dump(mode="json")
            f.write(json.dumps(data) + "\n")

        # Secure file permissions if newly created
        if file_created:
            try:
                secure_file(self.relations_path)
            except Exception:
                # Don't fail if permissions can't be set (log warning in production)
                pass

    def _append_deletion_marker(self, memory_id: str, is_relation: bool = False) -> None:
        """Append a deletion marker to JSONL file and secure permissions."""
        marker = {"id": memory_id, "_deleted": True}

        if is_relation:
            file_created = not self.relations_path.exists()
            with open(self.relations_path, "a") as f:
                f.write(json.dumps(marker) + "\n")
            if file_created:
                try:
                    secure_file(self.relations_path)
                except Exception:
                    pass
        else:
            file_created = not self.memories_path.exists()
            with open(self.memories_path, "a") as f:
                f.write(json.dumps(marker) + "\n")
            if file_created:
                try:
                    secure_file(self.memories_path)
                except Exception:
                    pass

    def save_memory(self, memory: Memory) -> None:
        """
        Save or update a memory.

        Args:
            memory: Memory object to save
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        # Update in-memory index
        old_memory = self._memories.get(memory.id)
        self._memories[memory.id] = memory
        # Update tag index
        self._update_tag_index(memory, old_memory)

        # Append to JSONL file
        self._append_memory(memory)

    def save_memories_batch(self, memories: list[Memory]) -> None:
        """
        Save multiple memories in a single batch operation for better performance.

        Args:
            memories: List of Memory objects to save
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        if not memories:
            return

        # Update in-memory indexes
        for memory in memories:
            self._memories[memory.id] = memory

        # Batch write to JSONL file
        file_created = not self.memories_path.exists()
        with open(self.memories_path, "a", buffering=8192) as f:
            for memory in memories:
                data = memory.model_dump(mode="json")
                f.write(json.dumps(data) + "\n")

        # Secure file permissions if newly created
        if file_created:
            try:
                secure_file(self.memories_path)
            except Exception as e:
                logging.warning(f"Failed to secure file '{self.memories_path}': {e}")

    def get_memory(self, memory_id: str) -> Memory | None:
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
        last_used: int | None = None,
        use_count: int | None = None,
        strength: float | None = None,
        status: MemoryStatus | None = None,
        promoted_at: int | None = None,
        promoted_to: str | None = None,
        review_priority: float | None = None,
        last_review_at: int | None = None,
        review_count: int | None = None,
        cross_domain_count: int | None = None,
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
            review_priority: New review priority (0.0-1.0)
            last_review_at: New last review timestamp
            review_count: New review count
            cross_domain_count: New cross-domain usage count

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
        if review_priority is not None:
            memory.review_priority = review_priority
        if last_review_at is not None:
            memory.last_review_at = last_review_at
        if review_count is not None:
            memory.review_count = review_count
        if cross_domain_count is not None:
            memory.cross_domain_count = cross_domain_count

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

    def delete_memories_batch(self, memory_ids: list[str]) -> int:
        """
        Delete multiple memories in a single batch operation for better performance.

        Args:
            memory_ids: List of memory IDs to delete

        Returns:
            Number of memories actually deleted (skips non-existent IDs)
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        if not memory_ids:
            return 0

        # Filter to only existing memories
        existing_ids = [mid for mid in memory_ids if mid in self._memories]

        if not existing_ids:
            return 0

        # Remove from in-memory index
        for memory_id in existing_ids:
            del self._memories[memory_id]
            self._deleted_memory_ids.add(memory_id)

        # Batch write deletion markers
        file_created = not self.memories_path.exists()
        with open(self.memories_path, "a", buffering=8192) as f:
            for memory_id in existing_ids:
                marker = {"id": memory_id, "_deleted": True}
                f.write(json.dumps(marker) + "\n")

        # Secure file permissions if newly created
        if file_created:
            try:
                from ..security.permissions import secure_file

                secure_file(self.memories_path)
            except Exception as e:
                logging.warning(f"Failed to secure file '{self.memories_path}': {e}")

        return len(existing_ids)

    def list_memories(
        self,
        status: MemoryStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Memory]:
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

    def count_memories(self, status: MemoryStatus | None = None) -> int:
        """
        Count memories with optional filtering.
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        if status is None:
            return len(self._memories)

        return sum(1 for m in self._memories.values() if m.status == status)

    def search_memories(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        status: MemoryStatus | list[MemoryStatus] | None = MemoryStatus.ACTIVE,
        window_days: int | None = None,
        limit: int = 10,
    ) -> list[Memory]:
        """
        Search memories with filters.

        Args:
            query: Text to search for in content
            tags: Filter by tags (any match)
            status: Filter by status (single, list, or None)
            window_days: Only return memories from last N days
            limit: Maximum results

        Returns:
            List of Memory objects
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        self._ensure_tag_index_current()

        # Start with all memories or tag-filtered subset
        if tags:
            # Use tag index for faster filtering
            memory_ids = set()
            for tag in tags:
                if tag in self._tag_index:
                    memory_ids.update(self._tag_index[tag])
            memories = [self._memories[mid] for mid in memory_ids if mid in self._memories]
        else:
            memories = list(self._memories.values())

        # Filter by status
        if status is not None:
            if isinstance(status, list):
                status_values = set(status)
                memories = [m for m in memories if m.status in status_values]
            else:
                memories = [m for m in memories if m.status == status]

        # Filter by time window
        if window_days is not None:
            cutoff = int(time.time()) - (window_days * 86400)
            memories = [m for m in memories if m.last_used >= cutoff]

        # Filter by query
        if query:
            query = query.lower()
            memories = [m for m in memories if query in m.content.lower()]

        # Sort by last_used DESC
        memories.sort(key=lambda m: m.last_used, reverse=True)

        if limit is not None:
            return memories[:limit]
        return memories

    def get_all_embeddings(self) -> dict[str, list[float]]:
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

        # Validate foreign keys (parity with SQLite)
        if relation.from_memory_id not in self._memories:
            raise ValueError(f"Source memory {relation.from_memory_id} does not exist")
        if relation.to_memory_id not in self._memories:
            raise ValueError(f"Target memory {relation.to_memory_id} does not exist")

        # Update in-memory index
        self._relations[relation.id] = relation

        # Append to JSONL file
        self._append_relation(relation)

    def create_relations_batch(self, relations: list[Relation]) -> None:
        """
        Create multiple relations in a single batch operation for better performance.

        Validates all foreign keys before creating any relations.

        Args:
            relations: List of Relation objects to create

        Raises:
            ValueError: If any relation references non-existent memories
        """
        if not self._connected:
            raise RuntimeError("Storage not connected")

        if not relations:
            return

        # Validate all foreign keys before making any changes
        for relation in relations:
            if relation.from_memory_id not in self._memories:
                raise ValueError(f"Source memory {relation.from_memory_id} does not exist")
            if relation.to_memory_id not in self._memories:
                raise ValueError(f"Target memory {relation.to_memory_id} does not exist")

        # Update in-memory index
        for relation in relations:
            self._relations[relation.id] = relation

        # Batch write to JSONL file
        file_created = not self.relations_path.exists()
        with open(self.relations_path, "a", buffering=8192) as f:
            for relation in relations:
                data = relation.model_dump(mode="json")
                f.write(json.dumps(data) + "\n")

        # Secure file permissions if newly created
        if file_created:
            try:
                from ..security.permissions import secure_file

                secure_file(self.relations_path)
            except Exception as e:
                logging.warning(f"Failed to secure file '{self.relations_path}': {e}")

    def get_relations(
        self,
        from_memory_id: str | None = None,
        to_memory_id: str | None = None,
        relation_type: str | None = None,
    ) -> list[Relation]:
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

    def get_all_relations(self) -> list[Relation]:
        """
        Get all relations in storage.

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
        self, status: MemoryStatus | None = MemoryStatus.ACTIVE
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

    def compact(self) -> dict[str, int]:
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
            with open(self.memories_path) as f:
                stats["memories_before"] = sum(1 for line in f if line.strip())

        if self.relations_path.exists():
            with open(self.relations_path) as f:
                stats["relations_before"] = sum(1 for line in f if line.strip())

        # Rewrite memories file
        temp_memories = self.memories_path.with_suffix(".jsonl.tmp")
        with open(temp_memories, "w") as f:
            for memory in self._memories.values():
                data = memory.model_dump(mode="json")
                f.write(json.dumps(data) + "\n")

        # Secure temp file before replacing
        try:
            secure_file(temp_memories)
        except Exception:
            pass

        temp_memories.replace(self.memories_path)

        # Rewrite relations file
        temp_relations = self.relations_path.with_suffix(".jsonl.tmp")
        with open(temp_relations, "w") as f:
            for relation in self._relations.values():
                data = relation.model_dump(mode="json")
                f.write(json.dumps(data) + "\n")

        # Secure temp file before replacing
        try:
            secure_file(temp_relations)
        except Exception:
            pass

        temp_relations.replace(self.relations_path)

        # Clear deletion tracking
        self._deleted_memory_ids.clear()
        self._deleted_relation_ids.clear()

        return stats

    # Async methods for better I/O performance
    async def save_memory_async(self, memory: Memory) -> None:
        """Async version of save_memory for better I/O performance."""
        if not self._connected:
            raise RuntimeError("Storage not connected")

        # Update in-memory index
        old_memory = self._memories.get(memory.id)
        self._memories[memory.id] = memory
        # Update tag index
        self._update_tag_index(memory, old_memory)

        # Async append to JSONL file
        await self._append_memory_async(memory)

    async def _append_memory_async(self, memory: Memory) -> None:
        """Async append memory to JSONL file."""
        file_created = not self.memories_path.exists()

        # Use asyncio for file I/O
        loop = asyncio.get_event_loop()
        data = memory.model_dump(mode="json")
        content = json.dumps(data) + "\n"

        # This is an I/O-bound operation, run it in a thread pool to avoid blocking the event loop.
        # The 'a' mode correctly handles file creation and appends atomically.
        def _sync_append() -> None:
            with open(self.memories_path, "a", buffering=8192, encoding="utf-8") as f:
                f.write(content)

        await loop.run_in_executor(None, _sync_append)

        # Secure file permissions if newly created
        if file_created:
            try:
                secure_file(self.memories_path)
            except Exception as e:
                logging.error(f"Failed to secure file {self.memories_path}: {e}", exc_info=True)

    def get_storage_stats(self) -> dict[str, Any]:
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
            with open(self.memories_path) as f:
                mem_lines = sum(1 for line in f if line.strip())

        if self.relations_path.exists():
            rel_bytes = self.relations_path.stat().st_size
            with open(self.relations_path) as f:
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
