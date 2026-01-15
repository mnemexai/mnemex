"""SQLite-based storage interface for CortexGraph.

Provides a robust, SQL-based backend for larger datasets.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

from ..config import get_config
from ..security.permissions import secure_file
from .models import KnowledgeGraph, Memory, MemoryStatus, Relation

logger = logging.getLogger(__name__)


class SQLiteStorage:
    """SQLite-based storage backend."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """
        Initialize SQLite storage.

        Args:
            storage_path: Path to storage directory. If None, uses config default.
        """
        config = get_config()

        if storage_path is None:
            self.storage_dir = config.storage_path
        else:
            self.storage_dir = (
                storage_path if isinstance(storage_path, Path) else Path(storage_path)
            )

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Use a specific filename for the database
        self.db_path = self.storage_dir / "cortexgraph.db"
        self._conn: sqlite3.Connection | None = None
        self._connected = False

    @property
    def storage_path(self) -> Path:
        """Get current storage directory path."""
        return self.storage_dir

    @storage_path.setter
    def storage_path(self, value: Path | str) -> None:
        """Set storage directory path."""
        path = value if isinstance(value, Path) else Path(value)
        self.storage_dir = path
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / "cortexgraph.db"

    def connect(self) -> None:
        """Connect to SQLite database and initialize schema."""
        if self._connected:
            return

        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

        # Enable foreign keys
        self._conn.execute("PRAGMA foreign_keys = ON")

        self._init_schema()
        self._connected = True

        # Secure the database file
        try:
            secure_file(self.db_path)
        except Exception as e:
            # Log error but don't fail if security settings can't be applied
            # (e.g. on Windows or specific filesystems)
            logger.warning(f"Failed to secure database file: {e}")

    def _init_schema(self) -> None:
        """Initialize database schema."""
        if not self._conn:
            return

        # Memories table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                meta TEXT NOT NULL,  -- JSON
                created_at INTEGER NOT NULL,
                last_used INTEGER NOT NULL,
                use_count INTEGER NOT NULL DEFAULT 0,
                strength REAL NOT NULL DEFAULT 1.0,
                status TEXT NOT NULL,
                promoted_at INTEGER,
                promoted_to TEXT,
                embed BLOB,          -- Serialized bytes or JSON
                entities TEXT,       -- JSON list
                review_priority REAL DEFAULT 0.0,
                last_review_at INTEGER,
                review_count INTEGER DEFAULT 0,
                cross_domain_count INTEGER DEFAULT 0
            )
        """)

        # Relations table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                from_memory_id TEXT NOT NULL,
                to_memory_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL NOT NULL DEFAULT 1.0,
                created_at INTEGER NOT NULL,
                metadata TEXT NOT NULL, -- JSON
                FOREIGN KEY (from_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
                FOREIGN KEY (to_memory_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        """)

        # Indexes
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status)")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_last_used ON memories(last_used)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_memory_id)"
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_memory_id)")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type)"
        )

        self._conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
        self._connected = False

    def __enter__(self) -> "SQLiteStorage":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def save_memory(self, memory: Memory) -> None:
        """Save or update a memory."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        data = memory.to_db_dict()

        # Handle embedding serialization
        data["embed"] = json.dumps(memory.embed) if memory.embed else None

        query = """
            INSERT OR REPLACE INTO memories (
                id, content, meta, created_at, last_used, use_count, strength,
                status, promoted_at, promoted_to, embed, entities,
                review_priority, last_review_at, review_count, cross_domain_count
            ) VALUES (
                :id, :content, :meta, :created_at, :last_used, :use_count, :strength,
                :status, :promoted_at, :promoted_to, :embed, :entities,
                :review_priority, :last_review_at, :review_count, :cross_domain_count
            )
        """

        with self._conn:
            self._conn.execute(query, data)

    def save_memories_batch(self, memories: list[Memory]) -> None:
        """Save multiple memories in a batch."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        if not memories:
            return

        query = """
            INSERT OR REPLACE INTO memories (
                id, content, meta, created_at, last_used, use_count, strength,
                status, promoted_at, promoted_to, embed, entities,
                review_priority, last_review_at, review_count, cross_domain_count
            ) VALUES (
                :id, :content, :meta, :created_at, :last_used, :use_count, :strength,
                :status, :promoted_at, :promoted_to, :embed, :entities,
                :review_priority, :last_review_at, :review_count, :cross_domain_count
            )
        """

        data_list = []
        for mem in memories:
            d = mem.to_db_dict()
            d["embed"] = json.dumps(mem.embed) if mem.embed else None
            data_list.append(d)

        with self._conn:
            self._conn.executemany(query, data_list)

    def get_memory(self, memory_id: str) -> Memory | None:
        """Retrieve a memory by ID."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        cursor = self._conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Deserialize embedding if present
        row_dict = dict(row)
        if row_dict.get("embed"):
            row_dict["embed"] = json.loads(row_dict["embed"])

        return Memory.from_db_row(row_dict)

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
        """Update specific fields of a memory."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        updates = []
        params: dict[str, Any] = {"id": memory_id}

        if last_used is not None:
            updates.append("last_used = :last_used")
            params["last_used"] = last_used
        if use_count is not None:
            updates.append("use_count = :use_count")
            params["use_count"] = use_count
        if strength is not None:
            updates.append("strength = :strength")
            params["strength"] = strength
        if status is not None:
            updates.append("status = :status")
            params["status"] = status.value
        if promoted_at is not None:
            updates.append("promoted_at = :promoted_at")
            params["promoted_at"] = promoted_at
        if promoted_to is not None:
            updates.append("promoted_to = :promoted_to")
            params["promoted_to"] = promoted_to
        if review_priority is not None:
            updates.append("review_priority = :review_priority")
            params["review_priority"] = review_priority
        if last_review_at is not None:
            updates.append("last_review_at = :last_review_at")
            params["last_review_at"] = last_review_at
        if review_count is not None:
            updates.append("review_count = :review_count")
            params["review_count"] = review_count
        if cross_domain_count is not None:
            updates.append("cross_domain_count = :cross_domain_count")
            params["cross_domain_count"] = cross_domain_count

        if not updates:
            return True

        query = f"UPDATE memories SET {', '.join(updates)} WHERE id = :id"

        with self._conn:
            cursor = self._conn.execute(query, params)
            return cursor.rowcount > 0

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        with self._conn:
            cursor = self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def list_memories(
        self,
        status: MemoryStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Memory]:
        """List memories with optional filtering."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        query = "SELECT * FROM memories"
        params: list[Any] = []

        if status is not None:
            query += " WHERE status = ?"
            params.append(status.value)

        query += " ORDER BY last_used DESC"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        elif offset > 0:
            query += " LIMIT -1 OFFSET ?"
            params.append(offset)

        cursor = self._conn.execute(query, params)

        memories = []
        for row in cursor:
            row_dict = dict(row)
            if row_dict.get("embed"):
                row_dict["embed"] = json.loads(row_dict["embed"])
            memories.append(Memory.from_db_row(row_dict))

        return memories

    def search_memories(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        status: MemoryStatus | list[MemoryStatus] | None = MemoryStatus.ACTIVE,
        window_days: int | None = None,
        limit: int = 10,
    ) -> list[Memory]:
        """Search memories with filters."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        sql_query = "SELECT * FROM memories WHERE 1=1"
        params: list[Any] = []

        if status is not None:
            if isinstance(status, list):
                if status:
                    placeholders = ", ".join(["?"] * len(status))
                    sql_query += f" AND status IN ({placeholders})"
                    params.extend([s.value for s in status])
            else:
                sql_query += " AND status = ?"
                params.append(status.value)

        if window_days is not None:
            cutoff = int(time.time()) - (window_days * 86400)
            sql_query += " AND last_used >= ?"
            params.append(cutoff)

        if query:
            sql_query += " AND content LIKE ?"
            params.append(f"%{query}%")

        # SQLite doesn't have great JSON support for array containment in older versions,
        # but we can do a LIKE query for simple tag matching or fetch and filter in python.
        # For robustness, let's fetch candidates and filter in Python if tags are present,
        # unless we want to use json_each (requires json1 extension, usually available).
        # Let's try a simple LIKE approach for now as a fallback, or just filter in app.
        # Given the scale warning in JSONL, SQLite might handle more, but full scan is okay for now.

        sql_query += " ORDER BY last_used DESC"

        # If tags are present, we might need to fetch more to filter
        fetch_limit = limit * 5 if tags else limit
        sql_query += " LIMIT ?"
        params.append(fetch_limit)

        cursor = self._conn.execute(sql_query, params)

        memories = []
        for row in cursor:
            row_dict = dict(row)
            if row_dict.get("embed"):
                row_dict["embed"] = json.loads(row_dict["embed"])
            mem = Memory.from_db_row(row_dict)

            # Filter by tags if needed
            if tags:
                mem_tags = set(mem.meta.tags)
                if not any(tag in mem_tags for tag in tags):
                    continue

            memories.append(mem)
            if len(memories) >= limit:
                break

        return memories

    def count_memories(self, status: MemoryStatus | None = None) -> int:
        """Count memories."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        query = "SELECT COUNT(*) FROM memories"
        params: list[Any] = []

        if status is not None:
            query += " WHERE status = ?"
            params.append(status.value)

        cursor = self._conn.execute(query, params)
        result = cursor.fetchone()
        return int(result[0]) if result else 0

    def get_all_embeddings(self) -> dict[str, list[float]]:
        """Get all memory embeddings."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        query = "SELECT id, embed FROM memories WHERE embed IS NOT NULL AND status = ?"
        cursor = self._conn.execute(query, (MemoryStatus.ACTIVE.value,))

        embeddings = {}
        for row in cursor:
            embeddings[row["id"]] = json.loads(row["embed"])

        return embeddings

    # Relation methods

    def create_relation(self, relation: Relation) -> None:
        """Create a new relation."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        data = relation.to_db_dict()

        query = """
            INSERT OR REPLACE INTO relations (
                id, from_memory_id, to_memory_id, relation_type, strength, created_at, metadata
            ) VALUES (
                :id, :from_memory_id, :to_memory_id, :relation_type, :strength, :created_at, :metadata
            )
        """

        with self._conn:
            self._conn.execute(query, data)

    def get_relations(
        self,
        from_memory_id: str | None = None,
        to_memory_id: str | None = None,
        relation_type: str | None = None,
    ) -> list[Relation]:
        """Get relations with optional filtering."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        query = "SELECT * FROM relations WHERE 1=1"
        params: list[Any] = []

        if from_memory_id:
            query += " AND from_memory_id = ?"
            params.append(from_memory_id)

        if to_memory_id:
            query += " AND to_memory_id = ?"
            params.append(to_memory_id)

        if relation_type:
            query += " AND relation_type = ?"
            params.append(relation_type)

        cursor = self._conn.execute(query, params)
        return [Relation.from_db_row(dict(row)) for row in cursor]

    def get_all_relations(self) -> list[Relation]:
        """Get all relations."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        cursor = self._conn.execute("SELECT * FROM relations")
        return [Relation.from_db_row(dict(row)) for row in cursor]

    def delete_relation(self, relation_id: str) -> bool:
        """Delete a relation."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        with self._conn:
            cursor = self._conn.execute("DELETE FROM relations WHERE id = ?", (relation_id,))
            return cursor.rowcount > 0

    def get_knowledge_graph(
        self, status: MemoryStatus | None = MemoryStatus.ACTIVE
    ) -> KnowledgeGraph:
        """Get complete knowledge graph."""
        from ..core.decay import calculate_score

        memories = self.list_memories(status=status)
        relations = self.get_all_relations()

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

    def compact(self) -> dict[str, int]:
        """Compact database (VACUUM)."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        # Get stats before
        mem_before = self.count_memories()
        rel_before = len(self.get_all_relations())

        self._conn.execute("VACUUM")

        return {
            "memories_before": mem_before,
            "memories_after": mem_before,
            "relations_before": rel_before,
            "relations_after": rel_before,
        }

    async def save_memory_async(self, memory: Memory) -> None:
        """Async version of save_memory (wraps sync call)."""
        # SQLite is fast enough for local use that true async isn't strictly necessary,
        # but we'll wrap it to match interface.
        self.save_memory(memory)

    def get_storage_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        if not self._conn:
            raise RuntimeError("Storage not connected")

        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        mem_count = self.count_memories()
        rel_count = len(self.get_all_relations())

        return {
            "memories": {
                "active": mem_count,
                "total_lines": mem_count,  # Approximate
                "file_size_bytes": db_size,
                "compaction_savings": 0,
            },
            "relations": {
                "active": rel_count,
                "total_lines": rel_count,
                "file_size_bytes": 0,  # Included in db_size
                "compaction_savings": 0,
            },
            "should_compact": False,  # SQLite handles this mostly automatically
        }
