"""Integration with Basic Memory MCP for long-term storage."""

import time
from typing import Any

from ..config import get_config
from ..storage.models import Memory


class BasicMemoryIntegration:
    """Integration with Basic Memory for promoting memories to Obsidian vault."""

    def __init__(self) -> None:
        """Initialize the Basic Memory integration."""
        self.config = get_config()
        self.vault_path = self.config.ltm_vault_path

    def is_available(self) -> bool:
        """Check if Basic Memory vault is configured and accessible."""
        if self.vault_path is None:
            return False
        return self.vault_path.exists() and self.vault_path.is_dir()

    def _sanitize_filename(self, content: str) -> str:
        """Create a safe filename from content."""
        # Take first 50 chars, remove special characters
        filename = content[:50].strip()
        # Replace spaces and special chars with hyphens
        filename = "".join(c if c.isalnum() or c in (" ", "-", "_") else "-" for c in filename)
        # Collapse multiple hyphens
        while "--" in filename:
            filename = filename.replace("--", "-")
        return filename.strip("-")

    def _create_markdown_note(self, memory: Memory) -> str:
        """
        Create Markdown content for a memory note.

        Follows Basic Memory / Obsidian conventions:
        - YAML frontmatter with metadata
        - Clear sections
        - Tags and links
        """
        tags_str = ", ".join(memory.meta.tags) if memory.meta.tags else ""

        # Build frontmatter
        frontmatter_lines = [
            "---",
            f"created: {time.strftime('%Y-%m-%d', time.localtime(memory.created_at))}",
            f"last_used: {time.strftime('%Y-%m-%d', time.localtime(memory.last_used))}",
            f"use_count: {memory.use_count}",
            f"stm_id: {memory.id}",
        ]

        if tags_str:
            frontmatter_lines.append(f"tags: [{tags_str}]")

        if memory.meta.source:
            frontmatter_lines.append(f"source: {memory.meta.source}")

        frontmatter_lines.append("---")
        frontmatter_lines.append("")

        # Build content sections
        content_lines = [
            f"# {self._sanitize_filename(memory.content)}",
            "",
            "## Content",
            "",
            memory.content,
            "",
        ]

        if memory.meta.context:
            content_lines.extend(
                [
                    "## Context",
                    "",
                    memory.meta.context,
                    "",
                ]
            )

        # Add metadata section
        content_lines.extend(
            [
                "## Metadata",
                "",
                f"- **Created**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(memory.created_at))}",
                f"- **Last Used**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(memory.last_used))}",
                f"- **Use Count**: {memory.use_count}",
                f"- **Strength**: {memory.strength}",
                "",
            ]
        )

        if memory.meta.tags:
            content_lines.append(f"**Tags**: #{' #'.join(memory.meta.tags)}")
            content_lines.append("")

        # Footer
        content_lines.extend(
            [
                "---",
                "",
                "*Promoted from STM (Short-Term Memory) server*",
            ]
        )

        return "\n".join(frontmatter_lines + content_lines)

    def promote_to_obsidian(self, memory: Memory) -> dict[str, Any]:
        """
        Promote a memory to the Obsidian vault.

        Args:
            memory: Memory to promote

        Returns:
            Dictionary with success status and path
        """
        if not self.is_available():
            return {
                "success": False,
                "message": "Basic Memory vault not configured or not accessible",
                "vault_path": str(self.vault_path) if self.vault_path else None,
            }

        # Create filename from content
        filename = self._sanitize_filename(memory.content)
        if not filename:
            filename = f"memory-{memory.id[:8]}"

        # Ensure uniqueness
        assert self.vault_path is not None
        base_path = self.vault_path / "STM"
        base_path.mkdir(exist_ok=True)

        file_path = base_path / f"{filename}.md"
        counter = 1
        while file_path.exists():
            file_path = base_path / f"{filename}-{counter}.md"
            counter += 1

        # Generate markdown content
        markdown_content = self._create_markdown_note(memory)

        # Write to file
        try:
            file_path.write_text(markdown_content, encoding="utf-8")

            return {
                "success": True,
                "message": "Memory promoted to Obsidian vault",
                "path": str(file_path.relative_to(self.vault_path)),
                "full_path": str(file_path),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to write memory to vault: {e}",
                "path": str(file_path),
            }

    def get_vault_stats(self) -> dict[str, Any]:
        """Get statistics about the vault."""
        if not self.is_available():
            return {
                "available": False,
                "vault_path": str(self.vault_path) if self.vault_path else None,
            }

        assert self.vault_path is not None
        stm_folder = self.vault_path / "STM"
        if not stm_folder.exists():
            note_count = 0
        else:
            note_count = len(list(stm_folder.glob("*.md")))

        return {
            "available": True,
            "vault_path": str(self.vault_path),
            "stm_notes_count": note_count,
        }
