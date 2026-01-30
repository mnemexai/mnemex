"""Semantic Merge agent for intelligent memory consolidation.

This agent processes merge requests from ClusterDetector, combining similar
memories while preserving all unique information.

From contracts/agent-api.md:
    Scan Contract:
        - MUST only process from beads issues (not free scan)
        - MUST filter for consolidation:merge label

    Process Contract:
        - MUST preserve all unique entities
        - MUST preserve all unique content
        - MUST create consolidated_from relations
        - MUST archive (not delete) originals
        - MUST close beads issue on success
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

from cortexgraph.agents.base import ConsolidationAgent

if TYPE_CHECKING:
    from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.agents.beads_integration import (
    claim_issue,
    close_issue,
    query_consolidation_issues,
)
from cortexgraph.agents.models import MergeResult
from cortexgraph.agents.storage_utils import get_storage
from cortexgraph.core.consolidation import (
    calculate_merged_strength,
    merge_content_smart,
    merge_entities,
    merge_metadata,
)
from cortexgraph.storage.models import Memory, MemoryStatus, Relation

logger = logging.getLogger(__name__)


class SemanticMerge(ConsolidationAgent[MergeResult]):
    """Combines clustered memories intelligently.

    Unlike DecayAnalyzer and ClusterDetector which scan storage directly,
    SemanticMerge reads from beads issues created by ClusterDetector.
    This queue-based approach allows for human oversight and audit trails.

    Example:
        >>> merge = SemanticMerge(dry_run=True)
        >>> issue_ids = merge.scan()  # Returns beads issue IDs
        >>> for issue_id in issue_ids:
        ...     result = merge.process_item(issue_id)
        ...     print(f"Merged {len(result.source_ids)} into {result.new_memory_id}")
    """

    def __init__(
        self,
        dry_run: bool = False,
        rate_limit: int = 100,
    ) -> None:
        """Initialize SemanticMerge agent.

        Args:
            dry_run: If True, preview merges without making changes
            rate_limit: Max operations per minute
        """
        super().__init__(dry_run=dry_run, rate_limit=rate_limit)
        self._storage: "JSONLStorage | None" = None
        self._pending_issues: dict[str, dict[str, Any]] = {}  # Cache issue data by ID

    @property
    def storage(self) -> "JSONLStorage":
        """Get storage instance (lazy initialization)."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def scan(self) -> list[str]:
        """Scan beads for merge issues from ClusterDetector.

        Returns:
            List of beads issue IDs to process

        Contract:
            - MUST only process from beads issues (not free scan)
            - MUST filter for consolidation:merge label
            - MUST NOT modify any data
        """
        # Query beads for merge issues
        issues = query_consolidation_issues(agent="merge", status="open")

        # Cache issue data for process_item
        self._pending_issues = {issue["id"]: issue for issue in issues}

        # Return issue IDs
        return list(self._pending_issues.keys())

    def process_item(self, memory_id: str) -> MergeResult:
        """Process a single merge request from beads.

        Args:
            memory_id: Beads issue ID containing merge request

        Returns:
            MergeResult with merge outcome

        Contract:
            - MUST preserve all unique entities
            - MUST preserve all unique content
            - MUST create consolidated_from relations
            - MUST archive (not delete) originals
            - MUST close beads issue on success
            - If dry_run=True, MUST NOT modify any data

        Raises:
            ValueError: If memory_id is invalid or memories not found
            RuntimeError: If merge fails
        """
        # Get issue data
        issue = self._pending_issues.get(memory_id)
        if not issue:
            # Try to fetch from beads
            issues = query_consolidation_issues(agent="merge", status="open")
            for i in issues:
                if i["id"] == memory_id:
                    issue = i
                    break

        if not issue:
            raise ValueError(f"Unknown beads issue: {memory_id}")

        # Parse issue notes for memory IDs
        try:
            notes = json.loads(issue.get("notes", "{}"))
            memory_ids = notes.get("memory_ids", [])
            cluster_id = notes.get("cluster_id", "unknown")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid notes JSON in issue {memory_id}") from e

        if len(memory_ids) < 2:
            raise ValueError(f"Issue {memory_id} has fewer than 2 memories to merge")

        # Fetch source memories
        # Check memories dict first (for tests), then try connected storage methods
        source_memories = []
        for mem_id in memory_ids:
            mem = None
            # First try direct dict access (for mocks/tests)
            if hasattr(self.storage, "memories") and isinstance(self.storage.memories, dict):
                mem = self.storage.memories.get(mem_id)
            # Then try storage methods (for real storage)
            if mem is None:
                try:
                    if hasattr(self.storage, "get_memory"):
                        mem = self.storage.get_memory(mem_id)
                except RuntimeError:
                    # Storage not connected - already checked dict above
                    pass
            if mem is None:
                raise ValueError(f"Memory not found: {mem_id}")
            source_memories.append(mem)

        # Collect all unique entities
        all_entities: set[str] = set()
        for mem in source_memories:
            entities = getattr(mem, "entities", []) or []
            all_entities.update(entities)

        # Collect all unique tags
        all_tags: set[str] = set()
        for mem in source_memories:
            tags = getattr(mem, "tags", []) or []
            all_tags.update(tags)

        # Merge content (deduplicate while preserving unique info)
        content_parts = []
        for mem in source_memories:
            content = getattr(mem, "content", "")
            if content and content not in content_parts:
                content_parts.append(content)

        merged_content = "\n\n---\n\n".join(content_parts)

        # Generate new memory ID
        new_memory_id = str(uuid.uuid4())

        # Create content diff summary
        content_diff = (
            f"Merged {len(source_memories)} memories about {', '.join(list(all_entities)[:3])}"
        )

        if self.dry_run:
            # Dry run - don't modify anything
            logger.info(f"[DRY RUN] Would merge {memory_ids} into {new_memory_id}")
            return MergeResult(
                new_memory_id=new_memory_id,
                source_ids=memory_ids,
                relation_ids=[],  # No relations created in dry run
                content_diff=content_diff,
                entities_preserved=len(all_entities),
                success=True,
                beads_issue_id=memory_id,
            )

        # === LIVE MODE: Actually perform the merge ===

        # Claim the issue
        if not claim_issue(memory_id):
            raise RuntimeError(f"Failed to claim issue {memory_id}")

        try:
            # Get cohesion from issue notes (for strength calculation)
            cohesion = notes.get("cohesion", 0.8)

            # Use consolidation module for intelligent merging (T053)
            merged_content = merge_content_smart(source_memories)
            merged_meta = merge_metadata(source_memories)
            merged_entities_list = merge_entities(source_memories)
            merged_strength = calculate_merged_strength(source_memories, cohesion)

            # Calculate timestamps: earliest created, latest used
            earliest_created = min(
                getattr(m, "created_at", int(time.time())) for m in source_memories
            )
            latest_used = max(getattr(m, "last_used", int(time.time())) for m in source_memories)
            total_use_count = sum(getattr(m, "use_count", 0) for m in source_memories)

            # Create the merged memory
            merged_memory = Memory(
                id=new_memory_id,
                content=merged_content,
                meta=merged_meta,
                entities=merged_entities_list,
                created_at=earliest_created,
                last_used=latest_used,
                use_count=total_use_count,
                strength=merged_strength,
                status=MemoryStatus.ACTIVE,
            )

            # Save merged memory
            self.storage.save_memory(merged_memory)
            logger.info(f"Created merged memory {new_memory_id}")

            # Create consolidated_from relations (T054)
            relation_ids = []
            now = int(time.time())
            for orig_id in memory_ids:
                relation = Relation(
                    id=str(uuid.uuid4()),
                    from_memory_id=new_memory_id,
                    to_memory_id=orig_id,
                    relation_type="consolidated_from",
                    strength=1.0,
                    created_at=now,
                    metadata={
                        "cluster_id": cluster_id,
                        "cohesion": cohesion,
                        "beads_issue_id": memory_id,
                    },
                )
                self.storage.create_relation(relation)
                relation_ids.append(relation.id)
            logger.info(f"Created {len(relation_ids)} consolidated_from relations")

            # Archive original memories (T055) - status change, not delete
            for orig_id in memory_ids:
                self.storage.update_memory(orig_id, status=MemoryStatus.ARCHIVED)
            logger.info(f"Archived {len(memory_ids)} original memories")

            # Close the beads issue (T056)
            close_issue(memory_id, f"Merged into {new_memory_id}")

            return MergeResult(
                new_memory_id=new_memory_id,
                source_ids=memory_ids,
                relation_ids=relation_ids,
                content_diff=content_diff,
                entities_preserved=len(all_entities),
                success=True,
                beads_issue_id=memory_id,
            )

        except Exception as e:
            logger.error(f"Merge failed for {memory_id}: {e}")
            raise RuntimeError(f"Merge failed: {e}") from e
