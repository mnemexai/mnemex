"""
Comprehensive tests for the `cortexgraph.security.paths` module.

This test suite ensures that the path validation and sanitization functions
in `cortexgraph.security.paths` are robust and correctly handle a wide
range of valid and invalid inputs. The tests cover:
- Path traversal attacks.
- Absolute vs. relative path validation.
- Handling of dangerous characters and control characters.
- Normalization of paths (e.g., slashes, whitespace).
- Filename sanitization, including reserved names and length limits.
- Directory containment checks to prevent escaping a base directory.
- Vault path validation.
"""

import tempfile
from pathlib import Path

import pytest

from cortexgraph.security.paths import (
    ensure_within_directory,
    sanitize_filename,
    validate_folder_path,
    validate_vault_path,
)


class TestValidateFolderPath:
    """
    Tests for the `validate_folder_path` function.

    These tests verify that the function correctly validates and normalizes
    relative folder paths, while rejecting absolute paths, path traversal
    attempts, and paths with invalid characters.
    """

    def test_valid_single_level_folder(self):
        """Test valid single-level folder paths."""
        assert validate_folder_path("notes") == "notes"
        assert validate_folder_path("projects") == "projects"
        assert validate_folder_path("work") == "work"

    def test_valid_nested_folder_paths(self):
        """Test valid nested folder paths."""
        assert validate_folder_path("notes/personal") == "notes/personal"
        assert validate_folder_path("work/projects/2024") == "work/projects/2024"
        assert validate_folder_path("a/b/c/d/e") == "a/b/c/d/e"

    def test_empty_folder_allow_empty_true(self):
        """Test empty folder with allow_empty=True."""
        assert validate_folder_path("", allow_empty=True) == ""

    def test_empty_folder_allow_empty_false(self):
        """Test empty folder with allow_empty=False."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_folder_path("", allow_empty=False)

    def test_whitespace_only_folder(self):
        """Test that whitespace-only folders become empty after stripping."""
        with pytest.raises(ValueError, match="empty path component"):
            validate_folder_path("   ", allow_empty=True)
        with pytest.raises(ValueError, match="empty path component"):
            validate_folder_path("   ", allow_empty=False)

    def test_path_traversal_double_dots(self):
        """Test rejection of path traversal with .. patterns."""
        with pytest.raises(ValueError, match="path traversal patterns"):
            validate_folder_path("..")
        with pytest.raises(ValueError, match="path traversal patterns"):
            validate_folder_path("../etc")
        with pytest.raises(ValueError, match="path traversal patterns"):
            validate_folder_path("../../etc/passwd")
        with pytest.raises(ValueError, match="path traversal patterns"):
            validate_folder_path("notes/../../../etc")

    def test_absolute_paths_unix(self):
        """Test rejection of absolute Unix paths."""
        with pytest.raises(ValueError, match="must be a relative path"):
            validate_folder_path("/")
        with pytest.raises(ValueError, match="must be a relative path"):
            validate_folder_path("/etc/passwd")
        with pytest.raises(ValueError, match="must be a relative path"):
            validate_folder_path("/home/user/notes")

    def test_absolute_paths_windows(self):
        """Test rejection of absolute Windows paths."""
        with pytest.raises(ValueError, match="must be a relative path"):
            validate_folder_path("C:\\")
        with pytest.raises(ValueError, match="must be a relative path"):
            validate_folder_path("C:\\Users\\test")
        with pytest.raises(ValueError, match="must be a relative path"):
            validate_folder_path("D:/projects")

    def test_network_paths(self):
        """Test rejection of UNC network paths."""
        with pytest.raises(ValueError, match="must be a relative path"):
            validate_folder_path("\\\\server\\share")
        with pytest.raises(ValueError, match="must be a relative path"):
            validate_folder_path("\\\\network\\folder")

    def test_control_characters(self):
        """Test rejection of control characters."""
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_folder_path("test\x00folder")
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_folder_path("test\x1ffolder")
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_folder_path("test\x0bfolder")

    def test_dangerous_characters(self):
        """Test rejection of dangerous characters."""
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_folder_path("test<folder")
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_folder_path("test>folder")
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_folder_path("test:folder")
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_folder_path('test"folder')
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_folder_path("test|folder")
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_folder_path("test?folder")
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_folder_path("test*folder")

    def test_double_slashes(self):
        """Test rejection of double slashes (empty path components)."""
        with pytest.raises(ValueError, match="consecutive slashes"):
            validate_folder_path("a//b")
        with pytest.raises(ValueError, match="consecutive slashes"):
            validate_folder_path("test//folder")
        with pytest.raises(ValueError, match="consecutive slashes"):
            validate_folder_path("a///b///c")

    def test_current_directory_reference(self):
        """Test rejection of current directory references (.)."""
        with pytest.raises(ValueError, match="current directory reference"):
            validate_folder_path(".")
        with pytest.raises(ValueError, match="current directory reference"):
            validate_folder_path("./notes")
        with pytest.raises(ValueError, match="current directory reference"):
            validate_folder_path("notes/./subfolder")
        with pytest.raises(ValueError, match="current directory reference"):
            validate_folder_path("a/b/./c")

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        assert validate_folder_path("  notes  ") == "notes"
        assert validate_folder_path("\tnotes\t") == "notes"
        assert validate_folder_path("  notes/personal  ") == "notes/personal"

    def test_trailing_slashes_removed(self):
        """Test that trailing slashes are removed (leading / is absolute path)."""
        assert validate_folder_path("notes/") == "notes"
        assert validate_folder_path("notes/personal/") == "notes/personal"
        assert validate_folder_path("a/b/c/") == "a/b/c"

    def test_backslash_to_forward_slash_normalization(self):
        """Test backslash to forward slash conversion."""
        assert validate_folder_path("notes\\personal") == "notes/personal"
        assert validate_folder_path("a\\b\\c") == "a/b/c"
        assert validate_folder_path("mixed/path\\test") == "mixed/path/test"

    def test_custom_field_name_in_errors(self):
        """Test that custom field_name appears in error messages."""
        with pytest.raises(ValueError, match="custom_field"):
            validate_folder_path("..", field_name="custom_field")
        with pytest.raises(ValueError, match="custom_field"):
            validate_folder_path("", field_name="custom_field", allow_empty=False)


class TestSanitizeFilename:
    """
    Tests for the `sanitize_filename` function.

    These tests ensure that filenames are properly sanitized by removing or
    replacing invalid characters, rejecting reserved filenames, and enforcing
    length limits. This is crucial for preventing security vulnerabilities
    related to file creation.
    """

    def test_valid_normal_filename(self):
        """Test valid normal filenames."""
        assert sanitize_filename("normal-file.md") == "normal-file.md"
        assert sanitize_filename("document.txt") == "document.txt"
        assert sanitize_filename("my_file.py") == "my_file.py"

    def test_valid_filename_with_extensions(self):
        """Test valid filenames with various extensions."""
        assert sanitize_filename("readme.md") == "readme.md"
        assert sanitize_filename("data.json") == "data.json"
        assert sanitize_filename("image.png") == "image.png"
        assert sanitize_filename("archive.tar.gz") == "archive.tar.gz"

    def test_valid_filename_with_hyphens(self):
        """Test valid filenames with hyphens."""
        assert sanitize_filename("my-test-file.txt") == "my-test-file.txt"
        assert sanitize_filename("dash-separated-name.md") == "dash-separated-name.md"

    def test_path_separators_removed(self):
        """Test that path separators are replaced with hyphens."""
        assert sanitize_filename("../../etc/passwd") == "etc-passwd"
        assert sanitize_filename("path/to/file.txt") == "path-to-file.txt"
        assert sanitize_filename("windows\\path\\file.txt") == "windows-path-file.txt"
        assert sanitize_filename("a/b\\c/d.txt") == "a-b-c-d.txt"

    def test_control_characters_removed(self):
        """Test that control characters are removed."""
        assert sanitize_filename("test\x00file.txt") == "testfile.txt"
        assert sanitize_filename("test\x1ffile.txt") == "testfile.txt"
        assert sanitize_filename("test\x0bfile.txt") == "testfile.txt"
        assert sanitize_filename("test\x7ffile.txt") == "testfile.txt"

    def test_dangerous_characters_replaced(self):
        """Test that dangerous characters are replaced with hyphens."""
        assert sanitize_filename("file<name>.txt") == "file-name-.txt"
        assert sanitize_filename("file>name.txt") == "file-name.txt"
        assert sanitize_filename("file:name.txt") == "file-name.txt"
        assert sanitize_filename('file"name.txt') == "file-name.txt"
        assert sanitize_filename("file|name.txt") == "file-name.txt"
        assert sanitize_filename("file?name.txt") == "file-name.txt"
        assert sanitize_filename("file*name.txt") == "file-name.txt"

    def test_windows_reserved_names(self):
        """Test rejection of Windows reserved names."""
        reserved = [
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
        ]

        for name in reserved:
            with pytest.raises(ValueError, match="Windows reserved name"):
                sanitize_filename(name)
            with pytest.raises(ValueError, match="Windows reserved name"):
                sanitize_filename(name.lower())

    def test_reserved_names_with_extensions(self):
        """Test rejection of Windows reserved names with extensions."""
        with pytest.raises(ValueError, match="Windows reserved name"):
            sanitize_filename("CON.txt")
        with pytest.raises(ValueError, match="Windows reserved name"):
            sanitize_filename("PRN.md")
        with pytest.raises(ValueError, match="Windows reserved name"):
            sanitize_filename("NUL.json")
        with pytest.raises(ValueError, match="Windows reserved name"):
            sanitize_filename("COM1.log")

    def test_length_validation_within_limit(self):
        """Test that filenames within the length limit are accepted."""
        filename_200 = "a" * 200 + ".txt"
        assert len(sanitize_filename(filename_200)) == 204

    def test_length_validation_exceeds_limit(self):
        """Test rejection of filenames exceeding max length."""
        filename_too_long = "a" * 256
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_filename(filename_too_long)

        filename_260 = "x" * 260
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_filename(filename_260)

    def test_custom_max_length(self):
        """Test custom max_length parameter."""
        with pytest.raises(ValueError, match="exceeds maximum length of 10"):
            sanitize_filename("verylongfilename.txt", max_length=10)

        assert sanitize_filename("short.txt", max_length=20) == "short.txt"

    def test_empty_filename(self):
        """Test rejection of empty filenames."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_filename("")
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_filename("   ")
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_filename("\t\n")

    def test_filename_becomes_empty_after_sanitization(self):
        """Test rejection when filename becomes empty after sanitization."""
        with pytest.raises(ValueError, match="empty after sanitization"):
            sanitize_filename("///")
        with pytest.raises(ValueError, match="empty after sanitization"):
            sanitize_filename("<<<>>>")
        with pytest.raises(ValueError, match="empty after sanitization"):
            sanitize_filename(".....")
        with pytest.raises(ValueError, match="empty after sanitization"):
            sanitize_filename("---")

    def test_duplicate_hyphens_collapsed(self):
        """Test that duplicate hyphens are collapsed."""
        assert sanitize_filename("test---file.txt") == "test-file.txt"
        assert sanitize_filename("a----b----c.txt") == "a-b-c.txt"

    def test_leading_trailing_hyphens_removed(self):
        """Test that leading/trailing hyphens and dots are removed."""
        assert sanitize_filename("-file.txt") == "file.txt"
        assert sanitize_filename("file.txt-") == "file.txt"
        assert sanitize_filename(".hidden") == "hidden"
        assert sanitize_filename("..file.txt") == "file.txt"

    def test_custom_field_name_in_errors(self):
        """Test that custom field_name appears in error messages."""
        with pytest.raises(ValueError, match="my_file"):
            sanitize_filename("", field_name="my_file")
        with pytest.raises(ValueError, match="my_file"):
            sanitize_filename("a" * 300, field_name="my_file")


class TestEnsureWithinDirectory:
    """
    Tests for the `ensure_within_directory` function.

    These tests confirm that the function correctly resolves paths and raises
    an error if the resulting path falls outside of the specified base
    directory. This is a critical security measure to prevent directory
    traversal attacks.
    """

    def test_path_within_base_directory_relative(self):
        """Test that paths within base directory are accepted (relative)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            test_path = base_dir / "notes" / "test.md"

            result = ensure_within_directory(test_path, base_dir)
            assert result.is_absolute()
            # Resolve both paths to handle symlinks (e.g., /var -> /private/var on macOS)
            assert str(result).startswith(str(base_dir.resolve()))

    def test_path_within_base_directory_absolute(self):
        """Test that paths within base directory are accepted (absolute)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir).resolve()
            test_path = base_dir / "subfolder" / "file.txt"

            result = ensure_within_directory(test_path, base_dir)
            assert result.is_absolute()
            assert str(result).startswith(str(base_dir))

    def test_nested_paths_within_base(self):
        """Test deeply nested paths within base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            test_path = base_dir / "a" / "b" / "c" / "d" / "e" / "file.txt"

            result = ensure_within_directory(test_path, base_dir)
            assert str(result).startswith(str(base_dir.resolve()))

    def test_path_traversal_escaping_base(self):
        """Test that path traversal attempts are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            test_path = base_dir / ".." / "etc" / "passwd"
            with pytest.raises(ValueError, match="escapes base directory"):
                ensure_within_directory(test_path, base_dir)

            test_path2 = base_dir / "notes" / ".." / ".." / "etc"
            with pytest.raises(ValueError, match="escapes base directory"):
                ensure_within_directory(test_path2, base_dir)

    def test_absolute_path_outside_base(self):
        """Test that absolute paths outside base are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            outside_path = Path("/etc/passwd")
            with pytest.raises(ValueError, match="escapes base directory"):
                ensure_within_directory(outside_path, base_dir)

    def test_symlink_resolution_enabled(self):
        """Test symlink resolution with resolve_symlinks=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            real_file = base_dir / "real_file.txt"
            real_file.write_text("test content")

            symlink_file = base_dir / "symlink.txt"
            symlink_file.symlink_to(real_file)

            result = ensure_within_directory(symlink_file, base_dir, resolve_symlinks=True)
            assert result.is_absolute()
            assert str(result).startswith(str(base_dir.resolve()))

    def test_symlink_resolution_disabled(self):
        """Test symlink resolution with resolve_symlinks=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            real_file = base_dir / "real_file.txt"
            real_file.write_text("test content")

            symlink_file = base_dir / "symlink.txt"
            symlink_file.symlink_to(real_file)

            result = ensure_within_directory(symlink_file, base_dir, resolve_symlinks=False)
            assert result.is_absolute()
            assert str(result).startswith(str(base_dir.absolute()))

    def test_symlink_escaping_base_with_resolution(self):
        """Test that symlinks escaping base are caught with resolve_symlinks=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "vault"
            base_dir.mkdir()

            outside_dir = Path(tmpdir) / "outside"
            outside_dir.mkdir()
            outside_file = outside_dir / "secret.txt"
            outside_file.write_text("secret")

            symlink = base_dir / "link_to_secret.txt"
            symlink.symlink_to(outside_file)

            with pytest.raises(ValueError, match="escapes base directory"):
                ensure_within_directory(symlink, base_dir, resolve_symlinks=True)

    def test_custom_field_name_in_errors(self):
        """Test that custom field_name appears in error messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            outside_path = Path("/etc/passwd")

            with pytest.raises(ValueError, match="my_path"):
                ensure_within_directory(outside_path, base_dir, field_name="my_path")


class TestValidateVaultPath:
    """
    Tests for the `validate_vault_path` function.

    These tests ensure that the function correctly validates and resolves
    absolute paths for the vault directory, including expanding user-home
    (~) paths, while rejecting relative paths.
    """

    def test_valid_absolute_path(self):
        """Test valid absolute paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()

            result = validate_vault_path(vault_path)
            assert result.is_absolute()
            assert result == vault_path.resolve()

    def test_valid_absolute_path_as_string(self):
        """Test valid absolute paths passed as strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_dir = Path(tmpdir) / "vault"
            vault_dir.mkdir()

            result = validate_vault_path(str(vault_dir))
            assert result.is_absolute()
            assert isinstance(result, Path)

    def test_relative_path_rejected(self):
        """Test that relative paths are rejected."""
        with pytest.raises(ValueError, match="must be an absolute path"):
            validate_vault_path("relative/path")
        with pytest.raises(ValueError, match="must be an absolute path"):
            validate_vault_path("vault")
        with pytest.raises(ValueError, match="must be an absolute path"):
            validate_vault_path("./vault")

    def test_path_expansion_tilde(self):
        """Test that tilde (~) paths are expanded."""
        vault_path = Path("~/vault")
        result = validate_vault_path(vault_path)

        assert result.is_absolute()
        assert "~" not in str(result)

    def test_path_expansion_tilde_string(self):
        """Test that tilde paths as strings are expanded."""
        result = validate_vault_path("~/test/vault")

        assert result.is_absolute()
        assert "~" not in str(result)

    def test_nonexistent_path_allowed(self):
        """Test that non-existent paths are allowed (will be created later)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "nonexistent" / "vault"

            result = validate_vault_path(vault_path)
            assert result.is_absolute()

    def test_custom_field_name_in_errors(self):
        """Test that custom field_name appears in error messages."""
        with pytest.raises(ValueError, match="my_vault"):
            validate_vault_path("relative/path", field_name="my_vault")
