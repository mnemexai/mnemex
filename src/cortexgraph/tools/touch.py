"""Touch memory tool - reinforce a memory by updating its access time."""

import time
from typing import Any

from ..context import db, mcp
from ..core.decay import calculate_score
from ..security.validators import validate_uuid


@mcp.tool()
def touch_memory(memory_id: str, boost_strength: bool = False) -> dict[str, Any]:
    """Reinforce memory to reset decay.

    Args:
        memory_id: Memory UUID.
        boost_strength: Increase base strength.

    Returns:
        Dict with old_score, new_score, use_count, strength.

    Raises:
        ValueError: Invalid UUID.
    """
    # Input validation
    memory_id = validate_uuid(memory_id, "memory_id")

    memory = db.get_memory(memory_id)
    if memory is None:
        return {"success": False, "message": f"Memory not found: {memory_id}"}

    now = int(time.time())
    old_score = calculate_score(
        use_count=memory.use_count,
        last_used=memory.last_used,
        strength=memory.strength,
        now=now,
    )

    new_use_count = memory.use_count + 1
    new_strength = memory.strength
    if boost_strength:
        new_strength = min(2.0, memory.strength + 0.1)

    db.update_memory(
        memory_id=memory_id,
        last_used=now,
        use_count=new_use_count,
        strength=new_strength,
    )

    new_score = calculate_score(
        use_count=new_use_count,
        last_used=now,
        strength=new_strength,
        now=now,
    )

    return {
        "success": True,
        "memory_id": memory_id,
        "old_score": round(old_score, 4),
        "new_score": round(new_score, 4),
        "use_count": new_use_count,
        "strength": round(new_strength, 4),
        "message": f"Memory reinforced. Score: {old_score:.2f} -> {new_score:.2f}",
    }
