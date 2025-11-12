"""Integration tests for ActivationMiddleware hook interception."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortexgraph.middleware.activation_hook import ActivationMiddleware
from cortexgraph.storage.models import (
    ActivationContext,
    ActivationResult,
    ActivationScore,
    ActivationSource,
)


class TestActivationMiddlewareIntegration:
    """Test ActivationMiddleware hook integration with FastMCP."""

    @pytest.mark.asyncio
    async def test_middleware_intercepts_tool_call(self) -> None:
        """Test that middleware intercepts tool calls and activates memories."""
        # Mock activation service
        mock_service = AsyncMock()
        mock_result = ActivationResult(
            activated_memories=["mem1", "mem2"],
            activation_scores={
                "mem1": ActivationScore.calculate(
                    memory_id="mem1",
                    base_relevance=0.8,
                    temporal_score=0.7,
                    source=ActivationSource.DIRECT,
                ),
                "mem2": ActivationScore.calculate(
                    memory_id="mem2",
                    base_relevance=0.6,
                    temporal_score=0.5,
                    source=ActivationSource.DIRECT,
                ),
            },
            total_candidates=10,
            activation_latency_ms=25.0,
        )
        mock_service.activate.return_value = mock_result

        # Create middleware
        middleware = ActivationMiddleware(activation_service=mock_service, timeout=0.05)

        # Mock context
        mock_context = MagicMock()
        mock_context.message.name = "search_memory"
        mock_context.message.arguments = {"query": "help me with TypeScript"}
        mock_context.fastmcp_context = MagicMock()

        # Mock call_next
        async def mock_call_next(ctx: MagicMock) -> str:
            return "tool_result"

        # Execute middleware
        result = await middleware.on_call_tool(mock_context, mock_call_next)

        # Verify activation was called
        mock_service.activate.assert_called_once()
        call_args = mock_service.activate.call_args[0][0]
        assert isinstance(call_args, ActivationContext)
        assert call_args.message == "help me with TypeScript"

        # Verify result stored in context
        mock_context.fastmcp_context.set_state.assert_called_once_with(
            "activated_memories", mock_result
        )

        # Verify call_next was called
        assert result == "tool_result"

    @pytest.mark.asyncio
    async def test_middleware_extracts_query_from_search_tool(self) -> None:
        """Test query extraction from search_memory tool."""
        mock_service = AsyncMock()
        mock_service.activate.return_value = ActivationResult(
            activated_memories=[],
            activation_scores={},
            total_candidates=0,
            activation_latency_ms=5.0,
        )

        middleware = ActivationMiddleware(activation_service=mock_service)

        mock_context = MagicMock()
        mock_context.message.name = "search_memory"
        mock_context.message.arguments = {"query": "find authentication examples"}
        mock_context.fastmcp_context = MagicMock()

        async def mock_call_next(ctx: MagicMock) -> str:
            return "result"

        await middleware.on_call_tool(mock_context, mock_call_next)

        # Verify activation called with correct query
        call_args = mock_service.activate.call_args[0][0]
        assert call_args.message == "find authentication examples"

    @pytest.mark.asyncio
    async def test_middleware_extracts_query_from_save_tool(self) -> None:
        """Test query extraction from save_memory tool."""
        mock_service = AsyncMock()
        mock_service.activate.return_value = ActivationResult(
            activated_memories=[],
            activation_scores={},
            total_candidates=0,
            activation_latency_ms=5.0,
        )

        middleware = ActivationMiddleware(activation_service=mock_service)

        mock_context = MagicMock()
        mock_context.message.name = "save_memory"
        mock_context.message.arguments = {"content": "I prefer using JWT for auth"}
        mock_context.fastmcp_context = MagicMock()

        async def mock_call_next(ctx: MagicMock) -> str:
            return "result"

        await middleware.on_call_tool(mock_context, mock_call_next)

        # Verify activation called with content as query
        call_args = mock_service.activate.call_args[0][0]
        assert call_args.message == "I prefer using JWT for auth"

    @pytest.mark.asyncio
    async def test_middleware_handles_no_query(self) -> None:
        """Test middleware handles tools with no extractable query."""
        mock_service = AsyncMock()

        middleware = ActivationMiddleware(activation_service=mock_service)

        mock_context = MagicMock()
        mock_context.message.name = "gc"  # Garbage collection tool - no query
        mock_context.message.arguments = {}
        mock_context.fastmcp_context = MagicMock()

        async def mock_call_next(ctx: MagicMock) -> str:
            return "result"

        result = await middleware.on_call_tool(mock_context, mock_call_next)

        # Activation should not be called if no query
        mock_service.activate.assert_not_called()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_middleware_respects_timeout(self) -> None:
        """Test that middleware enforces timeout on activation."""
        import asyncio

        mock_service = AsyncMock()

        # Simulate slow activation
        async def slow_activate(ctx: ActivationContext) -> ActivationResult:
            await asyncio.sleep(0.2)  # 200ms - exceeds 50ms timeout
            return ActivationResult(
                activated_memories=[],
                activation_scores={},
                total_candidates=0,
                activation_latency_ms=200.0,
            )

        mock_service.activate.side_effect = slow_activate

        middleware = ActivationMiddleware(activation_service=mock_service, timeout=0.05)

        mock_context = MagicMock()
        mock_context.message.name = "search_memory"
        mock_context.message.arguments = {"query": "test"}
        mock_context.fastmcp_context = MagicMock()

        async def mock_call_next(ctx: MagicMock) -> str:
            return "result"

        # Should not raise, should handle timeout gracefully
        result = await middleware.on_call_tool(mock_context, mock_call_next)
        assert result == "result"

        # Should still pass through to call_next even if activation times out

    @pytest.mark.asyncio
    async def test_middleware_handles_activation_error(self) -> None:
        """Test middleware handles activation service errors gracefully."""
        mock_service = AsyncMock()
        mock_service.activate.side_effect = Exception("Activation failed")

        middleware = ActivationMiddleware(activation_service=mock_service)

        mock_context = MagicMock()
        mock_context.message.name = "search_memory"
        mock_context.message.arguments = {"query": "test"}
        mock_context.fastmcp_context = MagicMock()

        async def mock_call_next(ctx: MagicMock) -> str:
            return "result"

        # Should not raise, should handle error gracefully
        result = await middleware.on_call_tool(mock_context, mock_call_next)
        assert result == "result"

        # Should still pass through to call_next even if activation fails

    @pytest.mark.asyncio
    async def test_middleware_passes_activation_config(self) -> None:
        """Test that middleware passes configuration to activation service."""
        mock_service = AsyncMock()
        mock_service.activate.return_value = ActivationResult(
            activated_memories=[],
            activation_scores={},
            total_candidates=0,
            activation_latency_ms=5.0,
        )

        middleware = ActivationMiddleware(activation_service=mock_service)

        mock_context = MagicMock()
        mock_context.message.name = "search_memory"
        mock_context.message.arguments = {"query": "test"}
        mock_context.fastmcp_context = MagicMock()

        async def mock_call_next(ctx: MagicMock) -> str:
            return "result"

        await middleware.on_call_tool(mock_context, mock_call_next)

        # Verify ActivationContext passed with default config
        call_args = mock_service.activate.call_args[0][0]
        assert call_args.max_memories == 10  # Default from ActivationContext
        assert call_args.activation_threshold == 0.5
        assert call_args.enable_spreading is True
