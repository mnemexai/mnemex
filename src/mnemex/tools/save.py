"""Save memory tool."""

import time
import uuid
from typing import Any

from ..config import get_config
from ..context import db, mcp
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
        content: The content to remember.
        tags: Tags for categorization.
        entities: Named entities in this memory.
        source: Source of the memory.
        context: Context when memory was created.
        meta: Additional custom metadata.
    """
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
