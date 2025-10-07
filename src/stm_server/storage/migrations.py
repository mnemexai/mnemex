"""Schema migration system for STM database."""

import sqlite3
from pathlib import Path
from typing import Callable, List, Tuple


# Current schema version
CURRENT_VERSION = 2


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version from the database."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    version = cursor.fetchone()[0]
    return version


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    """Set the schema version in the database."""
    conn.execute(f"PRAGMA user_version = {version}")
    conn.commit()


def migration_v1(conn: sqlite3.Connection) -> None:
    """Initial schema creation (v1)."""
    cursor = conn.cursor()

    # Create schema version tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at INTEGER NOT NULL
        )
    """)

    # Create main memories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            meta TEXT NOT NULL,  -- JSON string
            created_at INTEGER NOT NULL,
            last_used INTEGER NOT NULL,
            use_count INTEGER NOT NULL DEFAULT 0,
            strength REAL NOT NULL DEFAULT 1.0,
            status TEXT NOT NULL DEFAULT 'active',
            promoted_at INTEGER,
            promoted_to TEXT,
            embed BLOB  -- Optional float32 embedding vector
        )
    """)

    # Create indexes for common queries
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_last_used ON memories(last_used)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_use_count ON memories(use_count)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_status ON memories(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)"
    )

    # Record the migration
    import time

    cursor.execute(
        "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
        (1, int(time.time())),
    )

    conn.commit()


def migration_v2(conn: sqlite3.Connection) -> None:
    """Add relations table and entity support (v2)."""
    cursor = conn.cursor()

    # Create relations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relations (
            id TEXT PRIMARY KEY,
            from_memory_id TEXT NOT NULL,
            to_memory_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            strength REAL NOT NULL DEFAULT 1.0,
            created_at INTEGER NOT NULL,
            metadata TEXT,  -- JSON string
            FOREIGN KEY (from_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
            FOREIGN KEY (to_memory_id) REFERENCES memories(id) ON DELETE CASCADE
        )
    """)

    # Create indexes for relation queries
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_from_memory ON relations(from_memory_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_to_memory ON relations(to_memory_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_relation_type ON relations(relation_type)"
    )

    # Add entities column to memories (stored as JSON array)
    # SQLite doesn't support ALTER TABLE ADD COLUMN with default complex types,
    # so we'll handle this in the application layer for existing rows
    try:
        cursor.execute("ALTER TABLE memories ADD COLUMN entities TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        # Column already exists (shouldn't happen, but handle gracefully)
        pass

    # Record the migration
    import time

    cursor.execute(
        "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
        (2, int(time.time())),
    )

    conn.commit()


# Migration registry: version -> migration function
MIGRATIONS: List[Tuple[int, Callable[[sqlite3.Connection], None]]] = [
    (1, migration_v1),
    (2, migration_v2),
]


def needs_migration(conn: sqlite3.Connection) -> bool:
    """Check if the database needs migration."""
    current_version = get_schema_version(conn)
    return current_version < CURRENT_VERSION


def apply_migrations(conn: sqlite3.Connection, backup_path: Path | None = None) -> None:
    """
    Apply all pending migrations to bring the database up to date.

    Args:
        conn: SQLite connection
        backup_path: Optional path to save a backup before migration
    """
    current_version = get_schema_version(conn)

    if current_version == CURRENT_VERSION:
        return  # Already up to date

    # Create backup if requested
    if backup_path:
        import shutil

        if hasattr(conn, "execute"):
            # Get database path from connection
            cursor = conn.cursor()
            cursor.execute("PRAGMA database_list")
            db_file = cursor.fetchone()[2]  # Main database file path
            if db_file and db_file != ":memory:":
                shutil.copy2(db_file, backup_path)

    # Apply pending migrations
    for version, migration_func in MIGRATIONS:
        if version > current_version:
            try:
                migration_func(conn)
                set_schema_version(conn, version)
            except Exception as e:
                # Rollback on error
                conn.rollback()
                raise RuntimeError(
                    f"Migration to version {version} failed: {e}"
                ) from e


def initialize_database(conn: sqlite3.Connection) -> None:
    """
    Initialize a new database with the current schema.

    Args:
        conn: SQLite connection
    """
    # For a new database, just apply all migrations in order
    apply_migrations(conn)
