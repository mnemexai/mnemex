"""Long-Term Memory index for Obsidian vault.

Index markdown files in the vault for fast search without scanning every file.
"""

import json
import re
import time
from pathlib import Path
from typing import Any

import frontmatter

from ..config import get_config


class LTMDocument:
    """A document in the LTM index."""

    def __init__(
        self,
        path: str,
        title: str,
        content: str,
        frontmatter: dict[str, Any],
        wikilinks: list[str],
        tags: list[str],
        mtime: float,
        size: int,
    ):
        self.path = path
        self.title = title
        self.content = content
        self.frontmatter = frontmatter
        self.wikilinks = wikilinks
        self.tags = tags
        self.mtime = mtime
        self.size = size

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "title": self.title,
            "content": self.content,
            "frontmatter": self.frontmatter,
            "wikilinks": self.wikilinks,
            "tags": self.tags,
            "mtime": self.mtime,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LTMDocument":
        """Create from dictionary."""
        return cls(
            path=data["path"],
            title=data["title"],
            content=data["content"],
            frontmatter=data.get("frontmatter", {}),
            wikilinks=data.get("wikilinks", []),
            tags=data.get("tags", []),
            mtime=data["mtime"],
            size=data["size"],
        )


class LTMIndex:
    """Index of Long-Term Memory documents in Obsidian vault."""

    # Pattern for extracting wikilinks: [[link]] or [[link|alias]]
    WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

    # Pattern for extracting hashtags: #tag
    HASHTAG_PATTERN = re.compile(r"#([a-zA-Z0-9_/-]+)")

    def __init__(self, vault_path: Path, index_path: Path | None = None):
        """
        Initialize LTM index.

        Args:
            vault_path: Path to Obsidian vault directory
            index_path: Path to index JSONL file (default: vault_path/.cortexgraph-index.jsonl)
        """
        self.vault_path = vault_path
        self.config = get_config()

        # Prefer new default path; fallback to legacy if it exists
        if index_path is None:
            new_filename = self.config.ltm_index_filename
            legacy_filename = self.config.ltm_legacy_index_filename
            new_path = vault_path / new_filename
            legacy_path = vault_path / legacy_filename
            if new_path.exists() or not legacy_path.exists():
                self.index_path = new_path
            else:
                self.index_path = legacy_path
        else:
            self.index_path = index_path

        # In-memory index
        self._documents: dict[str, LTMDocument] = {}

        # Statistics
        self.stats = {
            "total_documents": 0,
            "total_wikilinks": 0,
            "last_indexed": 0,
            "index_time_ms": 0,
        }

    def extract_wikilinks(self, content: str) -> list[str]:
        """
        Extract wikilinks from markdown content.

        Args:
            content: Markdown content

        Returns:
            List of wikilink targets (without brackets)
        """
        matches = self.WIKILINK_PATTERN.findall(content)
        return list(set(matches))  # Deduplicate

    def extract_hashtags(self, content: str) -> list[str]:
        """
        Extract hashtags from markdown content.

        Args:
            content: Markdown content

        Returns:
            List of hashtags (without #)
        """
        matches = self.HASHTAG_PATTERN.findall(content)
        return list(set(matches))  # Deduplicate

    def parse_markdown_file(self, file_path: Path) -> LTMDocument | None:
        """
        Parse a markdown file and extract metadata.

        Args:
            file_path: Path to markdown file

        Returns:
            LTMDocument or None if parsing fails
        """
        try:
            # Read file with frontmatter parsing
            with open(file_path, encoding="utf-8") as f:
                post = frontmatter.load(f)

            # Extract title (from frontmatter or filename)
            title_raw = post.get("title", file_path.stem)
            title = str(title_raw) if title_raw else file_path.stem

            # Extract tags from frontmatter
            fm_tags_raw = post.get("tags", [])
            if isinstance(fm_tags_raw, str):
                fm_tags: list[str] = [fm_tags_raw]
            elif isinstance(fm_tags_raw, list):
                fm_tags = fm_tags_raw
            else:
                fm_tags = []

            # Extract hashtags from content
            content_tags = self.extract_hashtags(post.content)

            # Combine tags
            all_tags = list(set(fm_tags + content_tags))

            # Extract wikilinks
            wikilinks = self.extract_wikilinks(post.content)

            # Get file stats
            stat = file_path.stat()

            # Create relative path from vault root (use POSIX style for cross-platform consistency)
            rel_path = file_path.relative_to(self.vault_path).as_posix()

            return LTMDocument(
                path=rel_path,
                title=title,
                content=post.content,
                frontmatter=dict(post.metadata),
                wikilinks=wikilinks,
                tags=all_tags,
                mtime=stat.st_mtime,
                size=stat.st_size,
            )

        except Exception as e:
            # Log error but don't fail entire index
            print(f"Warning: Failed to parse {file_path}: {e}")
            return None

    def build_index(self, force: bool = False, verbose: bool = False) -> None:
        """
        Build or update the index by scanning vault directory.

        Args:
            force: If True, rebuild entire index. If False, only update changed files.
            verbose: If True, print progress information
        """
        start_time = time.time()

        if not self.vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {self.vault_path}")

        # Load existing index if not forcing rebuild
        if not force and self.index_path.exists():
            self.load_index()
            if verbose:
                print(f"Loaded existing index with {len(self._documents)} documents")

        # Find all markdown files
        markdown_files = list(self.vault_path.rglob("*.md"))

        if verbose:
            print(f"Found {len(markdown_files)} markdown files in vault")

        # Track which files we've seen (for detecting deletions)
        seen_paths: set[str] = set()

        # Index each file
        updated_count = 0
        skipped_count = 0

        for file_path in markdown_files:
            rel_path = file_path.relative_to(self.vault_path).as_posix()
            seen_paths.add(rel_path)

            # Check if file needs updating (incremental mode)
            if not force:
                existing_doc = self._documents.get(rel_path)
                if existing_doc and existing_doc.mtime >= file_path.stat().st_mtime:
                    skipped_count += 1
                    continue

            # Parse and index file
            doc = self.parse_markdown_file(file_path)
            if doc:
                self._documents[rel_path] = doc
                updated_count += 1

                if verbose and updated_count % 100 == 0:
                    print(f"  ... indexed {updated_count} files")

        # Remove deleted files from index
        deleted_count = 0
        for path in list(self._documents.keys()):
            if path not in seen_paths:
                del self._documents[path]
                deleted_count += 1

        # Update statistics
        self.stats = {
            "total_documents": len(self._documents),
            "total_wikilinks": sum(len(doc.wikilinks) for doc in self._documents.values()),
            "last_indexed": int(time.time()),
            "index_time_ms": int((time.time() - start_time) * 1000),
        }

        if verbose:
            print("\nIndex built:")
            print(f"  Updated: {updated_count}")
            print(f"  Skipped: {skipped_count}")
            print(f"  Deleted: {deleted_count}")
            print(f"  Total: {self.stats['total_documents']} documents")
            print(f"  Time: {self.stats['index_time_ms']}ms")

        # Save index
        self.save_index()

    def save_index(self) -> None:
        """Save index to JSONL file."""
        with open(self.index_path, "w") as f:
            # Write metadata
            f.write(json.dumps({"_stats": self.stats}) + "\n")

            # Write documents
            for doc in self._documents.values():
                f.write(json.dumps(doc.to_dict()) + "\n")

    def load_index(self) -> None:
        """Load index from JSONL file."""
        if not self.index_path.exists():
            return

        self._documents.clear()

        with open(self.index_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                data = json.loads(line)

                # Check for metadata
                if "_stats" in data:
                    self.stats = data["_stats"]
                else:
                    doc = LTMDocument.from_dict(data)
                    self._documents[doc.path] = doc

    def search(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[LTMDocument]:
        """
        Search index for documents.

        Args:
            query: Text query (searches in title and content)
            tags: Filter by tags
            limit: Maximum results

        Returns:
            List of matching LTMDocument objects
        """
        results = list(self._documents.values())

        # Filter by tags
        if tags:
            results = [doc for doc in results if any(tag in doc.tags for tag in tags)]

        # Filter by query (simple substring match)
        if query:
            query_lower = query.lower()
            results = [
                doc
                for doc in results
                if query_lower in doc.title.lower() or query_lower in doc.content.lower()
            ]

        # Sort by relevance (for now, just by title match then content length)
        if query:

            def score_doc(doc: LTMDocument) -> tuple[int, int]:
                title_match = 1 if query.lower() in doc.title.lower() else 0
                return (title_match, -len(doc.content))  # Negative for descending

            results.sort(key=score_doc, reverse=True)

        return results[:limit]

    def get_document(self, path: str) -> LTMDocument | None:
        """
        Get a document by path.

        Args:
            path: Relative path from vault root

        Returns:
            LTMDocument or None
        """
        return self._documents.get(path)

    def get_documents_by_tag(self, tag: str) -> list[LTMDocument]:
        """
        Get all documents with a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of documents with the tag
        """
        return [doc for doc in self._documents.values() if tag in doc.tags]

    def get_backlinks(self, title: str) -> list[LTMDocument]:
        """
        Get all documents that link to a given note.

        Args:
            title: Title of the note (wikilink target)

        Returns:
            List of documents containing wikilinks to this title
        """
        return [doc for doc in self._documents.values() if title in doc.wikilinks]

    def get_forward_links(self, path: str) -> list[LTMDocument]:
        """
        Get all documents linked from a given note.

        Args:
            path: Path to the source document

        Returns:
            List of linked documents
        """
        doc = self._documents.get(path)
        if not doc:
            return []

        # Find documents by wikilink
        linked_docs = []
        for wikilink in doc.wikilinks:
            # Try to find document by title
            for candidate in self._documents.values():
                if candidate.title == wikilink:
                    linked_docs.append(candidate)
                    break

        return linked_docs

    def get_stats(self) -> dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Dictionary with statistics
        """
        return self.stats.copy()

    def add_document(self, file_path: Path) -> bool:
        """
        Add or update a single document in the index.

        Incrementally adds a new document without rebuilding the entire index.
        Useful for keeping index up-to-date when files are added.

        Args:
            file_path: Absolute path to the markdown file to add

        Returns:
            True if document was added/updated, False if parsing failed
        """
        if not file_path.exists():
            print(f"Warning: File does not exist: {file_path}")
            return False

        # Parse the file
        doc = self.parse_markdown_file(file_path)
        if not doc:
            return False

        # Add to index
        self._documents[doc.path] = doc

        # Update statistics
        self.stats["total_documents"] = len(self._documents)
        self.stats["total_wikilinks"] = sum(len(doc.wikilinks) for doc in self._documents.values())
        self.stats["last_indexed"] = int(time.time())

        # Save updated index
        self.save_index()

        return True


def main() -> int:
    """CLI entry point for LTM indexer."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Build LTM index for Obsidian vault")
    parser.add_argument(
        "vault_path",
        type=Path,
        help="Path to Obsidian vault",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        help="Path to index file (default: vault/.cortexgraph-index.jsonl; legacy .stm-index.jsonl supported)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild of entire index",
    )
    parser.add_argument(
        "--search",
        type=str,
        help="Search the index after building",
    )
    parser.add_argument(
        "--tag",
        type=str,
        help="Filter by tag",
    )

    args = parser.parse_args()

    try:
        # Build index
        index = LTMIndex(vault_path=args.vault_path, index_path=args.index_path)
        index.build_index(force=args.force, verbose=True)

        # Search if requested
        if args.search or args.tag:
            tags = [args.tag] if args.tag else None
            results = index.search(query=args.search, tags=tags, limit=20)

            print(f"\nSearch results ({len(results)}):")
            for doc in results:
                print(f"  - {doc.title} ({doc.path})")
                if doc.tags:
                    print(f"    Tags: {', '.join(doc.tags)}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
