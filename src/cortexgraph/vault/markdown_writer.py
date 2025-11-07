"""Markdown writer for Obsidian vault integration.

Clean-room implementation for writing markdown files with YAML frontmatter
and wikilinks. Does NOT use Basic Memory MCP code (AGPL license).
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any

import frontmatter

from ..security.paths import (
    ensure_within_directory,
    sanitize_filename,
    validate_folder_path,
    validate_vault_path,
)


class MarkdownWriter:
    """Write markdown files to Obsidian vault with proper formatting."""

    def __init__(self, vault_path: Path):
        """
        Initialize markdown writer.

        Args:
            vault_path: Path to Obsidian vault root directory

        Raises:
            ValueError: If vault_path is invalid or contains path traversal
        """
        # Validate and normalize vault path (prevents path traversal)
        self.vault_path = validate_vault_path(vault_path, "vault_path")
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def create_wikilink(self, target: str, alias: str | None = None) -> str:
        """
        Create a wikilink string.

        Args:
            target: Target note title
            alias: Optional display alias

        Returns:
            Formatted wikilink string

        Examples:
            >>> create_wikilink("Note Title")
            '[[Note Title]]'
            >>> create_wikilink("Note Title", "Display Text")
            '[[Note Title|Display Text]]'
        """
        if alias:
            return f"[[{target}|{alias}]]"
        return f"[[{target}]]"

    def write_note(
        self,
        title: str,
        content: str,
        folder: str = "",
        *,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        wikilinks: list[str] | None = None,
        created_at: int | None = None,
        modified_at: int | None = None,
    ) -> Path:
        """
        Write a markdown note to the vault.

        Args:
            title: Note title (used for filename)
            content: Note content (markdown)
            folder: Subfolder within vault (default: root)
            tags: List of tags
            metadata: Additional YAML frontmatter metadata
            wikilinks: List of wikilink targets to include in frontmatter
            created_at: Creation timestamp (Unix epoch)
            modified_at: Modification timestamp (Unix epoch)

        Returns:
            Path to created file

        Raises:
            ValueError: If folder contains path traversal or file path escapes vault

        Note:
            - Filename is sanitized from title (spaces to hyphens, lowercase)
            - YAML frontmatter is added automatically
            - Relations stored in frontmatter for backlink compatibility
        """
        # Validate folder path (prevents path traversal)
        if folder:
            folder = validate_folder_path(folder, "folder")

        # Sanitize filename (prevents path traversal via filename)
        filename = sanitize_filename(title, "title") + ".md"

        # Determine full path
        if folder:
            folder_path = self.vault_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            file_path = folder_path / filename
        else:
            file_path = self.vault_path / filename

        # Final safeguard: ensure path is within vault (prevents symlink attacks)
        file_path = ensure_within_directory(file_path, self.vault_path, "file_path")

        # Build frontmatter
        fm: dict[str, Any] = {
            "title": title,
            "created": datetime.fromtimestamp(created_at or int(time.time())).isoformat(),
            "modified": datetime.fromtimestamp(modified_at or int(time.time())).isoformat(),
        }

        if tags:
            fm["tags"] = tags

        if wikilinks:
            fm["links"] = wikilinks

        # Add custom metadata
        if metadata:
            fm.update(metadata)

        # Create frontmatter post
        post = frontmatter.Post(content, **fm)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

        return file_path

    def update_note(
        self,
        file_path: Path,
        content: str | None = None,
        *,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        append_content: str | None = None,
    ) -> None:
        """
        Update an existing note.

        Args:
            file_path: Path to note file
            content: New content (replaces existing if provided)
            tags: New tags (replaces existing if provided)
            metadata: Metadata to update (merged with existing)
            append_content: Content to append to existing content

        Raises:
            FileNotFoundError: If note doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Note not found: {file_path}")

        # Load existing note
        with open(file_path, encoding="utf-8") as f:
            post = frontmatter.load(f)

        # Update content
        if content is not None:
            post.content = content
        elif append_content is not None:
            post.content += "\n\n" + append_content

        # Update metadata
        if tags is not None:
            post["tags"] = tags

        if metadata:
            for key, value in metadata.items():
                post[key] = value

        # Update modified timestamp
        post["modified"] = datetime.now().isoformat()

        # Write updated note
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

    def read_note(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """
        Read a markdown note.

        Args:
            file_path: Path to note file

        Returns:
            Tuple of (content, frontmatter_dict)

        Raises:
            FileNotFoundError: If note doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Note not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            post = frontmatter.load(f)

        return post.content, dict(post.metadata)

    def delete_note(self, file_path: Path) -> None:
        """
        Delete a note.

        Args:
            file_path: Path to note file

        Raises:
            FileNotFoundError: If note doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Note not found: {file_path}")

        file_path.unlink()

    def find_note_by_title(self, title: str) -> Path | None:
        """
        Find a note by its title (from frontmatter).

        Args:
            title: Title to search for

        Returns:
            Path to note if found, None otherwise
        """
        # Search all markdown files
        for md_file in self.vault_path.rglob("*.md"):
            try:
                with open(md_file, encoding="utf-8") as f:
                    post = frontmatter.load(f)
                    if post.get("title") == title:
                        return md_file
            except Exception:  # nosec B112 - intentionally skipping unparseable files
                # Skip files that can't be parsed
                continue

        return None

    def _sanitize_filename(self, title: str) -> str:
        """
        Sanitize a title for use as filename.

        This method is deprecated and maintained for backwards compatibility.
        New code should use sanitize_filename() from security.paths directly.

        Args:
            title: Title to sanitize

        Returns:
            Sanitized filename (without extension)

        Raises:
            ValueError: If title is invalid

        Examples:
            >>> _sanitize_filename("My Note Title")
            'my-note-title'
            >>> _sanitize_filename("Invalid/Name?")
            'invalid-name'
        """
        # Use the security module's sanitize_filename function
        # Note: The old implementation was less strict; this might reject some edge cases
        try:
            return sanitize_filename(title, "title")
        except ValueError:
            # Fallback for backward compatibility: return "untitled"
            return "untitled"

    def get_note_path(self, title: str, folder: str = "") -> Path:
        """
        Get the expected path for a note given its title and folder.

        Args:
            title: Note title
            folder: Subfolder within vault

        Returns:
            Expected path to note file

        Raises:
            ValueError: If folder contains path traversal
        """
        # Validate folder path
        if folder:
            folder = validate_folder_path(folder, "folder")

        filename = sanitize_filename(title, "title") + ".md"

        if folder:
            file_path = self.vault_path / folder / filename
        else:
            file_path = self.vault_path / filename

        # Ensure within vault
        return ensure_within_directory(file_path, self.vault_path, "file_path")

    def list_notes(self, folder: str | None = None) -> list[Path]:
        """
        List all notes in vault or a specific folder.

        Args:
            folder: Optional folder to filter by

        Returns:
            List of paths to markdown files

        Raises:
            ValueError: If folder contains path traversal
        """
        # Validate folder path
        if folder:
            folder = validate_folder_path(folder, "folder")
            search_path = self.vault_path / folder
            # Ensure search path is within vault
            search_path = ensure_within_directory(search_path, self.vault_path, "search_path")
        else:
            search_path = self.vault_path

        if not search_path.exists():
            return []

        return list(search_path.rglob("*.md"))

    def create_folder(self, folder_name: str) -> Path:
        """
        Create a folder in the vault.

        Args:
            folder_name: Name of folder to create

        Returns:
            Path to created folder

        Raises:
            ValueError: If folder_name contains path traversal
        """
        # Validate folder path
        folder_name = validate_folder_path(folder_name, "folder_name")

        folder_path = self.vault_path / folder_name

        # Ensure folder is within vault
        folder_path = ensure_within_directory(folder_path, self.vault_path, "folder_path")

        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path


def main() -> int:
    """CLI entry point for markdown writer operations."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Write markdown notes to Obsidian vault")
    parser.add_argument(
        "vault_path",
        type=Path,
        help="Path to Obsidian vault",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new note")
    create_parser.add_argument("title", help="Note title")
    create_parser.add_argument("content", help="Note content")
    create_parser.add_argument("--folder", default="", help="Folder within vault")
    create_parser.add_argument("--tags", nargs="+", help="Tags for the note")

    # List command
    list_parser = subparsers.add_parser("list", help="List notes")
    list_parser.add_argument("--folder", help="Folder to list")

    # Read command
    read_parser = subparsers.add_parser("read", help="Read a note")
    read_parser.add_argument("title", help="Note title to read")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        writer = MarkdownWriter(vault_path=args.vault_path)

        if args.command == "create":
            file_path = writer.write_note(
                title=args.title,
                content=args.content,
                folder=args.folder,
                tags=args.tags,
            )
            print(f"✓ Note created: {file_path}")

        elif args.command == "list":
            notes = writer.list_notes(folder=args.folder)
            print(f"\nNotes ({len(notes)}):\n")
            for note_file in notes:
                print(f"  - {note_file.relative_to(writer.vault_path)}")

        elif args.command == "read":
            note_path = writer.find_note_by_title(args.title)
            if not note_path:
                print(f"Note not found: {args.title}", file=sys.stderr)
                return 1

            content, metadata = writer.read_note(note_path)
            print(f"\n{note_path}:")
            print(f"\nMetadata: {metadata}")
            print(f"\nContent:\n{content}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
