"""Export utility to save memories as Markdown files."""

import datetime
import logging
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from ..storage.models import Memory


class ExportStats(BaseModel):
    """Statistics for the export operation."""

    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0


class MarkdownExport:
    """Export memories to Markdown files with YAML frontmatter."""

    def __init__(self, output_dir: Path) -> None:
        """
        Initialize the exporter.

        Args:
            output_dir: Directory to save exported files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, text: str) -> str:
        """Create a safe filename from text."""
        # Remove invalid chars
        s = re.sub(r'[<>:"/\\|?*]', "", text)
        # Replace spaces with dashes
        s = s.replace(" ", "-")
        # Truncate to reasonable length
        return s[:50]

    def _format_frontmatter(self, memory: Memory) -> str:
        """Format memory metadata as YAML frontmatter."""
        # Format frontmatter
        frontmatter: dict[str, Any] = {
            "id": memory.id,
            "created_at": datetime.datetime.fromtimestamp(memory.created_at).isoformat(),
            "last_used": datetime.datetime.fromtimestamp(memory.last_used).isoformat(),
            "status": memory.status.value,
            "tags": memory.meta.tags,
            "use_count": memory.use_count,
            "strength": memory.strength,
        }

        # Add optional fields if present
        if memory.meta.source:
            frontmatter["source"] = memory.meta.source
        if memory.meta.context:
            frontmatter["context"] = memory.meta.context
        if memory.meta.extra:
            frontmatter["extra"] = memory.meta.extra
        if memory.entities:
            frontmatter["entities"] = memory.entities

        return str(yaml.dump(frontmatter, sort_keys=False, allow_unicode=True))

    def export_memory(self, memory: Memory) -> bool:
        """
        Export a single memory to a markdown file.

        Args:
            memory: Memory object to export

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate filename from content preview or ID
            content_preview = memory.content.split("\n")[0].strip()
            if not content_preview:
                filename = f"{memory.id}.md"
            else:
                safe_name = self._sanitize_filename(content_preview)
                filename = f"{safe_name}-{memory.id[:8]}.md"

            file_path = self.output_dir / filename

            frontmatter = self._format_frontmatter(memory)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"---\n{frontmatter}---\n\n")
                f.write(memory.content)
                f.write("\n")

            return True
        except Exception as e:
            logging.error(f"Failed to export memory {memory.id}: {e}")
            return False

    def export_batch(self, memories: list[Memory]) -> ExportStats:
        """
        Export a batch of memories.

        Args:
            memories: List of memories to export

        Returns:
            Export statistics
        """
        stats = ExportStats(total=len(memories))

        for memory in memories:
            if self.export_memory(memory):
                stats.success += 1
            else:
                stats.failed += 1

        return stats
