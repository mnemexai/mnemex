"""FastMCP middleware for transparent memory activation.

This middleware intercepts tool calls and automatically activates
relevant memories based on the conversation context.
"""

import asyncio
import logging
from typing import Any

from ..storage.models import ActivationContext

logger = logging.getLogger(__name__)


class ActivationMiddleware:
    """FastMCP middleware for transparent memory activation.

    Hooks into tool calls to automatically surface relevant memories
    during conversations without requiring explicit recall commands.
    """

    def __init__(self, activation_service: Any, timeout: float = 0.05) -> None:
        """Initialize activation middleware.

        Args:
            activation_service: ActivationService instance
            timeout: Maximum time for activation in seconds (default 50ms)
        """
        self.activation_service = activation_service
        self.timeout = timeout

    async def on_call_tool(self, context: Any, call_next: Any) -> Any:
        """Intercept tool calls to activate relevant memories.

        Args:
            context: FastMCP tool call context
            call_next: Continuation function to call original tool

        Returns:
            Result from the original tool call
        """
        try:
            # Extract query from tool arguments
            query = self._extract_query(context.message.name, context.message.arguments)

            # Only activate if we have a query
            if query:
                # Create activation context
                activation_context = ActivationContext(
                    message=query,
                    keywords=[],  # Will be extracted by service
                    session_id=None,  # TODO: Extract from context if available
                    already_activated=set(),  # TODO: Track per session
                    max_memories=10,
                    activation_threshold=0.5,
                    enable_spreading=True,
                )

                # Run activation with timeout
                try:
                    result = await asyncio.wait_for(
                        self.activation_service.activate(activation_context), timeout=self.timeout
                    )

                    # Store activated memories in context for potential use
                    if hasattr(context, "fastmcp_context"):
                        context.fastmcp_context.set_state("activated_memories", result)

                    logger.debug(
                        f"Activated {len(result.activated_memories)} memories "
                        f"for query '{query[:50]}...' in {result.activation_latency_ms:.1f}ms"
                    )

                except asyncio.TimeoutError:
                    logger.warning(f"Activation timed out after {self.timeout*1000}ms")
                    # Continue without activation (silent degradation)

                except Exception as e:
                    logger.error(f"Activation failed: {e}")
                    # Continue without activation (silent degradation)

        except Exception as e:
            logger.error(f"Middleware error: {e}")
            # Continue to tool execution even if middleware fails

        # Always call the original tool
        return await call_next(context)

    def _extract_query(self, tool_name: str, arguments: dict[str, Any]) -> str | None:
        """Extract query text from tool arguments.

        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments dictionary

        Returns:
            Query string if found, None otherwise
        """
        # Map tool names to query argument keys
        query_extractors = {
            "search_memory": "query",
            "save_memory": "content",
            "search_unified": "query",
            "open_memories": None,  # No query for direct ID lookup
            "gc": None,  # No query for garbage collection
            "promote_memory": None,  # No query for promotion
            "cluster_memories": None,  # No query for clustering
            "consolidate_memories": None,  # No query for consolidation
            "create_relation": None,  # No query for relation creation
            "touch_memory": None,  # No query for touch
            "read_graph": None,  # No query for graph read
        }

        # Get query field for this tool
        query_field = query_extractors.get(tool_name)

        if query_field is None:
            return None

        # Extract query from arguments
        query = arguments.get(query_field)

        if query and isinstance(query, str):
            return str(query).strip()

        return None
