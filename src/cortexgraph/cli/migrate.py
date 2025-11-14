"""Migration tool for upgrading from STM to CortexGraph."""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path


def get_old_stm_path() -> Path | None:
    """Find old STM data directory."""
    old_paths = [
        Path.home() / ".stm" / "jsonl",
        Path.home() / ".stm",
    ]
    for path in old_paths:
        if path.exists():
            return path
    return None


def get_new_cortexgraph_path() -> Path:
    """Get new CortexGraph data directory (XDG-compliant)."""
    xdg_config = os.getenv("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "cortexgraph" / "jsonl"
    return Path.home() / ".config" / "cortexgraph" / "jsonl"


def migrate_data(old_path: Path, new_path: Path, dry_run: bool = False) -> bool:
    """Migrate JSONL data files from old to new location."""
    print("📦 Migrating data:")
    print(f"   From: {old_path}")
    print(f"   To:   {new_path}")

    if dry_run:
        print("   [DRY RUN - no files will be copied]")

    # Find JSONL files to migrate
    jsonl_files = list(old_path.glob("*.jsonl"))

    if not jsonl_files:
        print("   ⚠️  No .jsonl files found in old directory")
        return False

    print(f"   Found {len(jsonl_files)} file(s) to migrate:")
    for file in jsonl_files:
        print(f"      - {file.name}")

    if dry_run:
        return True

    # Create new directory if it doesn't exist
    new_path.mkdir(parents=True, exist_ok=True)

    # Copy files
    copied = 0
    for file in jsonl_files:
        dest = new_path / file.name
        if dest.exists():
            print(f"   ⚠️  Skipping {file.name} (already exists at destination)")
        else:
            shutil.copy2(file, dest)
            print(f"   ✓ Copied {file.name}")
            copied += 1

    print(f"\n✅ Migration complete: {copied} file(s) copied")
    return True


def migrate_env_file(env_path: Path, dry_run: bool = False) -> bool:
    """Migrate .env file by renaming STM_* variables to CORTEXGRAPH_*."""
    if not env_path.exists():
        return False

    print(f"\n📝 Migrating .env file: {env_path}")

    if dry_run:
        print("   [DRY RUN - file will not be modified]")

    with open(env_path) as f:
        content = f.read()

    # Find all STM_* variables
    pattern = r"\bSTM_([A-Z_]+)\b"
    matches = re.findall(pattern, content)

    if not matches:
        print("   ℹ️  No STM_* variables found")
        return False

    unique_vars = sorted(set(matches))
    print(f"   Found {len(unique_vars)} variable(s) to rename:")
    for var in unique_vars:
        print(f"      STM_{var} → CORTEXGRAPH_{var}")

    if dry_run:
        return True

    # Create backup
    backup_path = env_path.with_suffix(".env.backup")
    shutil.copy2(env_path, backup_path)
    print(f"   💾 Backup created: {backup_path}")

    # Replace all STM_* with CORTEXGRAPH_*
    new_content = re.sub(pattern, r"CORTEXGRAPH_\1", content)

    with open(env_path, "w") as f:
        f.write(new_content)

    print("   ✅ .env file updated")
    return True


def main() -> None:
    """Main migration entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate from STM to CortexGraph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what will be migrated (dry run)
  cortexgraph-migrate --dry-run

  # Migrate data only
  cortexgraph-migrate --data-only

  # Migrate data and .env file
  cortexgraph-migrate --migrate-env

  # Full migration with custom paths
  cortexgraph-migrate --old-path ~/.stm/jsonl --new-path ~/.config/cortexgraph/jsonl
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="Only migrate data files (skip .env)",
    )
    parser.add_argument(
        "--migrate-env",
        action="store_true",
        help="Also migrate .env file (rename STM_* → CORTEXGRAPH_*)",
    )
    parser.add_argument(
        "--env-path",
        type=Path,
        help="Path to .env file to migrate (default: ./.env or ~/.config/cortexgraph/.env)",
    )
    parser.add_argument(
        "--old-path",
        type=Path,
        help="Old STM data directory (default: auto-detect)",
    )
    parser.add_argument(
        "--new-path",
        type=Path,
        help="New CortexGraph data directory (default: ~/.config/cortexgraph/jsonl)",
    )

    args = parser.parse_args()

    print("🔄 CortexGraph Migration Tool")
    print("=" * 50)

    # Detect old STM path
    old_path = args.old_path or get_old_stm_path()
    if not old_path:
        print("❌ No old STM data directory found.")
        print("   Looked in:")
        print("      - ~/.stm/jsonl")
        print("      - ~/.stm")
        print("\nIf your data is elsewhere, use --old-path to specify it.")
        sys.exit(1)

    # Get new CortexGraph path
    new_path = args.new_path or get_new_cortexgraph_path()

    # Migrate data
    data_migrated = migrate_data(old_path, new_path, dry_run=args.dry_run)

    # Migrate .env if requested
    env_migrated = False
    if args.migrate_env and not args.data_only:
        env_path = args.env_path
        if not env_path:
            # Try common locations
            candidates = [
                Path(".env"),
                Path.home() / ".config" / "cortexgraph" / ".env",
            ]
            for candidate in candidates:
                if candidate.exists():
                    env_path = candidate
                    break

        if env_path:
            env_migrated = migrate_env_file(env_path, dry_run=args.dry_run)
        else:
            print("\n⚠️  No .env file found. Use --env-path to specify one.")

    # Summary
    print("\n" + "=" * 50)
    if args.dry_run:
        print("🔍 DRY RUN COMPLETE - No changes made")
        print("\nRun without --dry-run to perform the migration.")
    else:
        print("✅ MIGRATION COMPLETE")
        if data_migrated:
            print(f"\n📁 Data migrated to: {new_path}")
        if env_migrated:
            print("📝 .env file updated")

        print("\nNext steps:")
        print("1. Update your Claude Desktop config to use 'cortexgraph' instead of 'stm'")
        print("2. Verify PYTHONPATH points to the new installation")
        print("3. Restart Claude Desktop")
        print("\nSee README.md for updated configuration examples.")


if __name__ == "__main__":
    main()
