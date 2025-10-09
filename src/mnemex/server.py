"""MCP Server entry point for Mnemex."""

import logging
import sys

from .config import get_config
from .context import db, mcp
from .core.decay import calculate_halflife

# Import tools to register them with the decorator
from .tools import (  # noqa: F401
    cluster,
    consolidate,
    create_relation,
    gc,
    open_memories,
    promote,
    read_graph,
    save,
    search,
    search_unified,
    touch,
)

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def initialize_server():
    """Initialize logging and database connections."""
    config = get_config()
    logging.getLogger().setLevel(config.log_level)

    logger.info("Initializing Mnemex")
    logger.info(f"Storage (JSONL): {config.storage_path}")

    model = config.decay_model
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

    db.connect()
    logger.info(f"Storage initialized with {db.count_memories()} memories")
    logger.info("MCP server tools registered (11 tools)")


def main_sync() -> None:
    """Synchronous entry point for the server."""
    try:
        initialize_server()
        mcp.run()
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main_sync()
