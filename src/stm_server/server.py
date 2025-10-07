"""MCP Server entry point for STM server."""

import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .config import get_config
from .storage.database import Database
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
    touch_tool,
)

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_server() -> Server:
    """Create and configure the MCP server instance."""
    config = get_config()
    config.ensure_db_dir()

    # Set logging level from config
    logging.getLogger().setLevel(config.log_level)

    # Create server instance
    server = Server("stm-server")

    logger.info("Initializing STM server")
    logger.info(f"Database: {config.db_path}")
    logger.info(f"Decay lambda: {config.decay_lambda} (halflife ~{0.693/config.decay_lambda/86400:.1f} days)")
    logger.info(f"Embeddings: {'enabled' if config.enable_embeddings else 'disabled'}")

    # Initialize database connection
    db = Database()
    db.connect()
    logger.info(f"Database initialized with {db.count_memories()} memories")

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

    logger.info("All tools registered (10 tools)")

    return server


async def main() -> None:
    """Main entry point for the STM server."""
    try:
        server = create_server()

        # Run server with stdio transport
        async with stdio_server() as (read_stream, write_stream):
            logger.info("STM server started, awaiting connections...")
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
