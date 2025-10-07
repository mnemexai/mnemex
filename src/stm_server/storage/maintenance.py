"""Maintenance CLI for JSONL storage.

Expose storage statistics and compaction operations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .jsonl_storage import JSONLStorage


def cmd_stats(storage_path: Path | None) -> int:
    storage = JSONLStorage(storage_path=storage_path)
    storage.connect()
    stats = storage.get_storage_stats()
    print(json.dumps(stats, indent=2))
    return 0


def cmd_compact(storage_path: Path | None, *, quiet: bool = False) -> int:
    storage = JSONLStorage(storage_path=storage_path)
    storage.connect()
    before = storage.get_storage_stats()
    result = storage.compact()
    after = storage.get_storage_stats()
    if quiet:
        print(json.dumps({"result": result}, indent=2))
    else:
        print("Before:")
        print(json.dumps(before, indent=2))
        print("\nCompaction:")
        print(json.dumps(result, indent=2))
        print("\nAfter:")
        print(json.dumps(after, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="JSONL storage maintenance")
    parser.add_argument(
        "--storage-path",
        type=Path,
        help="Override storage path (defaults to STM_STORAGE_PATH or config)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_stats = sub.add_parser("stats", help="Show storage stats")
    p_stats.set_defaults(func=lambda args: cmd_stats(args.storage_path))

    p_compact = sub.add_parser("compact", help="Compact JSONL files")
    p_compact.add_argument("--quiet", action="store_true", help="Only print compaction result")
    p_compact.set_defaults(func=lambda args: cmd_compact(args.storage_path, quiet=args.quiet))

    args = parser.parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
