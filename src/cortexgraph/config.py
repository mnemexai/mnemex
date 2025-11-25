"""Configuration management for Mnemex."""

import os
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


def _get_config_dir() -> Path:
    """Get XDG-compliant config directory."""
    xdg_config = os.getenv("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "cortexgraph"
    return Path.home() / ".config" / "cortexgraph"


# Load environment variables from .env file (XDG paths first, then local)
_config_dir = _get_config_dir()
_env_paths = [
    _config_dir / ".env",  # Primary: ~/.config/cortexgraph/.env
    Path(".env"),  # Fallback: ./env (for development)
]

_env_file_found = False
for env_path in _env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        _env_file_found = True
        break

# Log warning if no .env file found (but don't fail - config has defaults)
if not _env_file_found:
    import logging

    logging.warning(
        "No .env file found. CortexGraph will use default configuration.\n"
        f"To customize settings, create: {_config_dir / '.env'}\n"
        f"See .env.example in the cortexgraph repository for all available options."
    )


class Config(BaseModel):
    """Configuration for Mnemex."""

    # Storage (JSONL)
    storage_path: Path = Field(
        default_factory=lambda: _get_config_dir() / "jsonl",
        description="Path to JSONL storage directory",
    )
    storage_backend: str = Field(
        default="jsonl",
        description="Storage backend to use: jsonl | sqlite",
    )
    sqlite_path: Path | None = Field(
        default=None,
        description="Path to SQLite database file (default: storage_path/cortexgraph.db)",
    )

    # Decay model selection
    decay_model: str = Field(
        default="power_law",  # options: power_law, exponential, two_component
        description="Decay model to use: power_law | exponential | two_component",
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

    # Power-law parameters
    pl_alpha: float = Field(
        default=1.1,
        description="Power-law shape parameter alpha (heavier tail for higher alpha)",
        gt=0,
    )
    pl_halflife_days: float = Field(
        default=3.0,
        description="Target half-life in days for power-law used to derive t0",
        gt=0,
    )

    # Two-component exponential parameters
    tc_lambda_fast: float = Field(
        default=1.603e-5,  # ~12h half-life
        description="Fast component decay constant",
        gt=0,
    )
    tc_lambda_slow: float = Field(
        default=1.147e-6,  # ~7d half-life
        description="Slow component decay constant",
        gt=0,
    )
    tc_weight_fast: float = Field(
        default=0.7,
        description="Weight for fast component (0-1)",
        ge=0,
        le=1,
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

    # Natural language preprocessing (v0.6.0)
    enable_preprocessing: bool = Field(
        default=True,
        description="Enable automatic entity extraction and importance scoring",
    )

    # Clustering
    cluster_link_threshold: float = Field(
        default=0.83,
        description="Cosine similarity threshold for cluster linking",
        ge=0,
        le=1,
    )

    # Natural spaced repetition
    review_blend_ratio: float = Field(
        default=0.3,
        description="Ratio of review candidates to blend into search results (0.0-1.0)",
        ge=0,
        le=1,
    )
    review_danger_zone_min: float = Field(
        default=0.15,
        description="Minimum score for review danger zone (below this = too far gone)",
        ge=0,
        le=1,
    )
    review_danger_zone_max: float = Field(
        default=0.35,
        description="Maximum score for review danger zone (above this = still fresh)",
        ge=0,
        le=1,
    )
    auto_reinforce: bool = Field(
        default=True,
        description="Automatically reinforce memories when used in conversation",
    )
    cluster_max_size: int = Field(
        default=12,
        description="Maximum cluster size for LLM review",
        ge=1,
    )

    # Auto-recall (conversational memory reinforcement)
    auto_recall_enabled: bool = Field(
        default=True,
        description="Enable automatic memory recall during conversation",
    )
    auto_recall_mode: str = Field(
        default="silent",
        description="Auto-recall mode: silent | subtle | interactive",
    )
    auto_recall_relevance_threshold: float = Field(
        default=0.3,
        description="Minimum relevance score for auto-recall (0.0-1.0). Lower than explicit search to capture more context.",
        ge=0,
        le=1,
    )
    auto_recall_max_results: int = Field(
        default=3,
        description="Maximum memories to recall per trigger",
        ge=1,
        le=10,
    )
    auto_recall_min_interval: int = Field(
        default=300,
        description="Minimum seconds between auto-recall triggers (cooldown)",
        ge=0,
    )

    # Urgent Decay Event Triggers (T090)
    enable_urgent_decay_check: bool = Field(
        default=True,
        description="Enable event-driven urgent decay detection after save_memory",
    )
    urgent_decay_threshold: float = Field(
        default=0.10,
        description="Score threshold below which memory triggers urgent processing",
        ge=0,
        le=1,
    )

    # Long-Term Memory (LTM) Integration
    ltm_vault_path: Path | None = Field(
        default=None,
        description="Path to Obsidian vault for LTM storage and search",
    )
    ltm_index_path: Path | None = Field(
        default=None,
        description="Path to LTM index file (default: vault/.cortexgraph-index.jsonl)",
    )
    ltm_promoted_folder: str | None = Field(
        default=None,
        description="Folder within vault for promoted memories (required for promotion)",
    )
    ltm_index_filename: str = Field(
        default=".cortexgraph-index.jsonl",
        description="Filename for LTM index (within vault)",
    )
    ltm_legacy_index_filename: str = Field(
        default=".stm-index.jsonl",
        description="Legacy index filename (fallback if new index doesn't exist)",
    )
    ltm_index_max_age_seconds: int = Field(
        default=3600,
        description="Maximum age of LTM index before rebuilding (in seconds, default 1 hour)",
        ge=60,
    )

    # Short-Term Memory (STM) Storage Filenames
    stm_memories_filename: str = Field(
        default="memories.jsonl",
        description="Filename for memories storage (within CORTEXGRAPH_STORAGE_PATH)",
    )
    stm_relations_filename: str = Field(
        default="relations.jsonl",
        description="Filename for relations storage (within CORTEXGRAPH_STORAGE_PATH)",
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
    search_default_preview_length: int = Field(
        default=300,
        description="Default number of characters to return in search results (0 = full content)",
        ge=0,
        le=5000,
    )

    # Legacy Integration (deprecated) — removed
    basic_memory_path: Path | None | None = None

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    # Security
    detect_secrets: bool = Field(
        default=True,
        description="Enable secrets detection (warns about API keys, tokens, etc.)",
    )

    # Performance settings
    batch_size: int = Field(
        default=100,
        description="Batch size for bulk operations",
        ge=1,
        le=1000,
    )
    cache_size: int = Field(
        default=1000,
        description="Maximum number of items to cache in memory",
        ge=100,
        le=10000,
    )
    enable_async_io: bool = Field(
        default=True,
        description="Enable async I/O operations for better performance",
    )
    search_timeout: float = Field(
        default=5.0,
        description="Search operation timeout in seconds",
        ge=1.0,
        le=60.0,
    )

    @field_validator(
        "storage_path", "ltm_vault_path", "ltm_index_path", "sqlite_path", mode="before"
    )
    @classmethod
    def expand_path(cls, v: str | Path | None) -> Path | None:
        """Expand home directory and environment variables in paths."""
        if v is None:
            return None
        path = Path(os.path.expanduser(os.path.expandvars(str(v))))
        return path

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config_dict: dict[str, object] = {}

        # Storage
        if storage_path := os.getenv("CORTEXGRAPH_STORAGE_PATH"):
            config_dict["storage_path"] = storage_path
        if storage_backend := os.getenv("CORTEXGRAPH_STORAGE_BACKEND"):
            config_dict["storage_backend"] = storage_backend
        if sqlite_path := os.getenv("CORTEXGRAPH_SQLITE_PATH"):
            config_dict["sqlite_path"] = sqlite_path

        # Decay parameters
        if decay_model := os.getenv("CORTEXGRAPH_DECAY_MODEL"):
            config_dict["decay_model"] = decay_model
        if decay_lambda := os.getenv("CORTEXGRAPH_DECAY_LAMBDA"):
            config_dict["decay_lambda"] = float(decay_lambda)
        if decay_beta := os.getenv("CORTEXGRAPH_DECAY_BETA"):
            config_dict["decay_beta"] = float(decay_beta)

        # Power-law
        if pl_alpha := os.getenv("CORTEXGRAPH_PL_ALPHA"):
            config_dict["pl_alpha"] = float(pl_alpha)
        if pl_halflife_days := os.getenv("CORTEXGRAPH_PL_HALFLIFE_DAYS"):
            config_dict["pl_halflife_days"] = float(pl_halflife_days)

        # Two-component
        if tc_lambda_fast := os.getenv("CORTEXGRAPH_TC_LAMBDA_FAST"):
            config_dict["tc_lambda_fast"] = float(tc_lambda_fast)
        if tc_lambda_slow := os.getenv("CORTEXGRAPH_TC_LAMBDA_SLOW"):
            config_dict["tc_lambda_slow"] = float(tc_lambda_slow)
        if tc_weight_fast := os.getenv("CORTEXGRAPH_TC_WEIGHT_FAST"):
            config_dict["tc_weight_fast"] = float(tc_weight_fast)

        # Thresholds
        if forget_threshold := os.getenv("CORTEXGRAPH_FORGET_THRESHOLD"):
            config_dict["forget_threshold"] = float(forget_threshold)
        if promote_threshold := os.getenv("CORTEXGRAPH_PROMOTE_THRESHOLD"):
            config_dict["promote_threshold"] = float(promote_threshold)
        if promote_use_count := os.getenv("CORTEXGRAPH_PROMOTE_USE_COUNT"):
            config_dict["promote_use_count"] = int(promote_use_count)
        if promote_time_window := os.getenv("CORTEXGRAPH_PROMOTE_TIME_WINDOW"):
            config_dict["promote_time_window"] = int(promote_time_window)

        # Embeddings
        if embed_model := os.getenv("CORTEXGRAPH_EMBED_MODEL"):
            config_dict["embed_model"] = embed_model
        if enable_embeddings := os.getenv("CORTEXGRAPH_ENABLE_EMBEDDINGS"):
            config_dict["enable_embeddings"] = enable_embeddings.lower() in ("true", "1", "yes")

        # Semantic search
        if semantic_hi := os.getenv("CORTEXGRAPH_SEMANTIC_HI"):
            config_dict["semantic_hi"] = float(semantic_hi)
        if semantic_lo := os.getenv("CORTEXGRAPH_SEMANTIC_LO"):
            config_dict["semantic_lo"] = float(semantic_lo)

        # Clustering
        if cluster_link_threshold := os.getenv("CORTEXGRAPH_CLUSTER_LINK_THRESHOLD"):
            config_dict["cluster_link_threshold"] = float(cluster_link_threshold)
        if cluster_max_size := os.getenv("CORTEXGRAPH_CLUSTER_MAX_SIZE"):
            config_dict["cluster_max_size"] = int(cluster_max_size)

        # Natural spaced repetition
        if review_blend_ratio := os.getenv("CORTEXGRAPH_REVIEW_BLEND_RATIO"):
            config_dict["review_blend_ratio"] = float(review_blend_ratio)
        if review_danger_zone_min := os.getenv("CORTEXGRAPH_REVIEW_DANGER_ZONE_MIN"):
            config_dict["review_danger_zone_min"] = float(review_danger_zone_min)
        if review_danger_zone_max := os.getenv("CORTEXGRAPH_REVIEW_DANGER_ZONE_MAX"):
            config_dict["review_danger_zone_max"] = float(review_danger_zone_max)
        if auto_reinforce := os.getenv("CORTEXGRAPH_AUTO_REINFORCE"):
            config_dict["auto_reinforce"] = auto_reinforce.lower() in ("true", "1", "yes")

        # Auto-recall
        if auto_recall_enabled := os.getenv("CORTEXGRAPH_AUTO_RECALL_ENABLED"):
            config_dict["auto_recall_enabled"] = auto_recall_enabled.lower() in ("true", "1", "yes")
        if auto_recall_mode := os.getenv("CORTEXGRAPH_AUTO_RECALL_MODE"):
            config_dict["auto_recall_mode"] = auto_recall_mode
        if auto_recall_relevance_threshold := os.getenv(
            "CORTEXGRAPH_AUTO_RECALL_RELEVANCE_THRESHOLD"
        ):
            config_dict["auto_recall_relevance_threshold"] = float(auto_recall_relevance_threshold)
        if auto_recall_max_results := os.getenv("CORTEXGRAPH_AUTO_RECALL_MAX_RESULTS"):
            config_dict["auto_recall_max_results"] = int(auto_recall_max_results)
        if auto_recall_min_interval := os.getenv("CORTEXGRAPH_AUTO_RECALL_MIN_INTERVAL"):
            config_dict["auto_recall_min_interval"] = int(auto_recall_min_interval)

        # Long-Term Memory
        if ltm_vault_path := os.getenv("LTM_VAULT_PATH"):
            config_dict["ltm_vault_path"] = ltm_vault_path
        if ltm_index_path := os.getenv("LTM_INDEX_PATH"):
            config_dict["ltm_index_path"] = ltm_index_path
        if ltm_promoted_folder := os.getenv("LTM_PROMOTED_FOLDER"):
            config_dict["ltm_promoted_folder"] = ltm_promoted_folder
        if ltm_index_filename := os.getenv("LTM_INDEX_FILENAME"):
            config_dict["ltm_index_filename"] = ltm_index_filename
        if ltm_legacy_index_filename := os.getenv("LTM_LEGACY_INDEX_FILENAME"):
            config_dict["ltm_legacy_index_filename"] = ltm_legacy_index_filename
        if ltm_index_max_age_seconds := os.getenv("CORTEXGRAPH_LTM_INDEX_MAX_AGE_SECONDS"):
            config_dict["ltm_index_max_age_seconds"] = int(ltm_index_max_age_seconds)

        # Short-Term Memory Storage Filenames
        if stm_memories_filename := os.getenv("CORTEXGRAPH_MEMORIES_FILENAME"):
            config_dict["stm_memories_filename"] = stm_memories_filename
        if stm_relations_filename := os.getenv("CORTEXGRAPH_RELATIONS_FILENAME"):
            config_dict["stm_relations_filename"] = stm_relations_filename

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
        if search_preview_length := os.getenv("CORTEXGRAPH_SEARCH_PREVIEW_LENGTH"):
            config_dict["search_default_preview_length"] = int(search_preview_length)

        # Legacy Integration (ignored)

        # Logging
        if log_level := os.getenv("LOG_LEVEL"):
            config_dict["log_level"] = log_level

        # Security
        if detect_secrets := os.getenv("CORTEXGRAPH_DETECT_SECRETS"):
            config_dict["detect_secrets"] = detect_secrets.lower() in ("true", "1", "yes")

        return cls(**cast(dict[str, Any], config_dict))

    # No-op: JSONL storage ensures its own directory


# Global configuration instance
_config: Config | None = None


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
