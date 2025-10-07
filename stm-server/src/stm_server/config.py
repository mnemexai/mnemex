"""Configuration management for STM server."""

import math
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Load environment variables from .env file
load_dotenv()


class Config(BaseModel):
    """Configuration for STM server."""

    # Storage (Phase 2 - JSONL)
    storage_path: Path = Field(
        default_factory=lambda: Path.home() / ".stm" / "jsonl",
        description="Path to JSONL storage directory",
    )

    # Legacy database (Phase 1 - for migration)
    db_path: Path = Field(
        default_factory=lambda: Path.home() / ".stm" / "memories.db",
        description="Path to SQLite database file (legacy)",
    )

    # Decay parameters
    decay_lambda: float = Field(
        default=2.673e-6,  # 3-day half-life: ln(2) / (3 * 86400)
        description="Decay constant (lambda) for exponential decay",
        gt=0,
    )
    decay_beta: float = Field(
        default=0.6,
        description="Exponent for use_count in scoring function",
        ge=0,
    )

    # Thresholds
    forget_threshold: float = Field(
        default=0.05,
        description="Minimum score before memory is forgotten",
        ge=0,
        le=1,
    )
    promote_threshold: float = Field(
        default=0.65,
        description="Score threshold for automatic promotion",
        ge=0,
        le=1,
    )
    promote_use_count: int = Field(
        default=5,
        description="Use count threshold for promotion",
        ge=1,
    )
    promote_time_window: int = Field(
        default=14,
        description="Time window in days for use count evaluation",
        ge=1,
    )

    # Embeddings
    embed_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model name",
    )
    enable_embeddings: bool = Field(
        default=False,
        description="Enable semantic search with embeddings",
    )

    # Semantic search thresholds
    semantic_hi: float = Field(
        default=0.88,
        description="High similarity threshold (likely duplicate)",
        ge=0,
        le=1,
    )
    semantic_lo: float = Field(
        default=0.78,
        description="Low similarity threshold (likely distinct)",
        ge=0,
        le=1,
    )

    # Clustering
    cluster_link_threshold: float = Field(
        default=0.83,
        description="Cosine similarity threshold for cluster linking",
        ge=0,
        le=1,
    )
    cluster_max_size: int = Field(
        default=12,
        description="Maximum cluster size for LLM review",
        ge=1,
    )

    # Long-Term Memory (LTM) Integration
    ltm_vault_path: Optional[Path] = Field(
        default=None,
        description="Path to Obsidian vault for LTM storage and search",
    )
    ltm_index_path: Optional[Path] = Field(
        default=None,
        description="Path to LTM index file (default: vault/.stm-index.jsonl)",
    )
    ltm_promoted_folder: str = Field(
        default="stm-promoted",
        description="Folder within vault for promoted memories",
    )

    # Git Backup
    git_auto_commit: bool = Field(
        default=True,
        description="Enable automatic git commits",
    )
    git_commit_interval: int = Field(
        default=3600,
        description="Auto-commit interval in seconds",
        ge=60,  # Minimum 1 minute
    )

    # Unified Search
    search_stm_weight: float = Field(
        default=1.0,
        description="Weight for STM results in unified search",
        ge=0,
    )
    search_ltm_weight: float = Field(
        default=0.7,
        description="Weight for LTM results in unified search",
        ge=0,
    )

    # Legacy Integration (Phase 1 - deprecated)
    basic_memory_path: Optional[Path] = Field(
        default=None,
        description="Path to Obsidian vault for Basic Memory integration (deprecated, use ltm_vault_path)",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    @field_validator(
        "storage_path",
        "db_path",
        "ltm_vault_path",
        "ltm_index_path",
        "basic_memory_path",
        mode="before"
    )
    @classmethod
    def expand_path(cls, v: Optional[str | Path]) -> Optional[Path]:
        """Expand home directory and environment variables in paths."""
        if v is None:
            return None
        path = Path(os.path.expanduser(os.path.expandvars(str(v))))
        return path

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config_dict = {}

        # Storage
        if storage_path := os.getenv("STM_STORAGE_PATH"):
            config_dict["storage_path"] = storage_path

        # Legacy database
        if db_path := os.getenv("STM_DB_PATH"):
            config_dict["db_path"] = db_path

        # Decay parameters
        if decay_lambda := os.getenv("STM_DECAY_LAMBDA"):
            config_dict["decay_lambda"] = float(decay_lambda)
        if decay_beta := os.getenv("STM_DECAY_BETA"):
            config_dict["decay_beta"] = float(decay_beta)

        # Thresholds
        if forget_threshold := os.getenv("STM_FORGET_THRESHOLD"):
            config_dict["forget_threshold"] = float(forget_threshold)
        if promote_threshold := os.getenv("STM_PROMOTE_THRESHOLD"):
            config_dict["promote_threshold"] = float(promote_threshold)
        if promote_use_count := os.getenv("STM_PROMOTE_USE_COUNT"):
            config_dict["promote_use_count"] = int(promote_use_count)
        if promote_time_window := os.getenv("STM_PROMOTE_TIME_WINDOW"):
            config_dict["promote_time_window"] = int(promote_time_window)

        # Embeddings
        if embed_model := os.getenv("STM_EMBED_MODEL"):
            config_dict["embed_model"] = embed_model
        if enable_embeddings := os.getenv("STM_ENABLE_EMBEDDINGS"):
            config_dict["enable_embeddings"] = enable_embeddings.lower() in ("true", "1", "yes")

        # Semantic search
        if semantic_hi := os.getenv("STM_SEMANTIC_HI"):
            config_dict["semantic_hi"] = float(semantic_hi)
        if semantic_lo := os.getenv("STM_SEMANTIC_LO"):
            config_dict["semantic_lo"] = float(semantic_lo)

        # Clustering
        if cluster_link_threshold := os.getenv("STM_CLUSTER_LINK_THRESHOLD"):
            config_dict["cluster_link_threshold"] = float(cluster_link_threshold)
        if cluster_max_size := os.getenv("STM_CLUSTER_MAX_SIZE"):
            config_dict["cluster_max_size"] = int(cluster_max_size)

        # Long-Term Memory
        if ltm_vault_path := os.getenv("LTM_VAULT_PATH"):
            config_dict["ltm_vault_path"] = ltm_vault_path
        if ltm_index_path := os.getenv("LTM_INDEX_PATH"):
            config_dict["ltm_index_path"] = ltm_index_path
        if ltm_promoted_folder := os.getenv("LTM_PROMOTED_FOLDER"):
            config_dict["ltm_promoted_folder"] = ltm_promoted_folder

        # Git Backup
        if git_auto_commit := os.getenv("GIT_AUTO_COMMIT"):
            config_dict["git_auto_commit"] = git_auto_commit.lower() in ("true", "1", "yes")
        if git_commit_interval := os.getenv("GIT_COMMIT_INTERVAL"):
            config_dict["git_commit_interval"] = int(git_commit_interval)

        # Unified Search
        if search_stm_weight := os.getenv("SEARCH_STM_WEIGHT"):
            config_dict["search_stm_weight"] = float(search_stm_weight)
        if search_ltm_weight := os.getenv("SEARCH_LTM_WEIGHT"):
            config_dict["search_ltm_weight"] = float(search_ltm_weight)

        # Legacy Integration
        if basic_memory_path := os.getenv("BASIC_MEMORY_PATH"):
            config_dict["basic_memory_path"] = basic_memory_path
            # Auto-migrate to ltm_vault_path if not explicitly set
            if "ltm_vault_path" not in config_dict:
                config_dict["ltm_vault_path"] = basic_memory_path

        # Logging
        if log_level := os.getenv("LOG_LEVEL"):
            config_dict["log_level"] = log_level

        return cls(**config_dict)

    def ensure_db_dir(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


def calculate_decay_lambda_from_halflife(halflife_days: float) -> float:
    """
    Calculate decay constant from half-life in days.

    Args:
        halflife_days: Half-life period in days

    Returns:
        Decay constant (lambda) for exponential decay
    """
    halflife_seconds = halflife_days * 86400
    return math.log(2) / halflife_seconds


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
