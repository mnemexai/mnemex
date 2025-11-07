"""Save memory tool."""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, Any, cast

from ..config import get_config
from ..context import db, mcp
from ..performance import time_operation
from ..security.secrets import detect_secrets, format_secret_warning, should_warn_about_secrets
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

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Optional dependency for embeddings
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Global model cache to avoid reloading on every request
_model_cache: dict[str, Any] = {}


def _get_embedding_model(model_name: str) -> SentenceTransformer | None:
    """Get cached embedding model or create new one."""
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None

    if model_name not in _model_cache:
        try:
            _model_cache[model_name] = SentenceTransformer(model_name)
        except Exception:
            return None

    return _model_cache[model_name]


def _generate_embedding(content: str) -> list[float] | None:
    """Generate embedding for content if embeddings are enabled."""
    config = get_config()
    if not config.enable_embeddings or not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None

    model = _get_embedding_model(config.embed_model)
    if model is None:
        return None

    try:
        embedding = model.encode(content, convert_to_numpy=True)
        return cast(list[float], embedding.tolist())
    except Exception:
        return None


@mcp.tool()
@time_operation("save_memory")
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
    content = cast(
        str, validate_string_length(content, MAX_CONTENT_LENGTH, "content", allow_empty=False)
    )

    if tags is not None:
        tags = validate_list_length(tags, MAX_TAGS_COUNT, "tags")
        tags = [validate_tag(tag, f"tags[{i}]") for i, tag in enumerate(tags)]

    if entities is not None:
        entities = validate_list_length(entities, MAX_ENTITIES_COUNT, "entities")
        entities = [validate_entity(entity, f"entities[{i}]") for i, entity in enumerate(entities)]

    if source is not None:
        source = cast(str, validate_string_length(source, 500, "source", allow_none=True))

    if context is not None:
        context = cast(str, validate_string_length(context, 1000, "context", allow_none=True))

    # Secrets detection (if enabled)
    config = get_config()
    if config.detect_secrets:
        matches = detect_secrets(content)
        if should_warn_about_secrets(matches):
            warning = format_secret_warning(matches)
            logger.warning(f"Secrets detected in memory content:\n{warning}")
            # Note: We still save the memory but warn the user

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
