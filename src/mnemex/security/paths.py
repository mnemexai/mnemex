"""Path traversal prevention and path security utilities.

This module provides functions to validate and sanitize file paths to prevent
path traversal attacks and other path-related security vulnerabilities.

Security Objectives:
1. Prevent directory traversal attacks (../, ../../, etc.)
2. Reject absolute paths (prevent writing outside vault)
3. Reject or resolve symlinks (prevent symlink attacks)
4. Sanitize filenames (remove dangerous characters)
5. Ensure all paths stay within designated directories

References:
- CWE-22: Path Traversal
- OWASP: https://owasp.org/www-community/attacks/Path_Traversal
"""

import re
from pathlib import Path

# Dangerous path patterns
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.|[\x00-\x1f\x7f]|[<>:\"|?*]")
ABSOLUTE_PATH_PATTERN = re.compile(r"^([a-zA-Z]:[\\/]|/|\\\\)")


def validate_folder_path(
    folder: str,
    field_name: str = "folder",
    *,
    allow_empty: bool = True,
) -> str:
    """Validate a folder path to prevent path traversal attacks.

    This function ensures that folder paths are safe to use within a vault:
    - Rejects paths containing '..' (parent directory traversal)
    - Rejects absolute paths (starting with '/', 'C:\', etc.)
    - Rejects control characters and dangerous filename chars
    - Normalizes path separators to forward slashes
    - Strips leading/trailing whitespace and slashes

    Args:
        folder: Folder path to validate (e.g., "notes/personal", "projects")
        field_name: Name of the field being validated (for error messages)
        allow_empty: Whether to allow empty string (default: True)

    Returns:
        Validated and normalized folder path

    Raises:
        ValueError: If path contains dangerous patterns

    Examples:
        >>> validate_folder_path("notes/personal")
        'notes/personal'
        >>> validate_folder_path("../../../etc")
        ValueError: folder contains path traversal patterns
        >>> validate_folder_path("/absolute/path")
        ValueError: folder must be a relative path
        >>> validate_folder_path("")
        ''
    """
    # Allow empty folder (root of vault)
    if not folder:
        if allow_empty:
            return ""
        raise ValueError(f"{field_name} cannot be empty")

    # Strip whitespace
    folder = folder.strip()

    # Check for absolute paths
    if ABSOLUTE_PATH_PATTERN.match(folder):
        raise ValueError(
            f"{field_name} must be a relative path, not an absolute path. Got: {folder!r}"
        )

    # Check for path traversal patterns
    if PATH_TRAVERSAL_PATTERN.search(folder):
        raise ValueError(
            f"{field_name} contains forbidden characters or path traversal patterns. "
            f'Paths must not contain: .., control characters, or <>:"|?* '
            f"Got: {folder!r}"
        )

    # Normalize path separators (convert backslashes to forward slashes)
    folder = folder.replace("\\", "/")

    # Remove leading/trailing slashes
    folder = folder.strip("/")

    # Check for empty path components (e.g., "a//b")
    if "//" in folder:
        raise ValueError(
            f"{field_name} contains empty path components (consecutive slashes). Got: {folder!r}"
        )

    # Additional check: split and validate each component
    components = folder.split("/")
    for i, component in enumerate(components):
        if component == "..":
            raise ValueError(
                f"{field_name} contains parent directory reference (..) at position {i}. "
                f"Got: {folder!r}"
            )
        if component == ".":
            raise ValueError(
                f"{field_name} contains current directory reference (.) at position {i}. "
                f"Got: {folder!r}"
            )
        if not component:
            raise ValueError(
                f"{field_name} has empty path component at position {i}. Got: {folder!r}"
            )

    return folder


def sanitize_filename(
    filename: str,
    field_name: str = "filename",
    *,
    max_length: int = 255,
) -> str:
    """Sanitize a filename to prevent path traversal and filesystem attacks.

    This function ensures filenames are safe:
    - Removes or replaces path separators (/, \\)
    - Removes control characters and NUL bytes
    - Removes dangerous shell characters
    - Enforces maximum length (filesystem limit)
    - Prevents reserved filenames (CON, PRN, etc. on Windows)

    Args:
        filename: Filename to sanitize
        field_name: Name of the field being validated (for error messages)
        max_length: Maximum filename length (default: 255, filesystem limit)

    Returns:
        Sanitized filename safe for filesystem operations

    Raises:
        ValueError: If filename is empty after sanitization or exceeds max_length

    Examples:
        >>> sanitize_filename("normal-file.md")
        'normal-file.md'
        >>> sanitize_filename("../../etc/passwd")
        'etc-passwd'  # Slashes removed
        >>> sanitize_filename("file<with>bad:chars?.txt")
        'file-with-bad-chars.txt'
    """
    if not filename or not filename.strip():
        raise ValueError(f"{field_name} cannot be empty")

    # Strip whitespace
    filename = filename.strip()

    # Remove control characters (0x00-0x1f, 0x7f)
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)

    # Replace path separators with hyphens
    filename = filename.replace("/", "-").replace("\\", "-")

    # Remove or replace dangerous characters: < > : " | ? *
    filename = re.sub(r'[<>:"|?*]', "-", filename)

    # Remove duplicate hyphens
    filename = re.sub(r"-+", "-", filename)

    # Remove leading/trailing hyphens and dots (hidden files, relative paths)
    filename = filename.strip("-.")

    # Check if empty after sanitization
    if not filename:
        raise ValueError(
            f"{field_name} is empty after sanitization. "
            "Filename must contain at least one valid character."
        )

    # Check Windows reserved names (CON, PRN, AUX, NUL, COM1-COM9, LPT1-LPT9)
    # These are reserved on Windows regardless of extension
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
    name_without_ext = filename.rsplit(".", 1)[0].upper()
    if name_without_ext in reserved_names:
        raise ValueError(
            f"{field_name} uses a Windows reserved name: {name_without_ext}. "
            f"Reserved names: {sorted(reserved_names)}"
        )

    # Enforce maximum length
    if len(filename) > max_length:
        raise ValueError(
            f"{field_name} exceeds maximum length of {max_length} characters. "
            f"Got {len(filename)} characters: {filename!r}"
        )

    return filename


def ensure_within_directory(
    path: Path,
    base_dir: Path,
    field_name: str = "path",
    *,
    resolve_symlinks: bool = True,
) -> Path:
    """Ensure a path stays within a designated base directory.

    This function is the ultimate safeguard against path traversal:
    - Resolves the path to its absolute, canonical form
    - Resolves symlinks (optional, recommended for security)
    - Verifies the resolved path is within base_dir
    - Prevents escaping via symbolic links

    This should be called AFTER constructing the full path but BEFORE
    performing any filesystem operations.

    Args:
        path: Path to validate (relative or absolute)
        base_dir: Base directory that path must be within
        field_name: Name of the field being validated (for error messages)
        resolve_symlinks: Whether to resolve symbolic links (default: True)

    Returns:
        Validated path (resolved to absolute canonical form)

    Raises:
        ValueError: If path escapes base_dir or is invalid

    Examples:
        >>> ensure_within_directory(
        ...     Path("/vault/notes/test.md"),
        ...     Path("/vault"),
        ... )
        PosixPath('/vault/notes/test.md')

        >>> ensure_within_directory(
        ...     Path("/vault/../etc/passwd"),
        ...     Path("/vault"),
        ... )
        ValueError: path escapes base directory
    """
    # Resolve base_dir to absolute canonical path
    if resolve_symlinks:
        base_dir = base_dir.resolve()
    else:
        base_dir = base_dir.absolute()

    # Resolve the path to absolute canonical form
    if resolve_symlinks:
        try:
            resolved_path = path.resolve(strict=False)  # Don't require existence
        except (OSError, RuntimeError) as e:
            raise ValueError(f"{field_name} cannot be resolved: {path}. Error: {e}") from e
    else:
        resolved_path = path.absolute()

    # Check if resolved path is within base_dir
    try:
        # This will raise ValueError if resolved_path is not relative to base_dir
        resolved_path.relative_to(base_dir)
    except ValueError as e:
        raise ValueError(
            f"{field_name} escapes base directory. "
            f"Path: {path} "
            f"Resolved: {resolved_path} "
            f"Base: {base_dir}"
        ) from e

    return resolved_path


def validate_vault_path(
    vault_path: Path | str,
    field_name: str = "vault_path",
) -> Path:
    """Validate a vault base path.

    Ensures the vault path is:
    - An absolute path (to prevent confusion)
    - Not a path traversal attempt
    - A valid directory path

    Args:
        vault_path: Vault base directory path
        field_name: Name of the field being validated (for error messages)

    Returns:
        Validated vault path as Path object

    Raises:
        ValueError: If vault path is invalid

    Examples:
        >>> validate_vault_path("/home/user/vault")
        PosixPath('/home/user/vault')
        >>> validate_vault_path("relative/path")
        ValueError: vault_path must be an absolute path
    """
    # Convert to Path if string
    if isinstance(vault_path, str):
        vault_path = Path(vault_path).expanduser()
    else:
        vault_path = vault_path.expanduser()

    # Ensure absolute path
    if not vault_path.is_absolute():
        raise ValueError(f"{field_name} must be an absolute path. Got relative path: {vault_path}")

    # Resolve to canonical form (resolve symlinks)
    try:
        vault_path = vault_path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"{field_name} cannot be resolved: {vault_path}. Error: {e}") from e

    return vault_path
