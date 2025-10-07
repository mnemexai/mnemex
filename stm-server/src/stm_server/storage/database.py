"""Database interface for STM server."""

import json
import sqlite3
import struct
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import get_config
from .migrations import apply_migrations, get_schema_version, initialize_database
from .models import KnowledgeGraph, Memory, MemoryStatus, Relation


class Database:
    """SQLite database interface for STM memories."""

    def __init__(self, db_path: Path | None = None) -> None:
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. If None, uses config default.
        """
        config = get_config()
        self.db_path = db_path or config.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Connect to the database and ensure schema is up to date."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries

        # Initialize or migrate schema
        if get_schema_version(self.conn) == 0:
            initialize_database(self.conn)
        else:
            apply_migrations(self.conn)

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "Database":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def _serialize_embed(self, embed: List[float] | None) -> bytes | None:
        """Serialize embedding vector to bytes (float32)."""
        if embed is None:
            return None
        return struct.pack(f"{len(embed)}f", *embed)

    def _deserialize_embed(self, data: bytes | None) -> List[float] | None:
        """Deserialize embedding vector from bytes."""
        if data is None:
            return None
        count = len(data) // 4  # 4 bytes per float32
        return list(struct.unpack(f"{count}f", data))

    def save_memory(self, memory: Memory) -> None:
        """
        Save or update a memory in the database.

        Args:
            memory: Memory object to save
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        embed_bytes = self._serialize_embed(memory.embed)

        self.conn.execute(
            """
            INSERT OR REPLACE INTO memories
            (id, content, meta, created_at, last_used, use_count, strength,
             status, promoted_at, promoted_to, embed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory.id,
                memory.content,
                memory.meta.model_dump_json(),
                memory.created_at,
                memory.last_used,
                memory.use_count,
                memory.strength,
                memory.status.value,
                memory.promoted_at,
                memory.promoted_to,
                embed_bytes,
            ),
        )
        self.conn.commit()

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        Retrieve a memory by ID.

        Args:
            memory_id: ID of the memory to retrieve

        Returns:
            Memory object or None if not found
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        row_dict = dict(row)
        row_dict["embed"] = self._deserialize_embed(row_dict.get("embed"))
        return Memory.from_db_row(row_dict)

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
        if not self.conn:
            raise RuntimeError("Database not connected")

        updates = []
        params: List[Any] = []

        if last_used is not None:
            updates.append("last_used = ?")
            params.append(last_used)
        if use_count is not None:
            updates.append("use_count = ?")
            params.append(use_count)
        if strength is not None:
            updates.append("strength = ?")
            params.append(strength)
        if status is not None:
            updates.append("status = ?")
            params.append(status.value)
        if promoted_at is not None:
            updates.append("promoted_at = ?")
            params.append(promoted_at)
        if promoted_to is not None:
            updates.append("promoted_to = ?")
            params.append(promoted_to)

        if not updates:
            return False

        params.append(memory_id)
        query = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"

        cursor = self.conn.execute(query, params)
        self.conn.commit()

        return cursor.rowcount > 0

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from the database.

        Args:
            memory_id: ID of the memory to delete

        Returns:
            True if memory was deleted, False if not found
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()

        return cursor.rowcount > 0

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
        if not self.conn:
            raise RuntimeError("Database not connected")

        query = "SELECT * FROM memories"
        params: List[Any] = []

        if status is not None:
            query += " WHERE status = ?"
            params.append(status.value)

        query += " ORDER BY last_used DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            query += " OFFSET ?"
            params.append(offset)

        cursor = self.conn.execute(query, params)
        memories = []

        for row in cursor:
            row_dict = dict(row)
            row_dict["embed"] = self._deserialize_embed(row_dict.get("embed"))
            memories.append(Memory.from_db_row(row_dict))

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
        if not self.conn:
            raise RuntimeError("Database not connected")

        query = "SELECT * FROM memories WHERE 1=1"
        params: List[Any] = []

        if status is not None:
            query += " AND status = ?"
            params.append(status.value)

        if window_days is not None:
            cutoff = int(time.time()) - (window_days * 86400)
            query += " AND last_used >= ?"
            params.append(cutoff)

        # Tag filtering requires JSON extraction
        if tags:
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("meta LIKE ?")
                params.append(f'%"{tag}"%')
            query += f" AND ({' OR '.join(tag_conditions)})"

        query += " ORDER BY last_used DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)
        memories = []

        for row in cursor:
            row_dict = dict(row)
            row_dict["embed"] = self._deserialize_embed(row_dict.get("embed"))
            memories.append(Memory.from_db_row(row_dict))

        return memories

    def count_memories(self, status: Optional[MemoryStatus] = None) -> int:
        """
        Count memories with optional status filter.

        Args:
            status: Filter by memory status

        Returns:
            Number of memories
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        if status is None:
            cursor = self.conn.execute("SELECT COUNT(*) FROM memories")
        else:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM memories WHERE status = ?", (status.value,)
            )

        return cursor.fetchone()[0]

    def get_all_embeddings(self) -> Dict[str, List[float]]:
        """
        Get all memory embeddings for clustering/similarity search.

        Returns:
            Dictionary mapping memory IDs to embedding vectors
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute(
            "SELECT id, embed FROM memories WHERE embed IS NOT NULL AND status = 'active'"
        )

        embeddings = {}
        for row in cursor:
            memory_id = row[0]
            embed_bytes = row[1]
            if embed_bytes:
                embeddings[memory_id] = self._deserialize_embed(embed_bytes)

        return embeddings

    # Relation methods

    def create_relation(self, relation: Relation) -> None:
        """
        Create a new relation between memories.

        Args:
            relation: Relation object to create
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        self.conn.execute(
            """
            INSERT OR REPLACE INTO relations
            (id, from_memory_id, to_memory_id, relation_type, strength, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                relation.id,
                relation.from_memory_id,
                relation.to_memory_id,
                relation.relation_type,
                relation.strength,
                relation.created_at,
                relation.to_db_dict()["metadata"],
            ),
        )
        self.conn.commit()

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
        if not self.conn:
            raise RuntimeError("Database not connected")

        query = "SELECT * FROM relations WHERE 1=1"
        params: List[Any] = []

        if from_memory_id:
            query += " AND from_memory_id = ?"
            params.append(from_memory_id)

        if to_memory_id:
            query += " AND to_memory_id = ?"
            params.append(to_memory_id)

        if relation_type:
            query += " AND relation_type = ?"
            params.append(relation_type)

        cursor = self.conn.execute(query, params)
        relations = []

        for row in cursor:
            row_dict = dict(row)
            relations.append(Relation.from_db_row(row_dict))

        return relations

    def get_all_relations(self) -> List[Relation]:
        """
        Get all relations in the database.

        Returns:
            List of all Relation objects
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("SELECT * FROM relations")
        relations = []

        for row in cursor:
            row_dict = dict(row)
            relations.append(Relation.from_db_row(row_dict))

        return relations

    def delete_relation(self, relation_id: str) -> bool:
        """
        Delete a relation.

        Args:
            relation_id: ID of relation to delete

        Returns:
            True if deleted, False if not found
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("DELETE FROM relations WHERE id = ?", (relation_id,))
        self.conn.commit()

        return cursor.rowcount > 0

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
        import time
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
