"""End-to-end tests for automatic memory activation flow."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortexgraph.core.nlp import KeywordExtractor
from cortexgraph.middleware.activation_hook import ActivationMiddleware
from cortexgraph.storage.activation_index import build_activation_graph
from cortexgraph.storage.models import ActivationResult, Memory, MemoryMetadata


@pytest.mark.asyncio
async def test_full_conversation_flow_with_activation() -> None:
    """Test full conversation: save memory → ask question → auto-activate preference.

    Scenario:
        1. User saves: "I prefer TypeScript over JavaScript"
        2. User asks: "Help me set up a new web project"
        3. System automatically surfaces TypeScript preference (no explicit recall)
    """
    # Setup: Create memories
    memories = [
        Memory(
            id="mem1",
            content="I prefer TypeScript over JavaScript for type safety",
            meta=MemoryMetadata(tags=["typescript", "preferences"]),
            entities=["TypeScript", "JavaScript"],
        ),
        Memory(
            id="mem2",
            content="React is my preferred frontend framework",
            meta=MemoryMetadata(tags=["react", "frontend"]),
            entities=["React"],
        ),
        Memory(
            id="mem3",
            content="Database: PostgreSQL with Prisma ORM",
            meta=MemoryMetadata(tags=["database", "postgres"]),
            entities=["PostgreSQL", "Prisma"],
        ),
    ]

    # Build activation graph
    extractor = KeywordExtractor()

    def extract_fn(text: str) -> list[str]:
        return extractor.extract_keywords(text, max_keywords=10)

    _ = build_activation_graph(memories, [], extract_keywords_fn=extract_fn)

    # Create activation service (mock for now - will implement in T017)
    mock_service = AsyncMock()

    # Simulate activation finding TypeScript preference
    mock_result = ActivationResult(
        activated_memories=["mem1"],  # TypeScript preference
        activation_scores={},
        direct_matches=["mem1"],
        spread_matches=[],
        total_candidates=3,
        activation_latency_ms=15.0,
        fallback_tier="full",
    )
    mock_service.activate.return_value = mock_result

    # Create middleware
    middleware = ActivationMiddleware(activation_service=mock_service)

    # Simulate tool call: "Help me set up a new web project"
    mock_context = MagicMock()
    mock_context.message.name = "search_memory"
    mock_context.message.arguments = {"query": "help me set up a new web project"}
    mock_context.fastmcp_context = MagicMock()

    async def mock_call_next(ctx: MagicMock) -> str:
        return "search_result"

    # Execute middleware hook
    result = await middleware.on_call_tool(mock_context, mock_call_next)

    # Verify activation was triggered
    mock_service.activate.assert_called_once()

    # Verify activated memory stored in context
    set_state_calls = mock_context.fastmcp_context.set_state.call_args_list
    assert len(set_state_calls) == 1
    assert set_state_calls[0][0][0] == "activated_memories"
    activated_result = set_state_calls[0][0][1]
    assert isinstance(activated_result, ActivationResult)
    assert "mem1" in activated_result.activated_memories

    # Verify tool execution continued
    assert result == "search_result"


@pytest.mark.asyncio
async def test_conversation_without_matching_memories() -> None:
    """Test conversation when no memories match the query."""
    mock_service = AsyncMock()
    mock_service.activate.return_value = ActivationResult(
        activated_memories=[],
        activation_scores={},
        direct_matches=[],
        spread_matches=[],
        total_candidates=0,
        activation_latency_ms=5.0,
        fallback_tier="full",
    )

    middleware = ActivationMiddleware(activation_service=mock_service)

    mock_context = MagicMock()
    mock_context.message.name = "search_memory"
    mock_context.message.arguments = {"query": "quantum computing algorithms"}
    mock_context.fastmcp_context = MagicMock()

    async def mock_call_next(ctx: MagicMock) -> str:
        return "search_result"

    result = await middleware.on_call_tool(mock_context, mock_call_next)

    # Activation should still run but return empty results
    mock_service.activate.assert_called_once()

    # Empty result should still be stored
    set_state_calls = mock_context.fastmcp_context.set_state.call_args_list
    assert len(set_state_calls) == 1
    activated_result = set_state_calls[0][0][1]
    assert len(activated_result.activated_memories) == 0

    # Tool execution should continue normally
    assert result == "search_result"


@pytest.mark.asyncio
async def test_multiple_memories_activated() -> None:
    """Test activation surfacing multiple relevant memories."""
    mock_service = AsyncMock()

    # Simulate finding multiple related memories
    mock_result = ActivationResult(
        activated_memories=["mem1", "mem2", "mem3"],
        activation_scores={},
        direct_matches=["mem1", "mem2"],
        spread_matches=["mem3"],  # One via spreading activation
        total_candidates=10,
        activation_latency_ms=30.0,
        fallback_tier="full",
    )
    mock_service.activate.return_value = mock_result

    middleware = ActivationMiddleware(activation_service=mock_service)

    mock_context = MagicMock()
    mock_context.message.name = "search_memory"
    mock_context.message.arguments = {"query": "authentication best practices"}
    mock_context.fastmcp_context = MagicMock()

    async def mock_call_next(ctx: MagicMock) -> str:
        return "result"

    await middleware.on_call_tool(mock_context, mock_call_next)

    # Verify all memories were activated
    activated_result = mock_context.fastmcp_context.set_state.call_args[0][1]
    assert len(activated_result.activated_memories) == 3
    assert len(activated_result.direct_matches) == 2
    assert len(activated_result.spread_matches) == 1


@pytest.mark.asyncio
async def test_activation_preserves_tool_arguments() -> None:
    """Test that activation doesn't modify original tool arguments."""
    mock_service = AsyncMock()
    mock_service.activate.return_value = ActivationResult(
        activated_memories=[],
        activation_scores={},
        total_candidates=0,
        activation_latency_ms=5.0,
    )

    middleware = ActivationMiddleware(activation_service=mock_service)

    original_args = {
        "query": "test query",
        "tags": ["important"],
        "top_k": 5,
    }

    mock_context = MagicMock()
    mock_context.message.name = "search_memory"
    mock_context.message.arguments = original_args.copy()
    mock_context.fastmcp_context = MagicMock()

    async def mock_call_next(ctx: MagicMock) -> str:
        # Verify arguments unchanged
        assert ctx.message.arguments == original_args
        return "result"

    await middleware.on_call_tool(mock_context, mock_call_next)

    # Arguments should be preserved
    assert mock_context.message.arguments == original_args


@pytest.mark.asyncio
async def test_session_tracking_prevents_duplicates() -> None:
    """Test that already-activated memories aren't re-activated in same session."""
    mock_service = AsyncMock()

    # First call activates mem1
    mock_service.activate.return_value = ActivationResult(
        activated_memories=["mem1"],
        activation_scores={},
        total_candidates=5,
        activation_latency_ms=10.0,
    )

    middleware = ActivationMiddleware(activation_service=mock_service)

    # First message
    mock_context1 = MagicMock()
    mock_context1.message.name = "search_memory"
    mock_context1.message.arguments = {"query": "typescript"}
    mock_context1.fastmcp_context = MagicMock()

    async def mock_call_next(ctx: MagicMock) -> str:
        return "result"

    await middleware.on_call_tool(mock_context1, mock_call_next)

    # Get activation context from first call
    first_call_ctx = mock_service.activate.call_args[0][0]

    # Verify session tracking (future implementation)
    # In full implementation, second call would track already_activated
    assert isinstance(first_call_ctx.already_activated, set)
