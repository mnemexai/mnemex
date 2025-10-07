"""Save memory tool."""

import time
import uuid
from typing import Any

from mcp.server import Server
from mcp.types import Tool

from ..config import get_config
from ..storage.jsonl_storage import JSONLStorage
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
    except ImportError:
        # sentence-transformers not installed
        return None
    except Exception:
        # Error generating embedding
        return None


async def save_memory_handler(db: JSONLStorage, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Handle save memory requests.

    Args:
        db: Database instance
        arguments: Tool arguments

    Returns:
        Response dictionary
    """
    content = arguments["content"]
    tags = arguments.get("tags", [])
    entities = arguments.get("entities", [])
    source = arguments.get("source")
    context = arguments.get("context")
    extra_meta = arguments.get("meta", {})

    # Create metadata
    meta = MemoryMetadata(
        tags=tags,
        source=source,
        context=context,
        extra=extra_meta,
    )

    # Generate ID
    memory_id = str(uuid.uuid4())

    # Generate embedding if enabled
    embed = _generate_embedding(content)

    # Create memory
    now = int(time.time())
    memory = Memory(
        id=memory_id,
        content=content,
        meta=meta,
        created_at=now,
        last_used=now,
        use_count=0,
        embed=embed,
        entities=entities,
    )

    # Save to database
    db.save_memory(memory)

    return {
        "success": True,
        "memory_id": memory_id,
        "message": f"Memory saved with ID: {memory_id}",
        "has_embedding": embed is not None,
    }


def register(server: Server, db: JSONLStorage) -> None:
    """Register the save memory tool with the MCP server."""

    @server.call_tool()
    async def save_memory(arguments: dict[str, Any]) -> list[Any]:
        """
        Save a new memory to short-term storage.

        Args:
            content: The content to remember (required)
            tags: List of tags for categorization (optional)
            entities: List of named entities in this memory (optional)
            source: Source of the memory (optional)
            context: Context when memory was created (optional)
            meta: Additional custom metadata as key-value pairs (optional)

        Returns:
            Success status, memory ID, and confirmation message
        """
        result = await save_memory_handler(db, arguments)
        return [{"type": "text", "text": str(result)}]

    # Register tool metadata
    server.list_tools = lambda: [
        Tool(
            name="save_memory",
            description=(
                "Save a new memory to short-term storage. The memory will have temporal "
                "decay applied and will be forgotten if not used regularly. Frequently "
                "accessed memories may be promoted to long-term storage automatically."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content to remember",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization",
                    },
                    "source": {
                        "type": "string",
                        "description": "Source of the memory",
                    },
                    "context": {
                        "type": "string",
                        "description": "Context when memory was created",
                    },
                    "meta": {
                        "type": "object",
                        "description": "Additional custom metadata",
                    },
                },
                "required": ["content"],
            },
        )
    ]
