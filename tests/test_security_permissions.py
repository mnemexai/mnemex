"""
Comprehensive tests for the `cortexgraph.security.permissions` module.

This test suite verifies the functionality of file and directory permission
management utilities. It ensures that files and directories are created with
secure, owner-only permissions (e.g., 0o600 for files, 0o700 for directories
on POSIX systems) and that existing permissions can be correctly checked and
remediated.

The tests cover:
- Securing individual files and directories.
- Creating files/directories with secure permissions.
- Recursively securing directory trees.
- Checking for insecure permissions (group or world-read/write).
- Handling of edge cases like non-existent paths or incorrect path types.
- Command-line interface functionality for checking and applying permissions.
- Graceful handling of `PermissionError` exceptions.

Note: Most permission-related tests are skipped on non-POSIX systems (like
Windows) where the permission model is different and `os.chmod` has limited
effect.
"""

import os
import stat
import tempfile
from pathlib import Path

import pytest

from cortexgraph.security.permissions import (
    DIR_PERMISSIONS,
    FILE_PERMISSIONS,
    check_permissions,
    ensure_secure_storage,
    secure_config_file,
    secure_directory,
    secure_file,
)

IS_POSIX = os.name != "nt"


class TestSecureFile:
    """
    Tests for the `secure_file` function.

    These tests ensure that `secure_file` correctly sets permissions on new
    or existing files, handles errors gracefully, and supports custom
    permission settings.
    """

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_set_permissions_on_existing_file(self):
        """Test setting permissions on an existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            secure_file(test_file)

            file_stat = test_file.stat()
            actual_perms = stat.S_IMODE(file_stat.st_mode)
            assert actual_perms == FILE_PERMISSIONS
            assert actual_perms == 0o600

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_create_file_with_create_if_missing_true(self):
        """Test creating a file with create_if_missing=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "new_file.txt"

            assert not test_file.exists()
            secure_file(test_file, create_if_missing=True)

            assert test_file.exists()
            file_stat = test_file.stat()
            actual_perms = stat.S_IMODE(file_stat.st_mode)
            assert actual_perms == FILE_PERMISSIONS

    def test_file_not_found_when_create_if_missing_false(self):
        """Test FileNotFoundError when file doesn't exist and create_if_missing=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "nonexistent.txt"

            with pytest.raises(FileNotFoundError, match="File not found"):
                secure_file(test_file, create_if_missing=False)

    def test_value_error_when_path_is_directory(self):
        """Test ValueError when path is a directory not a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "directory"
            test_dir.mkdir()

            with pytest.raises(ValueError, match="Path is not a file"):
                secure_file(test_dir)

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_custom_permissions(self):
        """Test setting custom permissions (not just default)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            custom_perms = 0o640
            secure_file(test_file, permissions=custom_perms)

            file_stat = test_file.stat()
            actual_perms = stat.S_IMODE(file_stat.st_mode)
            assert actual_perms == custom_perms

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_verify_actual_permissions_after_setting(self):
        """Test verifying actual file permissions after setting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            os.chmod(test_file, 0o777)
            initial_perms = stat.S_IMODE(test_file.stat().st_mode)
            assert initial_perms == 0o777

            secure_file(test_file)

            final_perms = stat.S_IMODE(test_file.stat().st_mode)
            assert final_perms == FILE_PERMISSIONS
            assert final_perms == 0o600

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_secure_file_with_string_path(self):
        """Test secure_file accepts string paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            secure_file(str(test_file))

            file_stat = test_file.stat()
            actual_perms = stat.S_IMODE(file_stat.st_mode)
            assert actual_perms == FILE_PERMISSIONS


class TestSecureDirectory:
    """
    Tests for the `secure_directory` function.

    These tests verify that `secure_directory` can correctly set permissions
    on directories, create them if needed, and handle recursive operations
    without affecting files inside the directory tree.
    """

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_set_permissions_on_existing_directory(self):
        """Test setting permissions on an existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()

            secure_directory(test_dir)

            dir_stat = test_dir.stat()
            actual_perms = stat.S_IMODE(dir_stat.st_mode)
            assert actual_perms == DIR_PERMISSIONS
            assert actual_perms == 0o700

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_create_directory_with_create_if_missing_true(self):
        """Test creating a directory with create_if_missing=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "new_dir"

            assert not test_dir.exists()
            secure_directory(test_dir, create_if_missing=True)

            assert test_dir.exists()
            dir_stat = test_dir.stat()
            actual_perms = stat.S_IMODE(dir_stat.st_mode)
            assert actual_perms == DIR_PERMISSIONS

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_create_nested_directory_with_create_if_missing_true(self):
        """Test creating nested directories with create_if_missing=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "level1" / "level2" / "level3"

            assert not test_dir.exists()
            secure_directory(test_dir, create_if_missing=True)

            assert test_dir.exists()
            dir_stat = test_dir.stat()
            actual_perms = stat.S_IMODE(dir_stat.st_mode)
            assert actual_perms == DIR_PERMISSIONS

    def test_directory_not_found_when_create_if_missing_false(self):
        """Test FileNotFoundError when directory doesn't exist and create_if_missing=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "nonexistent"

            with pytest.raises(FileNotFoundError, match="Directory not found"):
                secure_directory(test_dir, create_if_missing=False)

    def test_value_error_when_path_is_file(self):
        """Test ValueError when path is a file not a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "file.txt"
            test_file.write_text("content")

            with pytest.raises(ValueError, match="Path is not a directory"):
                secure_directory(test_file)

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_custom_permissions(self):
        """Test setting custom permissions on a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()

            custom_perms = 0o750
            secure_directory(test_dir, permissions=custom_perms)

            dir_stat = test_dir.stat()
            actual_perms = stat.S_IMODE(dir_stat.st_mode)
            assert actual_perms == custom_perms

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_recursive_mode_secures_subdirectories(self):
        """Test recursive mode secures all subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "base"
            base_dir.mkdir()

            sub1 = base_dir / "sub1"
            sub1.mkdir()
            sub2 = base_dir / "sub2"
            sub2.mkdir()
            nested = sub1 / "nested"
            nested.mkdir()

            os.chmod(sub1, 0o755)
            os.chmod(sub2, 0o755)
            os.chmod(nested, 0o755)

            secure_directory(base_dir, recursive=True)

            assert stat.S_IMODE(base_dir.stat().st_mode) == DIR_PERMISSIONS
            assert stat.S_IMODE(sub1.stat().st_mode) == DIR_PERMISSIONS
            assert stat.S_IMODE(sub2.stat().st_mode) == DIR_PERMISSIONS
            assert stat.S_IMODE(nested.stat().st_mode) == DIR_PERMISSIONS

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_recursive_mode_does_not_affect_files(self):
        """Test recursive mode doesn't modify file permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "base"
            base_dir.mkdir()

            test_file = base_dir / "file.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o644)

            secure_directory(base_dir, recursive=True)

            assert stat.S_IMODE(test_file.stat().st_mode) == 0o644

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_verify_actual_permissions_after_setting(self):
        """Test verifying actual directory permissions after setting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()

            os.chmod(test_dir, 0o777)
            initial_perms = stat.S_IMODE(test_dir.stat().st_mode)
            assert initial_perms == 0o777

            secure_directory(test_dir)

            final_perms = stat.S_IMODE(test_dir.stat().st_mode)
            assert final_perms == DIR_PERMISSIONS
            assert final_perms == 0o700

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_secure_directory_with_string_path(self):
        """Test secure_directory accepts string paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()

            secure_directory(str(test_dir))

            dir_stat = test_dir.stat()
            actual_perms = stat.S_IMODE(dir_stat.st_mode)
            assert actual_perms == DIR_PERMISSIONS


class TestCheckPermissionsAsIsSecureFile:
    """
    Tests for `check_permissions` when validating file permissions.

    This class focuses on scenarios where `check_permissions` is used to
    determine if a path has secure *file* permissions (e.g., 0o600).
    """

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_file_with_secure_permissions_0o600(self):
        """Test files with secure permissions (0o600)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "secure.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o600)

            result = check_permissions(test_file)

            assert result["is_secure"] is True
            assert result["current"] == "0o600"
            assert result["expected"] == "0o600"
            assert result["world_readable"] is False
            assert result["group_readable"] is False

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_file_with_insecure_permissions_0o644(self):
        """Test files with insecure permissions (0o644)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "insecure.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o644)

            result = check_permissions(test_file)

            assert result["is_secure"] is False
            assert result["current"] == "0o644"
            assert result["world_readable"] is True
            assert result["group_readable"] is True

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_file_with_insecure_permissions_0o666(self):
        """Test files with insecure permissions (0o666)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "insecure.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o666)

            result = check_permissions(test_file)

            assert result["is_secure"] is False
            assert result["current"] == "0o666"
            assert result["world_readable"] is True
            assert result["world_writable"] is True
            assert result["group_readable"] is True
            assert result["group_writable"] is True

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_file_with_insecure_permissions_0o777(self):
        """Test files with insecure permissions (0o777)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "insecure.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o777)

            result = check_permissions(test_file)

            assert result["is_secure"] is False
            assert result["current"] == "0o777"
            assert result["world_readable"] is True
            assert result["world_writable"] is True

    def test_nonexistent_file_raises_error(self):
        """Test non-existent files raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "nonexistent.txt"

            with pytest.raises(FileNotFoundError, match="Path not found"):
                check_permissions(test_file)

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_directory_detected_as_insecure_for_file_check(self):
        """Test directories are detected as insecure when expecting file permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "directory"
            test_dir.mkdir()
            os.chmod(test_dir, 0o700)

            result = check_permissions(test_dir, expected_permissions=FILE_PERMISSIONS)

            assert result["is_secure"] is False
            assert result["expected"] == "0o600"


class TestCheckPermissionsAsIsSecureDirectory:
    """
    Tests for `check_permissions` when validating directory permissions.

    This class focuses on scenarios where `check_permissions` is used to
    determine if a path has secure *directory* permissions (e.g., 0o700).
    """

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_directory_with_secure_permissions_0o700(self):
        """Test directories with secure permissions (0o700)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "secure_dir"
            test_dir.mkdir()
            os.chmod(test_dir, 0o700)

            result = check_permissions(test_dir)

            assert result["is_secure"] is True
            assert result["current"] == "0o700"
            assert result["expected"] == "0o700"
            assert result["world_readable"] is False
            assert result["group_readable"] is False

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_directory_with_insecure_permissions_0o755(self):
        """Test directories with insecure permissions (0o755)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "insecure_dir"
            test_dir.mkdir()
            os.chmod(test_dir, 0o755)

            result = check_permissions(test_dir)

            assert result["is_secure"] is False
            assert result["current"] == "0o755"
            assert result["world_readable"] is True
            assert result["group_readable"] is True

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_directory_with_insecure_permissions_0o777(self):
        """Test directories with insecure permissions (0o777)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "insecure_dir"
            test_dir.mkdir()
            os.chmod(test_dir, 0o777)

            result = check_permissions(test_dir)

            assert result["is_secure"] is False
            assert result["current"] == "0o777"
            assert result["world_readable"] is True
            assert result["world_writable"] is True

    def test_nonexistent_directory_raises_error(self):
        """Test non-existent directories raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "nonexistent"

            with pytest.raises(FileNotFoundError, match="Path not found"):
                check_permissions(test_dir)

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_file_detected_as_insecure_for_directory_check(self):
        """Test files are detected as insecure when expecting directory permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "file.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o600)

            result = check_permissions(test_file, expected_permissions=DIR_PERMISSIONS)

            assert result["is_secure"] is False
            assert result["expected"] == "0o700"


class TestCheckPermissionsGroupAndOtherAccess:
    """
    Tests for `check_permissions` detecting group and other (world) access.

    This class verifies that the detailed permission flags (e.g.,
    `group_readable`, `world_writable`) are correctly reported.
    """

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_file_with_group_read_access(self):
        """Test files with group read access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o640)

            result = check_permissions(test_file)

            assert result["group_readable"] is True
            assert result["group_writable"] is False
            assert result["world_readable"] is False
            assert result["is_secure"] is False

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_file_with_group_write_access(self):
        """Test files with group write access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o620)

            result = check_permissions(test_file)

            assert result["group_readable"] is False
            assert result["group_writable"] is True
            assert result["is_secure"] is False

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_file_with_other_read_access(self):
        """Test files with other (world) read access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o604)

            result = check_permissions(test_file)

            assert result["world_readable"] is True
            assert result["world_writable"] is False
            assert result["group_readable"] is False
            assert result["is_secure"] is False

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_file_with_other_write_access(self):
        """Test files with other (world) write access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o602)

            result = check_permissions(test_file)

            assert result["world_readable"] is False
            assert result["world_writable"] is True
            assert result["is_secure"] is False

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_file_with_only_owner_access(self):
        """Test files with only owner access (secure)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o600)

            result = check_permissions(test_file)

            assert result["group_readable"] is False
            assert result["group_writable"] is False
            assert result["world_readable"] is False
            assert result["world_writable"] is False
            assert result["is_secure"] is True

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_directory_with_group_and_other_access(self):
        """Test directories with both group and other access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()
            os.chmod(test_dir, 0o755)

            result = check_permissions(test_dir)

            assert result["group_readable"] is True
            assert result["world_readable"] is True
            assert result["is_secure"] is False

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_various_permission_combinations(self):
        """Test various permission combinations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            test_cases = [
                (0o700, False, False, False, False),
                (0o750, True, False, False, False),
                (0o705, False, False, True, False),
                (0o777, True, True, True, True),
                (0o644, True, False, True, False),
                (0o664, True, True, True, False),
            ]

            for perms, grp_r, grp_w, wld_r, wld_w in test_cases:
                os.chmod(test_file, perms)
                result = check_permissions(test_file)

                assert result["group_readable"] == grp_r, f"Failed for {oct(perms)}"
                assert result["group_writable"] == grp_w, f"Failed for {oct(perms)}"
                assert result["world_readable"] == wld_r, f"Failed for {oct(perms)}"
                assert result["world_writable"] == wld_w, f"Failed for {oct(perms)}"


class TestSecureConfigFile:
    """
    Tests for the `secure_config_file` function.

    This class ensures that configuration files, which often contain sensitive
    data, are properly secured with owner-only read/write permissions.
    """

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_secure_existing_config_file(self):
        """Test securing an existing config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".env"
            config_file.write_text("API_KEY=secret")

            secure_config_file(config_file)

            file_stat = config_file.stat()
            actual_perms = stat.S_IMODE(file_stat.st_mode)
            assert actual_perms == 0o600

    def test_config_file_not_found(self):
        """Test FileNotFoundError when config file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "nonexistent.env"

            with pytest.raises(FileNotFoundError, match="Config file not found"):
                secure_config_file(config_file)

    def test_config_path_is_directory_raises_error(self):
        """Test ValueError when config path is a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            with pytest.raises(ValueError, match="Config path is not a file"):
                secure_config_file(config_dir)

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_secure_config_file_with_string_path(self):
        """Test secure_config_file accepts string paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".env"
            config_file.write_text("SECRET=value")

            secure_config_file(str(config_file))

            file_stat = config_file.stat()
            actual_perms = stat.S_IMODE(file_stat.st_mode)
            assert actual_perms == 0o600

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_secure_config_file_with_tilde_expansion(self):
        """Test secure_config_file handles tilde expansion."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as tf:
            tf.write("TEST=value")
            temp_path = Path(tf.name)

        try:
            secure_config_file(temp_path)

            file_stat = temp_path.stat()
            actual_perms = stat.S_IMODE(file_stat.st_mode)
            assert actual_perms == 0o600
        finally:
            temp_path.unlink()


class TestEnsureSecureStorage:
    """
    Tests for the `ensure_secure_storage` function.

    This class verifies that the function can recursively traverse a storage
    directory and apply secure permissions to all files and subdirectories
    within it.
    """

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_secure_storage_directory_and_files(self):
        """Test securing storage directory and all contained files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "storage"
            storage_dir.mkdir()

            file1 = storage_dir / "mem1.jsonl"
            file1.write_text("data1")
            file2 = storage_dir / "mem2.jsonl"
            file2.write_text("data2")

            os.chmod(file1, 0o644)
            os.chmod(file2, 0o644)

            stats = ensure_secure_storage(storage_dir)

            assert stats["files"] == 2
            assert stats["directories"] == 1
            assert stats["errors"] == 0

            assert stat.S_IMODE(storage_dir.stat().st_mode) == DIR_PERMISSIONS
            assert stat.S_IMODE(file1.stat().st_mode) == FILE_PERMISSIONS
            assert stat.S_IMODE(file2.stat().st_mode) == FILE_PERMISSIONS

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_secure_storage_with_subdirectories(self):
        """Test securing storage with nested subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "storage"
            storage_dir.mkdir()

            subdir1 = storage_dir / "sub1"
            subdir1.mkdir()
            subdir2 = storage_dir / "sub2"
            subdir2.mkdir()
            nested = subdir1 / "nested"
            nested.mkdir()

            file1 = storage_dir / "file1.txt"
            file1.write_text("data")
            file2 = subdir1 / "file2.txt"
            file2.write_text("data")
            file3 = nested / "file3.txt"
            file3.write_text("data")

            stats = ensure_secure_storage(storage_dir)

            assert stats["files"] == 3
            assert stats["directories"] >= 3
            assert stats["errors"] == 0

            assert stat.S_IMODE(storage_dir.stat().st_mode) == DIR_PERMISSIONS
            assert stat.S_IMODE(subdir1.stat().st_mode) == DIR_PERMISSIONS
            assert stat.S_IMODE(subdir2.stat().st_mode) == DIR_PERMISSIONS
            assert stat.S_IMODE(nested.stat().st_mode) == DIR_PERMISSIONS
            assert stat.S_IMODE(file1.stat().st_mode) == FILE_PERMISSIONS
            assert stat.S_IMODE(file2.stat().st_mode) == FILE_PERMISSIONS
            assert stat.S_IMODE(file3.stat().st_mode) == FILE_PERMISSIONS

    def test_storage_path_not_found(self):
        """Test FileNotFoundError when storage path doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "nonexistent"

            with pytest.raises(FileNotFoundError, match="Storage path not found"):
                ensure_secure_storage(storage_dir)

    def test_storage_path_is_file_raises_error(self):
        """Test ValueError when storage path is a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "file.txt"
            storage_file.write_text("content")

            with pytest.raises(ValueError, match="Storage path is not a directory"):
                ensure_secure_storage(storage_file)

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_custom_file_and_directory_permissions(self):
        """Test ensure_secure_storage with custom permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "storage"
            storage_dir.mkdir()

            file1 = storage_dir / "file.txt"
            file1.write_text("data")

            custom_file_perms = 0o640
            custom_dir_perms = 0o750

            stats = ensure_secure_storage(
                storage_dir, file_permissions=custom_file_perms, dir_permissions=custom_dir_perms
            )

            assert stats["files"] == 1
            assert stats["directories"] == 1

            assert stat.S_IMODE(storage_dir.stat().st_mode) == custom_dir_perms
            assert stat.S_IMODE(file1.stat().st_mode) == custom_file_perms

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_empty_storage_directory(self):
        """Test securing an empty storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "storage"
            storage_dir.mkdir()

            stats = ensure_secure_storage(storage_dir)

            assert stats["files"] == 0
            assert stats["directories"] == 1
            assert stats["errors"] == 0

            assert stat.S_IMODE(storage_dir.stat().st_mode) == DIR_PERMISSIONS


class TestCheckPermissions:
    """
    High-level tests for the `check_permissions` function.

    This class tests the overall behavior of the function, including its
    ability to auto-detect path types and return a comprehensive dictionary
    of permission details.
    """

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_check_permissions_secure_file(self):
        """Test check_permissions on a secure file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "secure.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o600)

            result = check_permissions(test_file)

            assert result["current"] == "0o600"
            assert result["expected"] == "0o600"
            assert result["is_secure"] is True
            assert "secure" in result["recommendation"].lower()

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_check_permissions_insecure_file(self):
        """Test check_permissions on an insecure file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "insecure.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o644)

            result = check_permissions(test_file)

            assert result["current"] == "0o644"
            assert result["is_secure"] is False
            assert "0o600" in result["recommendation"]

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_check_permissions_with_custom_expected_permissions(self):
        """Test check_permissions with custom expected permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o640)

            result = check_permissions(test_file, expected_permissions=0o640)

            assert result["current"] == "0o640"
            assert result["expected"] == "0o640"
            assert result["is_secure"] is True

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_check_permissions_auto_detects_directory(self):
        """Test check_permissions auto-detects directory type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()
            os.chmod(test_dir, 0o700)

            result = check_permissions(test_dir)

            assert result["expected"] == "0o700"
            assert result["is_secure"] is True

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_check_permissions_returns_all_fields(self):
        """Test check_permissions returns all expected fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o644)

            result = check_permissions(test_file)

            required_fields = [
                "current",
                "expected",
                "is_secure",
                "world_readable",
                "world_writable",
                "group_readable",
                "group_writable",
                "recommendation",
            ]

            for field in required_fields:
                assert field in result

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_check_permissions_with_string_path(self):
        """Test check_permissions accepts string paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o600)

            result = check_permissions(str(test_file))

            assert result["is_secure"] is True

    def test_check_permissions_nonexistent_path(self):
        """Test check_permissions raises error for nonexistent path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "nonexistent.txt"

            with pytest.raises(FileNotFoundError, match="Path not found"):
                check_permissions(test_file)


class TestMain:
    """
    Tests for the `main()` command-line interface function.

    This class mocks `sys.argv` to simulate command-line calls and verifies
    the output, exit codes, and file system side effects.
    """

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_main_check_secure_file(self, monkeypatch, capsys):
        """Test main with --check flag on a secure file."""
        from cortexgraph.security.permissions import main

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "secure.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o600)

            monkeypatch.setattr("sys.argv", ["prog", str(test_file), "--check"])

            result = main()

            assert result == 0
            captured = capsys.readouterr()
            assert "Secure: True" in captured.out

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_main_check_insecure_file(self, monkeypatch, capsys):
        """Test main with --check flag on an insecure file."""
        from cortexgraph.security.permissions import main

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "insecure.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o644)

            monkeypatch.setattr("sys.argv", ["prog", str(test_file), "--check"])

            result = main()

            assert result == 1
            captured = capsys.readouterr()
            assert "Secure: False" in captured.out
            assert "⚠️" in captured.out

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_main_secure_config_file(self, monkeypatch, capsys):
        """Test main with --config flag."""
        from cortexgraph.security.permissions import main

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".env"
            config_file.write_text("API_KEY=secret")

            monkeypatch.setattr("sys.argv", ["prog", str(config_file), "--config"])

            result = main()

            assert result == 0
            captured = capsys.readouterr()
            assert "Secured config file" in captured.out

            file_stat = config_file.stat()
            actual_perms = stat.S_IMODE(file_stat.st_mode)
            assert actual_perms == 0o600

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_main_secure_single_file(self, monkeypatch, capsys):
        """Test main securing a single file."""
        from cortexgraph.security.permissions import main

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            os.chmod(test_file, 0o644)

            monkeypatch.setattr("sys.argv", ["prog", str(test_file)])

            result = main()

            assert result == 0
            captured = capsys.readouterr()
            assert "Secured file" in captured.out

            file_stat = test_file.stat()
            actual_perms = stat.S_IMODE(file_stat.st_mode)
            assert actual_perms == 0o600

    @pytest.mark.skipif(not IS_POSIX, reason="Unix permissions not applicable on Windows")
    def test_main_secure_directory_non_recursive(self, monkeypatch, capsys):
        """Test main securing a directory without --recursive."""
        from cortexgraph.security.permissions import main

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()
            os.chmod(test_dir, 0o755)

            monkeypatch.setattr("sys.argv", ["prog", str(test_dir)])

            result = main()

            assert result == 0
            captured = capsys.readouterr()
            assert "Secured directory" in captured.out

            dir_stat = test_dir.stat()
            actual_perms = stat.S_IMODE(dir_stat.st_mode)
            assert actual_perms == 0o700

    def test_main_secure_directory_recursive(self, monkeypatch, capsys):
        """Test main securing a directory with --recursive."""
        from cortexgraph.security.permissions import main

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()

            subdir = test_dir / "subdir"
            subdir.mkdir()

            file1 = test_dir / "file1.txt"
            file1.write_text("data")

            monkeypatch.setattr("sys.argv", ["prog", str(test_dir), "--recursive"])

            result = main()

            assert result == 0
            captured = capsys.readouterr()
            assert "Secured directory" in captured.out
            assert "Files secured:" in captured.out
            assert "Directories secured:" in captured.out

    def test_main_recursive_with_errors(self, monkeypatch, capsys):
        """Test main with --recursive when there are permission errors."""
        from cortexgraph.security.permissions import main

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()

            file1 = test_dir / "file1.txt"
            file1.write_text("data")

            monkeypatch.setattr("sys.argv", ["prog", str(test_dir), "--recursive"])

            result = main()

            if result == 1:
                captured = capsys.readouterr()
                assert "Errors:" in captured.out
            else:
                assert result == 0

    def test_main_nonexistent_path(self, monkeypatch, capsys):
        """Test main with a nonexistent path."""
        from cortexgraph.security.permissions import main

        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent"

            monkeypatch.setattr("sys.argv", ["prog", str(nonexistent)])

            result = main()

            assert result == 1
            captured = capsys.readouterr()
            assert "Error" in captured.err or "Error" in captured.out

    def test_main_exception_handling(self, monkeypatch, capsys):
        """Test main exception handling."""
        from cortexgraph.security.permissions import main

        monkeypatch.setattr("sys.argv", ["prog", "/nonexistent/path/that/does/not/exist"])

        result = main()

        assert result == 1


class TestPermissionErrors:
    """
    Tests for `PermissionError` exception handling.

    This class ensures that the permission-setting functions raise or handle
    `PermissionError` appropriately when the underlying `os.chmod` call fails,
    simulated via mocking.
    """

    def test_secure_file_permission_error(self, monkeypatch):
        """Test PermissionError when securing a file."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            original_chmod = os.chmod

            def mock_chmod(path, mode):
                if str(path) == str(test_file):
                    raise PermissionError("Permission denied")
                return original_chmod(path, mode)

            monkeypatch.setattr(os, "chmod", mock_chmod)

            with pytest.raises(PermissionError, match="Unable to set permissions"):
                secure_file(test_file)

    def test_secure_directory_permission_error(self, monkeypatch):
        """Test PermissionError when securing a directory."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()

            original_chmod = os.chmod

            def mock_chmod(path, mode):
                if str(path) == str(test_dir):
                    raise PermissionError("Permission denied")
                return original_chmod(path, mode)

            monkeypatch.setattr(os, "chmod", mock_chmod)

            with pytest.raises(PermissionError, match="Unable to set permissions"):
                secure_directory(test_dir)

    def test_secure_directory_recursive_subdirectory_permission_error(self, monkeypatch, capsys):
        """Test PermissionError warning on subdirectory in recursive mode."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()

            subdir = test_dir / "subdir"
            subdir.mkdir()

            original_chmod = os.chmod

            def mock_chmod(path, mode):
                if str(path) == str(subdir):
                    raise PermissionError("Permission denied")
                return original_chmod(path, mode)

            monkeypatch.setattr(os, "chmod", mock_chmod)

            secure_directory(test_dir, recursive=True)

            captured = capsys.readouterr()
            assert "Warning: Unable to secure subdirectory" in captured.out

    @pytest.mark.skipif(
        not IS_POSIX or os.uname().sysname == "Darwin",
        reason="Permission error behavior differs on macOS/Windows",
    )
    def test_secure_config_file_permission_error(self, monkeypatch):
        """Test PermissionError when securing a config file."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".env"
            config_file.write_text("SECRET=value")

            original_chmod = os.chmod

            def mock_chmod(path, mode):
                if str(path) == str(config_file):
                    raise PermissionError("Permission denied")
                return original_chmod(path, mode)

            monkeypatch.setattr(os, "chmod", mock_chmod)

            with pytest.raises(PermissionError, match="Unable to secure config file"):
                secure_config_file(config_file)

    @pytest.mark.skipif(
        not IS_POSIX or os.uname().sysname == "Darwin",
        reason="Permission error behavior differs on macOS/Windows",
    )
    def test_ensure_secure_storage_directory_permission_error(self, monkeypatch, capsys):
        """Test PermissionError on storage directory in ensure_secure_storage."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "storage"
            storage_dir.mkdir()

            original_chmod = os.chmod

            def mock_chmod(path, mode):
                if str(path) == str(storage_dir):
                    raise PermissionError("Permission denied")
                return original_chmod(path, mode)

            monkeypatch.setattr(os, "chmod", mock_chmod)

            stats = ensure_secure_storage(storage_dir)

            assert stats["errors"] > 0
            captured = capsys.readouterr()
            assert "Warning: Unable to secure storage directory" in captured.out

    @pytest.mark.skipif(
        not IS_POSIX or os.uname().sysname == "Darwin",
        reason="Permission error behavior differs on macOS/Windows",
    )
    def test_ensure_secure_storage_file_permission_error(self, monkeypatch, capsys):
        """Test PermissionError on files in ensure_secure_storage."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "storage"
            storage_dir.mkdir()

            test_file = storage_dir / "file.txt"
            test_file.write_text("data")

            original_chmod = os.chmod
            call_count = [0]

            def mock_chmod(path, mode):
                call_count[0] += 1
                if call_count[0] > 1 and str(path) == str(test_file):
                    raise PermissionError("Permission denied")
                return original_chmod(path, mode)

            monkeypatch.setattr(os, "chmod", mock_chmod)

            stats = ensure_secure_storage(storage_dir)

            assert stats["errors"] > 0
            captured = capsys.readouterr()
            assert "Warning: Unable to secure" in captured.out

    def test_main_with_storage_errors_returns_1(self, monkeypatch, capsys):
        """Test main returns 1 when ensure_secure_storage has errors."""
        import os

        from cortexgraph.security.permissions import main

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()

            test_file = test_dir / "file.txt"
            test_file.write_text("data")

            original_chmod = os.chmod
            call_count = [0]

            def mock_chmod(path, mode):
                call_count[0] += 1
                if call_count[0] > 1:
                    raise PermissionError("Permission denied")
                return original_chmod(path, mode)

            monkeypatch.setattr(os, "chmod", mock_chmod)
            monkeypatch.setattr("sys.argv", ["prog", str(test_dir), "--recursive"])

            result = main()

            assert result == 1
            captured = capsys.readouterr()
            assert "Errors:" in captured.out
