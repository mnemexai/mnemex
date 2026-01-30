"""LTM Promoter agent for moving high-value memories to long-term storage.

This agent identifies memories meeting promotion criteria and writes them
to the Obsidian vault as permanent markdown files.

From contracts/agent-api.md:
    Scan Contract:
        - MUST find memories meeting promotion criteria
        - MUST NOT return already-promoted memories

    Process Contract:
        - MUST write valid markdown to vault
        - MUST set memory status to 'promoted'
        - MUST store vault_path reference
        - MUST NOT create duplicate vault files
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from cortexgraph.agents.base import ConsolidationAgent
from cortexgraph.agents.beads_integration import (
    close_issue,
    create_consolidation_issue,
)
from cortexgraph.agents.models import PromotionResult
from cortexgraph.agents.storage_utils import get_storage
from cortexgraph.core.scoring import should_promote
from cortexgraph.storage.models import MemoryStatus
from cortexgraph.vault.markdown_writer import MarkdownWriter

if TYPE_CHECKING:
    from cortexgraph.storage.jsonl_storage import JSONLStorage
    from cortexgraph.storage.models import Memory


def get_vault_path() -> Path:
    """Get vault path from config. Separated for testability."""
    vault_path = os.environ.get("LTM_VAULT_PATH", "~/.cortexgraph/vault")
    return Path(vault_path).expanduser()


logger = logging.getLogger(__name__)


class LTMPromoter(ConsolidationAgent[PromotionResult]):
    """Moves high-value memories to long-term storage.

    Unlike DecayAnalyzer and ClusterDetector which create beads issues,
    LTMPromoter scans storage directly for promotion candidates and
    writes them to the Obsidian vault.

    Example:
        >>> promoter = LTMPromoter(dry_run=True)
        >>> memory_ids = promoter.scan()  # Returns memory IDs meeting criteria
        >>> for mem_id in memory_ids:
        ...     result = promoter.process_item(mem_id)
        ...     print(f"Promoted {result.memory_id} to {result.vault_path}")
    """

    def __init__(
        self,
        dry_run: bool = False,
        rate_limit: int = 100,
        vault_path: Path | None = None,
    ) -> None:
        """Initialize LTMPromoter agent.

        Args:
            dry_run: If True, preview promotions without making changes
            rate_limit: Max operations per minute
            vault_path: Path to Obsidian vault (defaults to LTM_VAULT_PATH env var)
        """
        super().__init__(dry_run=dry_run, rate_limit=rate_limit)
        self._storage: "JSONLStorage | None" = None
        self._writer: MarkdownWriter | None = None
        self._vault_path = vault_path or get_vault_path()
        self._promotion_candidates: dict[str, tuple[bool, str, float]] = {}

    @property
    def storage(self) -> "JSONLStorage":
        """Get storage instance (lazy initialization)."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    @property
    def writer(self) -> MarkdownWriter:
        """Get vault writer instance (lazy initialization)."""
        if self._writer is None:
            self._writer = MarkdownWriter(self._vault_path)
        return self._writer

    def scan(self) -> list[str]:
        """Scan storage for memories meeting promotion criteria.

        Returns:
            List of memory IDs to process

        Contract:
            - MUST find memories meeting promotion criteria
            - MUST NOT return already-promoted memories
            - MUST NOT modify any data
        """
        candidates: list[str] = []
        self._promotion_candidates = {}

        # Get all memories from storage
        memories: dict[str, Memory] = {}

        # Try direct dict access first (for tests/mocks)
        if hasattr(self.storage, "memories") and isinstance(self.storage.memories, dict):
            memories = self.storage.memories
        else:
            # Try storage methods for real storage
            try:
                if hasattr(self.storage, "get_all_memories"):
                    memories = {m.id: m for m in self.storage.get_all_memories()}  # pyright: ignore[reportAttributeAccessIssue]
            except RuntimeError:
                logger.warning("Storage not connected, cannot scan")
                return []

        for mem_id, memory in memories.items():
            # Skip non-active memories
            status = getattr(memory, "status", MemoryStatus.ACTIVE)
            if status != MemoryStatus.ACTIVE:
                continue

            # Check promotion criteria (gracefully handle broken memories)
            try:
                should, reason, score = should_promote(memory)
                if should:
                    candidates.append(mem_id)
                    self._promotion_candidates[mem_id] = (should, reason, score)
                    logger.debug(f"Promotion candidate: {mem_id} ({reason})")
            except Exception as e:
                logger.warning(f"Skipping memory {mem_id} due to error: {e}")

        logger.info(f"LTMPromoter scan found {len(candidates)} promotion candidates")
        return candidates

    def process_item(self, memory_id: str) -> PromotionResult:
        """Process a single memory for promotion.

        Args:
            memory_id: UUID of memory to promote

        Returns:
            PromotionResult with promotion outcome

        Contract:
            - MUST write valid markdown to vault
            - MUST set memory status to 'promoted'
            - MUST store vault_path reference
            - MUST NOT create duplicate vault files
            - If dry_run=True, MUST NOT modify any data

        Raises:
            ValueError: If memory_id is invalid or memory not found
            RuntimeError: If promotion fails
        """
        # Get memory from storage
        memory: Memory | None = None

        # Try direct dict access first (for tests/mocks)
        if hasattr(self.storage, "memories") and isinstance(self.storage.memories, dict):
            memory = self.storage.memories.get(memory_id)

        # Then try storage methods
        if memory is None:
            try:
                if hasattr(self.storage, "get_memory"):
                    memory = self.storage.get_memory(memory_id)
            except RuntimeError:
                pass

        if memory is None:
            raise ValueError(f"Memory not found: {memory_id}")

        # Get promotion info from cache or recalculate
        if memory_id in self._promotion_candidates:
            _, reason, score = self._promotion_candidates[memory_id]
        else:
            should, reason, score = should_promote(memory)
            if not should:
                raise ValueError(f"Memory {memory_id} does not meet promotion criteria")

        # Parse criteria from reason string
        criteria_met = self._parse_criteria(reason)

        if self.dry_run:
            # Dry run - don't modify anything
            logger.info(f"[DRY RUN] Would promote {memory_id}: {reason}")
            return PromotionResult(
                memory_id=memory_id,
                vault_path=None,  # No path in dry run
                criteria_met=criteria_met,
                success=True,
                beads_issue_id=None,
            )

        # === LIVE MODE: Actually perform the promotion ===

        try:
            # Check for duplicates
            title = self._generate_title(memory)
            existing = self.writer.find_note_by_title(title)
            if existing is not None:
                logger.warning(f"Duplicate vault file exists: {existing}")
                return PromotionResult(
                    memory_id=memory_id,
                    vault_path=str(existing),
                    criteria_met=criteria_met,
                    success=False,
                    beads_issue_id=None,
                )

            # Create beads issue for audit trail
            issue_id = create_consolidation_issue(
                agent="promote",
                memory_ids=[memory_id],
                action="promote",
                urgency="low",
                extra_data={"reason": reason, "score": score},
            )

            # Write to vault
            content = self._generate_content(memory)
            entities = getattr(memory, "entities", []) or []
            tags = getattr(memory, "tags", []) or []
            created_at = getattr(memory, "created_at", None)
            last_used = getattr(memory, "last_used", None)

            vault_path = self.writer.write_note(
                title=title,
                content=content,
                folder="memories",
                tags=tags,
                metadata={
                    "memory_id": memory_id,
                    "entities": entities,
                    "promotion_reason": reason,
                    "decay_score": score,
                },
                created_at=created_at,
                modified_at=last_used,
            )
            logger.info(f"Wrote memory to vault: {vault_path}")

            # Update memory status to promoted
            self.storage.update_memory(memory_id, status=MemoryStatus.PROMOTED)
            logger.info(f"Updated memory status to PROMOTED: {memory_id}")

            # Close beads issue
            close_issue(issue_id, f"Promoted to {vault_path}")

            return PromotionResult(
                memory_id=memory_id,
                vault_path=str(vault_path),
                criteria_met=criteria_met,
                success=True,
                beads_issue_id=issue_id,
            )

        except Exception as e:
            logger.error(f"Promotion failed for {memory_id}: {e}")
            raise RuntimeError(f"Promotion failed: {e}") from e

    def _parse_criteria(self, reason: str) -> list[str]:
        """Parse promotion criteria from reason string.

        Args:
            reason: Reason string from should_promote()

        Returns:
            List of criteria names that were met
        """
        criteria = []

        if "score" in reason.lower() or "high score" in reason.lower():
            criteria.append("score_threshold")

        if "use count" in reason.lower() or "use_count" in reason.lower():
            criteria.append("use_count_threshold")

        if "review" in reason.lower():
            criteria.append("review_count_threshold")

        # Ensure at least one criterion
        if not criteria:
            criteria.append("score_threshold")

        return criteria

    def _generate_title(self, memory: Memory) -> str:
        """Generate a title for the vault note.

        Args:
            memory: Memory to generate title for

        Returns:
            Title string
        """
        content = getattr(memory, "content", "") or ""
        entities = getattr(memory, "entities", []) or []

        # Use first entity + truncated content
        if entities:
            prefix = entities[0]
            # Take first 50 chars of content
            snippet = content[:50].strip()
            if len(content) > 50:
                snippet += "..."
            return f"{prefix} - {snippet}"

        # Fallback to memory ID
        return f"Memory {memory.id[:8]}"

    def _generate_content(self, memory: Memory) -> str:
        """Generate markdown content for the vault note.

        Args:
            memory: Memory to convert to markdown

        Returns:
            Markdown content string
        """
        content = getattr(memory, "content", "") or ""
        entities = getattr(memory, "entities", []) or []

        lines = [
            "## Content",
            "",
            content,
            "",
        ]

        if entities:
            lines.extend(
                [
                    "## Entities",
                    "",
                    ", ".join(f"[[{e}]]" for e in entities),
                    "",
                ]
            )

        return "\n".join(lines)
