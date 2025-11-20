import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import get_config
from ..storage.jsonl_storage import JSONLStorage
from ..storage.models import Memory, MemoryStatus
from ..storage.sqlite_storage import SQLiteStorage
from ..vault.markdown_writer import MarkdownWriter

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency to get storage based on config
def get_storage():
    config = get_config()
    if config.storage_backend == "sqlite":
        storage: Any = SQLiteStorage()
    else:
        storage = JSONLStorage()

    storage.connect()
    try:
        yield storage
    finally:
        storage.close()


class MemoryResponse(BaseModel):
    id: str
    content: str
    created_at: int
    last_used: int
    use_count: int
    status: str
    tags: list[str]

    @classmethod
    def from_memory(cls, memory: Memory):
        return cls(
            id=memory.id,
            content=memory.content,
            created_at=memory.created_at,
            last_used=memory.last_used,
            use_count=memory.use_count,
            status=memory.status.value,
            tags=memory.meta.tags if memory.meta and memory.meta.tags else [],
        )


class MemoryListResponse(BaseModel):
    items: list[MemoryResponse]
    total: int


class SaveToVaultRequest(BaseModel):
    filename: str | None = None
    folder: str | None = None


@router.get("/memories", response_model=MemoryListResponse)
def list_memories(
    limit: int = 50, offset: int = 0, status: str | None = None, search: str | None = None
):
    """List memories with pagination and filtering."""
    config = get_config()

    if config.storage_backend == "sqlite":
        storage_cls: Any = SQLiteStorage
    else:
        storage_cls = JSONLStorage

    with storage_cls() as storage:
        # Convert status string to enum if provided
        memory_status = None
        if status:
            try:
                memory_status = MemoryStatus(status)
            except ValueError:
                pass  # Ignore invalid status for now or raise 400

        # If search query is present, use search_memories
        if search:
            # Search currently doesn't support pagination in the storage layer
            # So we fetch all and paginate in memory
            all_matches = storage.search_memories(query=search, limit=None)

            # Filter by status if needed
            if memory_status:
                all_matches = [m for m in all_matches if m.status == memory_status]

            total = len(all_matches)
            paginated_items = all_matches[offset : offset + limit]

            return MemoryListResponse(
                items=[MemoryResponse.from_memory(m) for m in paginated_items], total=total
            )

        # Standard listing
        memories = storage.list_memories(status=memory_status, limit=limit, offset=offset)
        total = storage.count_memories(status=memory_status)

        return MemoryListResponse(
            items=[MemoryResponse.from_memory(m) for m in memories], total=total
        )


@router.get("/memories/{memory_id}", response_model=MemoryResponse)
def get_memory(memory_id: str):
    """Get a single memory by ID."""
    config = get_config()
    if config.storage_backend == "sqlite":
        storage_cls: Any = SQLiteStorage
    else:
        storage_cls = JSONLStorage

    with storage_cls() as storage:
        memory = storage.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        return MemoryResponse.from_memory(memory)


@router.post("/memories/{memory_id}/save-to-vault")
def save_to_vault(memory_id: str, request: SaveToVaultRequest):
    """Save a memory to the Obsidian vault."""
    config = get_config()

    if not config.ltm_vault_path:
        raise HTTPException(status_code=400, detail="LTM Vault path not configured")

    if config.storage_backend == "sqlite":
        storage_cls: Any = SQLiteStorage
    else:
        storage_cls = JSONLStorage

    with storage_cls() as storage:
        memory = storage.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        try:
            writer = MarkdownWriter(vault_path=config.ltm_vault_path)

            # Determine filename
            title = request.filename or f"memory-{memory.id[:8]}"
            folder = request.folder or "Memories"

            # Prepare content and metadata
            content = memory.content
            tags = memory.meta.tags
            metadata = {
                "id": memory.id,
                "created_at": memory.created_at,
                "source": "cortexgraph",
                "type": "memory",
            }

            file_path = writer.write_note(
                title=title,
                content=content,
                folder=folder,
                tags=tags,
                metadata=metadata,
                created_at=memory.created_at,
                modified_at=memory.last_used,
            )

            return {"success": True, "path": str(file_path)}

        except Exception as e:
            logger.error(f"Failed to save to vault: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e
