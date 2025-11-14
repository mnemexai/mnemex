"""File permissions security utilities.

This module provides functions to set secure file and directory permissions
to protect sensitive memory data from unauthorized access.

Security Objectives:
1. Restrict file access to owner only (0o600 for files)
2. Restrict directory access to owner only (0o700 for dirs)
3. Prevent world-readable sensitive data
4. Prevent other users from accessing memory storage
5. Comply with security best practices for credential/data files

References:
- CWE-732: Incorrect Permission Assignment
- OWASP: https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html
"""

import os
import stat
from pathlib import Path

# Secure permission constants
FILE_PERMISSIONS = 0o600  # rw------- (owner read/write only)
DIR_PERMISSIONS = 0o700  # rwx------ (owner read/write/execute only)
CONFIG_PERMISSIONS = 0o600  # rw------- (owner read/write only)


def secure_file(
    file_path: Path | str,
    *,
    permissions: int = FILE_PERMISSIONS,
    create_if_missing: bool = False,
) -> None:
    """Set secure permissions on a file (owner read/write only).

    This function restricts file access to the owner only, preventing
    other users and groups from reading sensitive memory data.

    Args:
        file_path: Path to file to secure
        permissions: Permission bits to set (default: 0o600)
        create_if_missing: Create file if it doesn't exist (default: False)

    Raises:
        FileNotFoundError: If file doesn't exist and create_if_missing is False
        PermissionError: If unable to change permissions

    Examples:
        >>> secure_file(Path("memories.jsonl"))
        # Sets permissions to rw------- (0o600)
    """
    file_path = Path(file_path)

    # Create file if requested
    if create_if_missing and not file_path.exists():
        file_path.touch()

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    try:
        os.chmod(file_path, permissions)
    except PermissionError as e:
        raise PermissionError(
            f"Unable to set permissions on {file_path}. "
            f"Ensure you own the file and have write access."
        ) from e


def secure_directory(
    dir_path: Path | str,
    *,
    permissions: int = DIR_PERMISSIONS,
    create_if_missing: bool = False,
    recursive: bool = False,
) -> None:
    """Set secure permissions on a directory (owner read/write/execute only).

    This function restricts directory access to the owner only, preventing
    other users from listing or accessing directory contents.

    Args:
        dir_path: Path to directory to secure
        permissions: Permission bits to set (default: 0o700)
        create_if_missing: Create directory if it doesn't exist (default: False)
        recursive: Also secure all subdirectories (default: False)

    Raises:
        FileNotFoundError: If directory doesn't exist and create_if_missing is False
        PermissionError: If unable to change permissions

    Examples:
        >>> secure_directory(Path("~/.config/cortexgraph"), recursive=True)
        # Sets permissions to rwx------ (0o700) on all directories
    """
    dir_path = Path(dir_path)

    # Create directory if requested
    if create_if_missing and not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {dir_path}")

    try:
        os.chmod(dir_path, permissions)
    except PermissionError as e:
        raise PermissionError(
            f"Unable to set permissions on {dir_path}. "
            f"Ensure you own the directory and have write access."
        ) from e

    # Recursively secure subdirectories if requested
    if recursive:
        for subdir in dir_path.rglob("*"):
            if subdir.is_dir():
                try:
                    os.chmod(subdir, permissions)
                except PermissionError:
                    # Log warning but continue (some subdirs might be inaccessible)
                    print(f"Warning: Unable to secure subdirectory {subdir}")


def ensure_secure_storage(
    storage_path: Path | str,
    *,
    file_permissions: int = FILE_PERMISSIONS,
    dir_permissions: int = DIR_PERMISSIONS,
) -> dict[str, int]:
    """Ensure storage directory and all files have secure permissions.

    This function recursively secures all files and directories within
    the storage path. It's the primary function for securing memory storage.

    Args:
        storage_path: Path to storage directory
        file_permissions: Permission bits for files (default: 0o600)
        dir_permissions: Permission bits for directories (default: 0o700)

    Returns:
        Dictionary with counts of secured files and directories

    Raises:
        FileNotFoundError: If storage_path doesn't exist
        PermissionError: If unable to secure some files (partial success)

    Examples:
        >>> ensure_secure_storage(Path("~/.config/cortexgraph/jsonl"))
        {'files': 5, 'directories': 2, 'errors': 0}
    """
    storage_path = Path(storage_path).expanduser().resolve()

    if not storage_path.exists():
        raise FileNotFoundError(f"Storage path not found: {storage_path}")

    if not storage_path.is_dir():
        raise ValueError(f"Storage path is not a directory: {storage_path}")

    stats = {"files": 0, "directories": 0, "errors": 0}

    # Secure the storage directory itself
    try:
        os.chmod(storage_path, dir_permissions)
        stats["directories"] += 1
    except PermissionError as e:
        print(f"Warning: Unable to secure storage directory {storage_path}: {e}")
        stats["errors"] += 1

    # Recursively secure all contents
    for item in storage_path.rglob("*"):
        try:
            if item.is_file():
                os.chmod(item, file_permissions)
                stats["files"] += 1
            elif item.is_dir():
                os.chmod(item, dir_permissions)
                stats["directories"] += 1
        except PermissionError as e:
            print(f"Warning: Unable to secure {item}: {e}")
            stats["errors"] += 1

    return stats


def secure_config_file(config_path: Path | str) -> None:
    """Secure a configuration file (e.g., .env) with owner-only permissions.

    Configuration files often contain sensitive data like API keys, so they
    should have the most restrictive permissions (0o600).

    Args:
        config_path: Path to config file (.env, etc.)

    Raises:
        FileNotFoundError: If config file doesn't exist
        PermissionError: If unable to change permissions

    Examples:
        >>> secure_config_file(Path(".env"))
        # Sets permissions to rw------- (0o600)
    """
    config_path = Path(config_path).expanduser().resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    if not config_path.is_file():
        raise ValueError(f"Config path is not a file: {config_path}")

    try:
        os.chmod(config_path, CONFIG_PERMISSIONS)
    except PermissionError as e:
        raise PermissionError(
            f"Unable to secure config file {config_path}. "
            f"This file may contain sensitive data (API keys, etc.). "
            f"Please manually set permissions to 0o600 (rw-------): "
            f"chmod 600 {config_path}"
        ) from e


def check_permissions(
    path: Path | str,
    *,
    expected_permissions: int | None = None,
) -> dict[str, bool | int | str]:
    """Check if a file or directory has appropriate secure permissions.

    This function analyzes current permissions and reports if they meet
    security requirements (owner-only access).

    Args:
        path: Path to check
        expected_permissions: Expected permission bits (if None, determined by type)

    Returns:
        Dictionary with permission analysis:
        - 'current': Current permissions (octal)
        - 'expected': Expected permissions (octal)
        - 'is_secure': True if permissions meet security requirements
        - 'world_readable': True if others can read
        - 'group_readable': True if group can read
        - 'recommendation': Human-readable recommendation

    Examples:
        >>> check_permissions(Path("memories.jsonl"))
        {
            'current': 0o644,
            'expected': 0o600,
            'is_secure': False,
            'world_readable': True,
            'group_readable': True,
            'recommendation': 'Set to 0o600 (rw-------) for security'
        }
    """
    path = Path(path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    # Get current permissions
    current_stat = path.stat()
    current_perms = stat.S_IMODE(current_stat.st_mode)

    # Determine expected permissions
    if expected_permissions is None:
        expected_permissions = DIR_PERMISSIONS if path.is_dir() else FILE_PERMISSIONS

    # Check for security issues
    world_readable = bool(current_perms & stat.S_IROTH)
    world_writable = bool(current_perms & stat.S_IWOTH)
    group_readable = bool(current_perms & stat.S_IRGRP)
    group_writable = bool(current_perms & stat.S_IWGRP)

    is_secure = current_perms == expected_permissions

    # Generate recommendation
    if is_secure:
        recommendation = "Permissions are secure"
    else:
        issues = []
        if world_readable or world_writable:
            issues.append("world-accessible")
        if group_readable or group_writable:
            issues.append("group-accessible")

        recommendation = (
            f"Set to {oct(expected_permissions)} for security. "
            f"Current issues: {', '.join(issues) if issues else 'incorrect permissions'}"
        )

    return {
        "current": oct(current_perms),
        "expected": oct(expected_permissions),
        "is_secure": is_secure,
        "world_readable": world_readable,
        "world_writable": world_writable,
        "group_readable": group_readable,
        "group_writable": group_writable,
        "recommendation": recommendation,
    }


def main() -> int:
    """CLI entry point for permission security operations."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Secure file permissions for CortexGraph storage")
    parser.add_argument("path", type=Path, help="Path to secure")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check permissions without changing them",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively secure all files and directories",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Secure as config file (0o600, strict)",
    )

    args = parser.parse_args()

    try:
        if args.check:
            # Check permissions
            result = check_permissions(args.path)
            print(f"Path: {args.path}")
            print(f"Current permissions: {result['current']}")
            print(f"Expected permissions: {result['expected']}")
            print(f"Secure: {result['is_secure']}")
            if not result["is_secure"]:
                print(f"⚠️  {result['recommendation']}")
            return 0 if result["is_secure"] else 1

        elif args.config:
            # Secure as config file
            secure_config_file(args.path)
            print(f"✓ Secured config file: {args.path} (0o600)")
            return 0

        elif args.path.is_file():
            # Secure single file
            secure_file(args.path)
            print(f"✓ Secured file: {args.path} (0o600)")
            return 0

        elif args.path.is_dir():
            if args.recursive:
                # Recursively secure directory
                stats = ensure_secure_storage(args.path)
                print(f"✓ Secured directory: {args.path}")
                print(f"  Files secured: {stats['files']}")
                print(f"  Directories secured: {stats['directories']}")
                if stats["errors"] > 0:
                    print(f"  ⚠️  Errors: {stats['errors']}")
                    return 1
                return 0
            else:
                # Secure directory only (not contents)
                secure_directory(args.path)
                print(f"✓ Secured directory: {args.path} (0o700)")
                return 0

        else:
            print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
