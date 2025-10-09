"""Save memory tool."""

import time
import uuid
from typing import Any

from ..config import get_config
from ..context import db, mcp
from ..security.validators import (
    MAX_CONTENT_LENGTH,
    MAX_ENTITIES_COUNT,
    MAX_TAGS_COUNT,
    validate_entity,
    validate_list_length,
    validate_string_length,
    validate_tag,
)
from ..storage.models import Memory, MemoryMetadata


def _generate_embedding(content: str) -> list[float] | None:
    """Generate embedding for content if embeddings are enabled."""
    config = get_config()
    if not config.enable_embeddings:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(config.embed_model)
        embedding = model.encode(content, convert_to_numpy=True)
        return embedding.tolist()
    except (ImportError, Exception):
        return None


@mcp.tool()
def save_memory(
    content: str,
    tags: list[str] | None = None,
    entities: list[str] | None = None,
    source: str | None = None,
    context: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Save a new memory to short-term storage.

    The memory will have temporal decay applied and will be forgotten if not used
    regularly. Frequently accessed memories may be promoted to long-term storage
    automatically.

    Args:
        content: The content to remember (max 50,000 chars).
        tags: Tags for categorization (max 50 tags, each max 100 chars).
        entities: Named entities in this memory (max 100 entities).
        source: Source of the memory (max 500 chars).
        context: Context when memory was created (max 1,000 chars).
        meta: Additional custom metadata.

    Raises:
        ValueError: If any input fails validation.
    """
    # Input validation
    content = validate_string_length(content, MAX_CONTENT_LENGTH, "content")

    if tags is not None:
        tags = validate_list_length(tags, MAX_TAGS_COUNT, "tags")
        tags = [validate_tag(tag, f"tags[{i}]") for i, tag in enumerate(tags)]

    if entities is not None:
        entities = validate_list_length(entities, MAX_ENTITIES_COUNT, "entities")
        entities = [validate_entity(entity, f"entities[{i}]") for i, entity in enumerate(entities)]

    if source is not None:
        source = validate_string_length(source, 500, "source", allow_none=True)

    if context is not None:
        context = validate_string_length(context, 1000, "context", allow_none=True)

    # Create metadata
    metadata = MemoryMetadata(
        tags=tags or [],
        source=source,
        context=context,
        extra=meta or {},
    )

    # Generate ID and embedding
    memory_id = str(uuid.uuid4())
    embed = _generate_embedding(content)

    # Create memory
    now = int(time.time())
    memory = Memory(
        id=memory_id,
        content=content,
        meta=metadata,
        created_at=now,
        last_used=now,
        use_count=0,
        embed=embed,
        entities=entities or [],
    )

    # Save to database
    db.save_memory(memory)

    return {
        "success": True,
        "memory_id": memory_id,
        "message": f"Memory saved with ID: {memory_id}",
        "has_embedding": embed is not None,
    }
