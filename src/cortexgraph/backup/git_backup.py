"""Git integration for automated backups of STM storage.

Provides automatic commits, snapshots, and restore functionality.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from git import Repo
from git.exc import InvalidGitRepositoryError


class GitBackup:
    """Git-based backup manager for STM storage."""

    def __init__(self, storage_dir: Path, auto_commit: bool = True):
        """
        Initialize Git backup manager.

        Args:
            storage_dir: Directory containing JSONL storage files
            auto_commit: If True, enable automatic commits
        """
        self.storage_dir = storage_dir
        self.auto_commit = auto_commit
        self.repo: Repo | None = None

        # Tracking for auto-commit
        self._last_commit_time = 0
        self._commit_interval = 3600  # Default: 1 hour in seconds
        self._pending_changes = False

    def initialize(self) -> None:
        """
        Initialize Git repository in storage directory.

        Creates a new repo if one doesn't exist.
        """
        try:
            # Try to open existing repository
            self.repo = Repo(self.storage_dir)
        except InvalidGitRepositoryError:
            # Initialize new repository
            self.repo = Repo.init(self.storage_dir)

            # Create initial commit
            self._create_commit("Initial STM storage", initial=True)

    def set_commit_interval(self, seconds: int) -> None:
        """
        Set the interval for automatic commits.

        Args:
            seconds: Interval in seconds between auto-commits
        """
        self._commit_interval = seconds

    def mark_dirty(self) -> None:
        """Mark that changes have been made (for auto-commit tracking)."""
        self._pending_changes = True

    def _create_commit(self, message: str, initial: bool = False) -> str:
        """
        Create a git commit with all changes.

        Args:
            message: Commit message
            initial: If True, this is the initial commit

        Returns:
            Commit SHA

        Raises:
            GitCommandError: If commit fails
        """
        if self.repo is None:
            raise RuntimeError("Git repository not initialized")

        # Add all files
        if initial:
            # For initial commit, add .gitignore
            gitignore_path = self.storage_dir / ".gitignore"
            if not gitignore_path.exists():
                with open(gitignore_path, "w") as f:
                    f.write("# Python\n__pycache__/\n*.py[cod]\n*$py.class\n\n")
                    f.write("# Temp files\n*.tmp\n*.swp\n.DS_Store\n")

        # Stage all changes
        self.repo.index.add("*")

        # Check if there are changes to commit
        if not self.repo.is_dirty() and not initial:
            # No changes to commit
            return self.repo.head.commit.hexsha

        # Create commit
        commit = self.repo.index.commit(message)

        # Update tracking
        self._last_commit_time = int(time.time())
        self._pending_changes = False

        return commit.hexsha

    def create_snapshot(self, message: str | None = None) -> str:
        """
        Create a snapshot (commit) of current storage state.

        Args:
            message: Custom commit message (default: auto-generated with timestamp)

        Returns:
            Commit SHA
        """
        if self.repo is None:
            raise RuntimeError("Git repository not initialized")

        if message is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"STM snapshot - {timestamp}"

        return self._create_commit(message)

    def auto_commit_if_needed(self) -> str | None:
        """
        Perform automatic commit if interval has elapsed and there are changes.

        Returns:
            Commit SHA if commit was created, None otherwise
        """
        if not self.auto_commit:
            return None

        if not self._pending_changes:
            return None

        now = int(time.time())
        if now - self._last_commit_time < self._commit_interval:
            return None

        # Time to commit
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Auto-commit - {timestamp}"

        return self._create_commit(message)

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Get commit history.

        Args:
            limit: Maximum number of commits to return

        Returns:
            List of commit information dictionaries
        """
        if self.repo is None:
            raise RuntimeError("Git repository not initialized")

        commits = []
        for commit in list(self.repo.iter_commits())[:limit]:
            commits.append(
                {
                    "sha": commit.hexsha,
                    "short_sha": commit.hexsha[:7],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "timestamp": commit.committed_date,
                    "datetime": datetime.fromtimestamp(commit.committed_date).isoformat(),
                }
            )

        return commits

    def restore_snapshot(self, commit_sha: str) -> None:
        """
        Restore storage to a specific commit.

        Args:
            commit_sha: SHA of commit to restore to

        Raises:
            GitCommandError: If restore fails
        """
        if self.repo is None:
            raise RuntimeError("Git repository not initialized")

        # Check for uncommitted changes
        if self.repo.is_dirty():
            raise RuntimeError("Repository has uncommitted changes. Commit or stash them first.")

        # Reset to the specified commit
        self.repo.git.reset("--hard", commit_sha)

    def get_status(self) -> dict[str, Any]:
        """
        Get repository status.

        Returns:
            Dictionary with status information
        """
        if self.repo is None:
            return {
                "initialized": False,
                "error": "Repository not initialized",
            }

        try:
            return {
                "initialized": True,
                "dirty": self.repo.is_dirty(),
                "untracked_files": self.repo.untracked_files,
                "current_branch": self.repo.active_branch.name,
                "total_commits": len(list(self.repo.iter_commits())),
                "last_commit": {
                    "sha": self.repo.head.commit.hexsha[:7],
                    "message": self.repo.head.commit.message.strip(),
                    "timestamp": self.repo.head.commit.committed_date,
                }
                if self.repo.head.is_valid()
                else None,
                "auto_commit_enabled": self.auto_commit,
                "pending_changes": self._pending_changes,
                "time_until_next_commit": max(
                    0, self._commit_interval - (int(time.time()) - self._last_commit_time)
                )
                if self.auto_commit
                else None,
            }
        except Exception as e:
            return {
                "initialized": True,
                "error": str(e),
            }

    def create_branch(self, branch_name: str) -> None:
        """
        Create a new branch.

        Args:
            branch_name: Name of the branch to create
        """
        if self.repo is None:
            raise RuntimeError("Git repository not initialized")

        self.repo.create_head(branch_name)

    def switch_branch(self, branch_name: str) -> None:
        """
        Switch to a different branch.

        Args:
            branch_name: Name of the branch to switch to

        Raises:
            GitCommandError: If branch doesn't exist or switch fails
        """
        if self.repo is None:
            raise RuntimeError("Git repository not initialized")

        self.repo.git.checkout(branch_name)

    def diff_commits(self, commit_sha_a: str, commit_sha_b: str) -> str:
        """
        Get diff between two commits.

        Args:
            commit_sha_a: First commit SHA
            commit_sha_b: Second commit SHA

        Returns:
            Diff output as string
        """
        if self.repo is None:
            raise RuntimeError("Git repository not initialized")

        # GitPython returns a Git object response; ensure string type for API contract
        return str(self.repo.git.diff(commit_sha_a, commit_sha_b))

    def get_stats(self) -> dict[str, Any]:
        """
        Get repository statistics.

        Returns:
            Dictionary with statistics
        """
        if self.repo is None:
            return {"error": "Repository not initialized"}

        try:
            commits = list(self.repo.iter_commits())

            # Calculate stats
            total_additions = 0
            total_deletions = 0

            for commit in commits:
                stats = commit.stats.total
                total_additions += stats.get("insertions", 0)
                total_deletions += stats.get("deletions", 0)

            return {
                "total_commits": len(commits),
                "total_additions": total_additions,
                "total_deletions": total_deletions,
                "branches": [head.name for head in self.repo.heads],
                "current_branch": self.repo.active_branch.name,
                "repo_size_mb": sum(
                    f.stat().st_size for f in Path(self.repo.git_dir).rglob("*") if f.is_file()
                )
                / (1024 * 1024),
            }
        except Exception as e:
            return {"error": str(e)}


def main() -> int:
    """CLI entry point for Git backup operations."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Manage Git backups for STM storage")
    parser.add_argument(
        "storage_dir",
        type=Path,
        help="Path to STM storage directory",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Initialize command
    subparsers.add_parser("init", help="Initialize Git repository")

    # Snapshot command
    snapshot_parser = subparsers.add_parser("snapshot", help="Create a snapshot")
    snapshot_parser.add_argument("-m", "--message", help="Commit message")

    # History command
    history_parser = subparsers.add_parser("history", help="Show commit history")
    history_parser.add_argument("-n", "--limit", type=int, default=20, help="Number of commits")

    # Status command
    subparsers.add_parser("status", help="Show repository status")

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore to a commit")
    restore_parser.add_argument("commit_sha", help="Commit SHA to restore to")

    # Stats command
    subparsers.add_parser("stats", help="Show repository statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        backup = GitBackup(storage_dir=args.storage_dir, auto_commit=False)

        if args.command == "init":
            backup.initialize()
            print("✓ Git repository initialized")

        elif args.command == "snapshot":
            backup.initialize()
            commit_sha = backup.create_snapshot(message=args.message)
            print(f"✓ Snapshot created: {commit_sha[:7]}")

        elif args.command == "history":
            backup.initialize()
            history = backup.get_history(limit=args.limit)
            print(f"\nCommit history ({len(history)} commits):\n")
            for commit in history:
                print(f"  {commit['short_sha']} - {commit['datetime']}")
                print(f"    {commit['message']}")
                print()

        elif args.command == "status":
            backup.initialize()
            status = backup.get_status()
            print("\nRepository status:\n")
            print(json.dumps(status, indent=2))

        elif args.command == "restore":
            backup.initialize()
            backup.restore_snapshot(args.commit_sha)
            print(f"✓ Restored to commit {args.commit_sha[:7]}")

        elif args.command == "stats":
            backup.initialize()
            stats = backup.get_stats()
            print("\nRepository statistics:\n")
            print(json.dumps(stats, indent=2))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
