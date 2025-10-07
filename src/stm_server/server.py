"""MCP Server entry point for STM server."""

import logging
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .config import get_config
from .core.decay import calculate_halflife
from .storage.jsonl_storage import JSONLStorage
from .tools import (
    cluster_tool,
    consolidate_tool,
    create_relation_tool,
    gc_tool,
    open_memories_tool,
    promote_tool,
    read_graph_tool,
    save_tool,
    search_tool,
    search_unified_tool,
    touch_tool,
)

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_server() -> Server:
    """Create and configure the MCP server instance."""
    config = get_config()
    # Ensure storage directory exists is handled by JSONLStorage

    # Set logging level from config
    logging.getLogger().setLevel(config.log_level)

    # Create server instance
    server = Server("stm-server")

    logger.info("Initializing STM server")
    logger.info(f"Storage (JSONL): {get_config().storage_path}")
    # Log decay model details
    model = getattr(config, "decay_model", "power_law")
    if model == "power_law":
        logger.info(
            "Decay model: power_law (alpha=%.3f, halflife=%.1f days)",
            config.pl_alpha,
            config.pl_halflife_days,
        )
    elif model == "two_component":
        hl_fast = calculate_halflife(config.tc_lambda_fast)
        hl_slow = calculate_halflife(config.tc_lambda_slow)
        logger.info(
            "Decay model: two_component (w_fast=%.2f, hl_fast=%.1f d, hl_slow=%.1f d)",
            config.tc_weight_fast,
            hl_fast,
            hl_slow,
        )
    else:  # exponential
        hl = calculate_halflife(config.decay_lambda)
        logger.info(
            "Decay model: exponential (lambda=%.3e, halflife=%.1f days)",
            config.decay_lambda,
            hl,
        )
    logger.info(f"Embeddings: {'enabled' if config.enable_embeddings else 'disabled'}")

    # Initialize JSONL storage
    db = JSONLStorage()
    db.connect()
    logger.info(f"Storage initialized with {db.count_memories()} memories")

    # Register tools
    save_tool.register(server, db)
    search_tool.register(server, db)
    touch_tool.register(server, db)
    gc_tool.register(server, db)
    promote_tool.register(server, db)
    cluster_tool.register(server, db)
    consolidate_tool.register(server, db)
    read_graph_tool.register(server, db)
    open_memories_tool.register(server, db)
    create_relation_tool.register(server, db)
    search_unified_tool.register(server, db)

    logger.info("All tools registered (11 tools including unified search)")

    return server


async def main() -> None:
    """Main entry point for the STM server."""
    try:
        server = create_server()

        # Run server with stdio transport
        async with stdio_server() as (read_stream, write_stream):
            logger.info("STM server started, awaiting connections...")
            await server.run(read_stream, write_stream, server.create_initialization_options())
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
