"""Relationship Discovery agent for finding implicit memory connections.

This agent identifies potential relationships between memories based on
shared entities, tags, and semantic similarity.

From contracts/agent-api.md:
    Scan Contract:
        - MUST find memories with potential connections
        - MUST NOT return already-related pairs

    Process Contract:
        - MUST calculate relation strength
        - MUST provide reasoning for relation
        - MUST respect confidence threshold
        - MUST NOT create spurious relations (precision > 0.8)
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from cortexgraph.agents.base import ConsolidationAgent
from cortexgraph.agents.beads_integration import (
    close_issue,
    create_consolidation_issue,
)
from cortexgraph.agents.models import RelationResult
from cortexgraph.agents.storage_utils import get_storage
from cortexgraph.storage.models import MemoryStatus, Relation

if TYPE_CHECKING:
    from cortexgraph.storage.jsonl_storage import JSONLStorage
    from cortexgraph.storage.models import Memory

logger = logging.getLogger(__name__)


class RelationshipDiscovery(ConsolidationAgent[RelationResult]):
    """Finds implicit connections between memories.

    This agent scans storage for memory pairs that share entities,
    tags, or have semantic similarity and creates explicit relations.

    Example:
        >>> discovery = RelationshipDiscovery(dry_run=True)
        >>> pair_ids = discovery.scan()  # Returns "mem-1:mem-2" style IDs
        >>> for pair_id in pair_ids:
        ...     result = discovery.process_item(pair_id)
        ...     print(f"Created relation with strength {result.strength}")
    """

    def __init__(
        self,
        dry_run: bool = False,
        rate_limit: int = 100,
        min_confidence: float = 0.3,
        min_shared_entities: int = 1,
    ) -> None:
        """Initialize RelationshipDiscovery agent.

        Args:
            dry_run: If True, preview relations without creating them
            rate_limit: Max operations per minute
            min_confidence: Minimum confidence threshold for relations (0.0-1.0)
            min_shared_entities: Minimum shared entities for candidate detection
        """
        super().__init__(dry_run=dry_run, rate_limit=rate_limit)
        self._storage: "JSONLStorage | None" = None
        self._min_confidence = min_confidence
        self._min_shared_entities = min_shared_entities
        self._candidate_cache: dict[str, tuple[str, str, set[str]]] = {}

    @property
    def storage(self) -> "JSONLStorage":
        """Get storage instance (lazy initialization)."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def scan(self) -> list[str]:
        """Scan storage for memory pairs with potential relationships.

        Returns:
            List of pair IDs in format "mem-id-1:mem-id-2"

        Contract:
            - MUST find memories with potential connections
            - MUST NOT return already-related pairs
            - MUST NOT modify any data
        """
        candidates: list[str] = []
        self._candidate_cache = {}

        # Get all active memories
        memories: dict[str, Memory] = {}

        # Try direct dict access first (for tests/mocks)
        if hasattr(self.storage, "memories") and isinstance(self.storage.memories, dict):
            memories = self.storage.memories
        else:
            # Try storage methods for real storage
            try:
                if hasattr(self.storage, "list_memories"):
                    memories = {m.id: m for m in self.storage.list_memories()}
                elif hasattr(self.storage, "get_all_memories"):
                    memories = {m.id: m for m in self.storage.get_all_memories()}  # pyright: ignore[reportAttributeAccessIssue]
            except RuntimeError:
                logger.warning("Storage not connected, cannot scan")
                return []

        # Filter to active memories only
        active_memories = {
            mid: m
            for mid, m in memories.items()
            if getattr(m, "status", MemoryStatus.ACTIVE) == MemoryStatus.ACTIVE
        }

        # Build entity index for faster lookup
        entity_to_memories: dict[str, set[str]] = {}
        for mid, memory in active_memories.items():
            entities = getattr(memory, "entities", []) or []
            for entity in entities:
                if entity not in entity_to_memories:
                    entity_to_memories[entity] = set()
                entity_to_memories[entity].add(mid)

        # Find pairs with shared entities
        seen_pairs: set[tuple[str, str]] = set()
        existing_relations = self._get_existing_relation_pairs()

        for _entity, memory_ids in entity_to_memories.items():
            if len(memory_ids) < 2:
                continue

            memory_list = list(memory_ids)
            for i in range(len(memory_list)):
                for j in range(i + 1, len(memory_list)):
                    mid1, mid2 = memory_list[i], memory_list[j]

                    # Normalize pair order for deduplication
                    pair = (min(mid1, mid2), max(mid1, mid2))

                    # Skip if already seen or already related
                    if pair in seen_pairs:
                        continue
                    if pair in existing_relations:
                        continue

                    seen_pairs.add(pair)

                    # Calculate shared entities for this pair
                    try:
                        mem1 = active_memories[mid1]
                        mem2 = active_memories[mid2]
                        entities1 = set(getattr(mem1, "entities", []) or [])
                        entities2 = set(getattr(mem2, "entities", []) or [])
                        shared = entities1 & entities2

                        if len(shared) >= self._min_shared_entities:
                            pair_id = f"{pair[0]}:{pair[1]}"
                            candidates.append(pair_id)
                            self._candidate_cache[pair_id] = (pair[0], pair[1], shared)
                            logger.debug(f"Relationship candidate: {pair_id} (shared: {shared})")
                    except Exception as e:
                        logger.warning(f"Error checking pair {pair}: {e}")

        logger.info(f"RelationshipDiscovery scan found {len(candidates)} relationship candidates")
        return candidates

    def _get_existing_relation_pairs(self) -> set[tuple[str, str]]:
        """Get set of already-related memory pairs.

        Returns:
            Set of (mem_id_1, mem_id_2) tuples, normalized order
        """
        existing: set[tuple[str, str]] = set()

        # Try to get relations from storage
        if hasattr(self.storage, "relations") and isinstance(self.storage.relations, dict):
            for rel in self.storage.relations.values():
                from_id = getattr(rel, "from_memory_id", None)
                to_id = getattr(rel, "to_memory_id", None)
                if from_id and to_id:
                    pair = (min(from_id, to_id), max(from_id, to_id))
                    existing.add(pair)
        elif hasattr(self.storage, "get_relations"):
            # JSONLStorage uses get_relations() with no args to get all
            try:
                for rel in self.storage.get_relations():
                    pair = (
                        min(rel.from_memory_id, rel.to_memory_id),
                        max(rel.from_memory_id, rel.to_memory_id),
                    )
                    existing.add(pair)
            except Exception:
                pass
        elif hasattr(self.storage, "get_all_relations"):
            try:
                for rel in self.storage.get_all_relations():
                    pair = (
                        min(rel.from_memory_id, rel.to_memory_id),
                        max(rel.from_memory_id, rel.to_memory_id),
                    )
                    existing.add(pair)
            except Exception:
                pass

        return existing

    def process_item(self, memory_id: str) -> RelationResult:
        """Process a single memory pair for potential relationship.

        Args:
            memory_id: Pair identifier in format "mem-id-1:mem-id-2"

        Returns:
            RelationResult with relationship outcome

        Contract:
            - MUST calculate relation strength
            - MUST provide reasoning for relation
            - MUST respect confidence threshold
            - MUST NOT create spurious relations (precision > 0.8)
            - If dry_run=True, MUST NOT modify any data

        Raises:
            ValueError: If memory_id is invalid or memories not found
            RuntimeError: If relation creation fails
        """
        # Parse pair ID
        if ":" not in memory_id:
            raise ValueError(f"Invalid pair ID format: {memory_id}")

        parts = memory_id.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid pair ID format: {memory_id}")

        mem_id_1, mem_id_2 = parts

        # Get from cache or recalculate shared entities
        if memory_id in self._candidate_cache:
            _, _, shared_entities = self._candidate_cache[memory_id]
        else:
            # Fetch memories and calculate shared entities
            mem1 = self._get_memory(mem_id_1)
            mem2 = self._get_memory(mem_id_2)

            if mem1 is None:
                raise ValueError(f"Memory not found: {mem_id_1}")
            if mem2 is None:
                raise ValueError(f"Memory not found: {mem_id_2}")

            entities1 = set(getattr(mem1, "entities", []) or [])
            entities2 = set(getattr(mem2, "entities", []) or [])
            shared_entities = entities1 & entities2

        # Calculate relation strength and confidence
        strength, confidence, reasoning = self._calculate_relation_metrics(
            mem_id_1, mem_id_2, shared_entities
        )

        # Generate new relation ID
        relation_id = str(uuid.uuid4())

        if self.dry_run:
            # Dry run - don't create anything
            logger.info(
                f"[DRY RUN] Would create relation {mem_id_1} <-> {mem_id_2} "
                f"(strength={strength:.2f}, confidence={confidence:.2f})"
            )
            return RelationResult(
                from_memory_id=mem_id_1,
                to_memory_id=mem_id_2,
                relation_id=relation_id,
                strength=strength,
                reasoning=reasoning,
                shared_entities=list(shared_entities),
                confidence=confidence,
                beads_issue_id=None,
            )

        # === LIVE MODE: Actually create the relation ===

        # Check confidence threshold
        if confidence < self._min_confidence:
            logger.info(
                f"Skipping relation {memory_id}: confidence {confidence:.2f} < {self._min_confidence}"
            )
            return RelationResult(
                from_memory_id=mem_id_1,
                to_memory_id=mem_id_2,
                relation_id=relation_id,
                strength=strength,
                reasoning=f"Skipped: confidence {confidence:.2f} below threshold",
                shared_entities=list(shared_entities),
                confidence=confidence,
                beads_issue_id=None,
            )

        try:
            # Create beads issue for audit trail
            issue_id = create_consolidation_issue(
                agent="relations",
                memory_ids=[mem_id_1, mem_id_2],
                action="relate",
                urgency="low",
                extra_data={
                    "shared_entities": list(shared_entities),
                    "strength": strength,
                    "confidence": confidence,
                    "reasoning": reasoning,
                },
            )

            # Create the relation
            relation = Relation(
                id=relation_id,
                from_memory_id=mem_id_1,
                to_memory_id=mem_id_2,
                relation_type="related",
                strength=strength,
                metadata={
                    "discovered_by": "RelationshipDiscovery",
                    "shared_entities": list(shared_entities),
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "beads_issue_id": issue_id,
                },
            )

            self.storage.create_relation(relation)
            logger.info(f"Created relation {relation_id}: {mem_id_1} <-> {mem_id_2}")

            # Close beads issue
            close_issue(issue_id, f"Created relation {relation_id}")

            return RelationResult(
                from_memory_id=mem_id_1,
                to_memory_id=mem_id_2,
                relation_id=relation_id,
                strength=strength,
                reasoning=reasoning,
                shared_entities=list(shared_entities),
                confidence=confidence,
                beads_issue_id=issue_id,
            )

        except Exception as e:
            logger.error(f"Failed to create relation for {memory_id}: {e}")
            raise RuntimeError(f"Relation creation failed: {e}") from e

    def _get_memory(self, memory_id: str) -> Memory | None:
        """Get memory by ID from storage."""
        # Try direct dict access first (for tests/mocks)
        if hasattr(self.storage, "memories") and isinstance(self.storage.memories, dict):
            return self.storage.memories.get(memory_id)

        # Try storage methods
        if hasattr(self.storage, "get_memory"):
            try:
                return self.storage.get_memory(memory_id)
            except Exception:
                pass

        return None

    def _calculate_relation_metrics(
        self, mem_id_1: str, mem_id_2: str, shared_entities: set[str]
    ) -> tuple[float, float, str]:
        """Calculate relation strength, confidence, and reasoning.

        Args:
            mem_id_1: First memory ID
            mem_id_2: Second memory ID
            shared_entities: Set of entities shared between memories

        Returns:
            Tuple of (strength, confidence, reasoning)
        """
        mem1 = self._get_memory(mem_id_1)
        mem2 = self._get_memory(mem_id_2)

        if mem1 is None or mem2 is None:
            return 0.0, 0.0, "Memory not found"

        # Get entity and tag sets
        entities1 = set(getattr(mem1, "entities", []) or [])
        entities2 = set(getattr(mem2, "entities", []) or [])
        # Tags are stored in meta.tags for real Memory model, but tests may use direct tags
        # Try meta.tags first, fall back to direct tags attribute
        meta1 = getattr(mem1, "meta", None)
        meta2 = getattr(mem2, "meta", None)
        if meta1 and hasattr(meta1, "tags") and meta1.tags:
            tags1 = set(meta1.tags)
        else:
            tags1 = set(getattr(mem1, "tags", []) or [])
        if meta2 and hasattr(meta2, "tags") and meta2.tags:
            tags2 = set(meta2.tags)
        else:
            tags2 = set(getattr(mem2, "tags", []) or [])

        # Calculate Jaccard similarity for entities
        entity_union = entities1 | entities2
        entity_jaccard = len(shared_entities) / len(entity_union) if entity_union else 0.0

        # Calculate Jaccard similarity for tags
        shared_tags = tags1 & tags2
        tag_union = tags1 | tags2
        tag_jaccard = len(shared_tags) / len(tag_union) if tag_union else 0.0

        # Combined strength (weighted average)
        strength = 0.7 * entity_jaccard + 0.3 * tag_jaccard

        # Confidence based on number of shared entities and tags
        entity_confidence = min(1.0, len(shared_entities) / 3.0)  # 3+ entities = full confidence
        tag_confidence = min(1.0, len(shared_tags) / 2.0)  # 2+ tags = full confidence
        confidence = 0.6 * entity_confidence + 0.4 * tag_confidence

        # Build reasoning
        reasoning_parts = []
        if shared_entities:
            reasoning_parts.append(f"Shared entities: {', '.join(sorted(shared_entities))}")
        if shared_tags:
            reasoning_parts.append(f"Shared tags: {', '.join(sorted(shared_tags))}")

        if not reasoning_parts:
            reasoning = "No shared entities or tags"
        else:
            reasoning = "; ".join(reasoning_parts)

        return strength, confidence, reasoning
