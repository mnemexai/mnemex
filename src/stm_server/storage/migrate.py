"""Migration utilities for STM storage.

Convert between different storage backends (SQLite, JSONL).
"""

import sys
from pathlib import Path
from typing import Optional

from .database import Database
from .jsonl_storage import JSONLStorage


class MigrationError(Exception):
    """Exception raised during migration."""

    pass


def migrate_sqlite_to_jsonl(
    sqlite_path: Optional[Path] = None,
    jsonl_path: Optional[Path] = None,
    *,
    dry_run: bool = False,
    verbose: bool = True,
) -> dict:
    """
    Migrate data from SQLite database to JSONL storage.

    Args:
        sqlite_path: Path to SQLite database. If None, uses config default.
        jsonl_path: Path to JSONL storage directory. If None, uses config default.
        dry_run: If True, don't write to JSONL, just report what would be migrated
        verbose: If True, print progress information

    Returns:
        Dictionary with migration statistics

    Raises:
        MigrationError: If migration fails
    """
    stats = {
        "memories_migrated": 0,
        "relations_migrated": 0,
        "errors": [],
    }

    try:
        # Open SQLite database
        if verbose:
            print(f"Opening SQLite database: {sqlite_path or '(default)'}")

        db = Database(db_path=sqlite_path)
        db.connect()

        # Get all data from SQLite
        if verbose:
            print("Reading memories from SQLite...")

        memories = db.list_memories(status=None)  # Get all memories regardless of status
        stats["memories_migrated"] = len(memories)

        if verbose:
            print(f"Found {len(memories)} memories")
            print("Reading relations from SQLite...")

        relations = db.get_all_relations()
        stats["relations_migrated"] = len(relations)

        if verbose:
            print(f"Found {len(relations)} relations")

        db.close()

        if dry_run:
            if verbose:
                print("\n[DRY RUN] Would migrate:")
                print(f"  - {stats['memories_migrated']} memories")
                print(f"  - {stats['relations_migrated']} relations")
            return stats

        # Write to JSONL storage
        if verbose:
            print(f"\nWriting to JSONL storage: {jsonl_path or '(default)'}")

        storage = JSONLStorage(storage_path=jsonl_path)
        storage.connect()

        # Migrate memories
        if verbose:
            print("Migrating memories...")

        for i, memory in enumerate(memories, 1):
            try:
                storage.save_memory(memory)
                if verbose and i % 100 == 0:
                    print(f"  ... {i}/{len(memories)} memories")
            except Exception as e:
                error_msg = f"Failed to migrate memory {memory.id}: {e}"
                stats["errors"].append(error_msg)
                if verbose:
                    print(f"  ERROR: {error_msg}")

        # Migrate relations
        if verbose:
            print("Migrating relations...")

        for i, relation in enumerate(relations, 1):
            try:
                storage.create_relation(relation)
                if verbose and i % 100 == 0:
                    print(f"  ... {i}/{len(relations)} relations")
            except Exception as e:
                error_msg = f"Failed to migrate relation {relation.id}: {e}"
                stats["errors"].append(error_msg)
                if verbose:
                    print(f"  ERROR: {error_msg}")

        storage.close()

        if verbose:
            print("\n✓ Migration complete!")
            print(f"  Migrated: {stats['memories_migrated']} memories, {stats['relations_migrated']} relations")
            if stats["errors"]:
                print(f"  Errors: {len(stats['errors'])}")

        return stats

    except Exception as e:
        raise MigrationError(f"Migration failed: {e}") from e


def verify_migration(
    sqlite_path: Optional[Path] = None,
    jsonl_path: Optional[Path] = None,
    *,
    verbose: bool = True,
) -> bool:
    """
    Verify that JSONL storage matches SQLite database.

    Args:
        sqlite_path: Path to SQLite database
        jsonl_path: Path to JSONL storage directory
        verbose: If True, print verification details

    Returns:
        True if verification passes, False otherwise
    """
    try:
        # Open both storages
        db = Database(db_path=sqlite_path)
        db.connect()

        storage = JSONLStorage(storage_path=jsonl_path)
        storage.connect()

        # Compare counts
        db_mem_count = db.count_memories(status=None)
        jsonl_mem_count = storage.count_memories(status=None)

        db_rel_count = len(db.get_all_relations())
        jsonl_rel_count = len(storage.get_all_relations())

        if verbose:
            print("Verification:")
            print(f"  Memories: SQLite={db_mem_count}, JSONL={jsonl_mem_count}")
            print(f"  Relations: SQLite={db_rel_count}, JSONL={jsonl_rel_count}")

        # Check counts match
        if db_mem_count != jsonl_mem_count:
            if verbose:
                print(f"  ✗ Memory count mismatch!")
            return False

        if db_rel_count != jsonl_rel_count:
            if verbose:
                print(f"  ✗ Relation count mismatch!")
            return False

        # Sample check: verify a few random memories
        db_memories = db.list_memories(status=None, limit=10)

        for db_mem in db_memories:
            jsonl_mem = storage.get_memory(db_mem.id)
            if jsonl_mem is None:
                if verbose:
                    print(f"  ✗ Memory {db_mem.id} not found in JSONL")
                return False

            # Check key fields match
            if db_mem.content != jsonl_mem.content:
                if verbose:
                    print(f"  ✗ Memory {db_mem.id} content mismatch")
                return False

            if db_mem.use_count != jsonl_mem.use_count:
                if verbose:
                    print(f"  ✗ Memory {db_mem.id} use_count mismatch")
                return False

        db.close()
        storage.close()

        if verbose:
            print("  ✓ Verification passed!")

        return True

    except Exception as e:
        if verbose:
            print(f"  ✗ Verification failed: {e}")
        return False


def main() -> int:
    """CLI entry point for migration tool."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate STM storage from SQLite to JSONL")
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        help="Path to SQLite database (default: from config)",
    )
    parser.add_argument(
        "--jsonl-path",
        type=Path,
        help="Path to JSONL storage directory (default: from config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without writing",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration after completion",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )

    args = parser.parse_args()

    try:
        # Run migration
        stats = migrate_sqlite_to_jsonl(
            sqlite_path=args.sqlite_path,
            jsonl_path=args.jsonl_path,
            dry_run=args.dry_run,
            verbose=not args.quiet,
        )

        # Verify if requested
        if args.verify and not args.dry_run:
            if not verify_migration(
                sqlite_path=args.sqlite_path,
                jsonl_path=args.jsonl_path,
                verbose=not args.quiet,
            ):
                print("\n✗ Verification failed!", file=sys.stderr)
                return 1

        # Report errors
        if stats["errors"]:
            print(f"\nWarning: {len(stats['errors'])} errors occurred during migration")
            return 1

        return 0

    except MigrationError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nMigration cancelled", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
