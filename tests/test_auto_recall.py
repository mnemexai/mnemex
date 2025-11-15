"""Tests for auto-recall system (conversational memory reinforcement)."""

import pytest

from cortexgraph.config import Config, set_config
from cortexgraph.core.auto_recall import (
    AutoRecallEngine,
    ConversationAnalyzer,
    RecallMode,
)
from cortexgraph.storage.models import Memory
from cortexgraph.tools.auto_recall_tool import auto_recall_process_message
from tests.conftest import make_test_uuid


class TestConversationAnalyzer:
    """Test conversation analysis for topic extraction and recall triggering."""

    def test_extract_topics_proper_nouns(self):
        """Test extraction of proper nouns (Title Case)."""
        analyzer = ConversationAnalyzer()

        message = "I'm working on the STOPPER Protocol implementation"
        topics = analyzer.extract_topics(message)

        assert "stopper" in topics  # Acronym
        assert "protocol" in topics  # Title Case
        assert "implementation" in topics  # Significant word
        assert "working" not in topics  # Stop word

    def test_extract_topics_hyphenated_terms(self):
        """Test extraction of hyphenated technical terms."""
        analyzer = ConversationAnalyzer()

        message = "Using auto-recall and spaced-repetition for memory"
        topics = analyzer.extract_topics(message)

        assert "auto-recall" in topics
        assert "spaced-repetition" in topics
        assert "memory" in topics

    def test_extract_topics_acronyms(self):
        """Test extraction of acronyms (ALL CAPS)."""
        analyzer = ConversationAnalyzer()

        message = "JWT authentication with API endpoints"
        topics = analyzer.extract_topics(message)

        assert "jwt" in topics
        assert "api" in topics
        assert "authentication" in topics
        assert "endpoints" in topics

    def test_extract_topics_filters_stop_words(self):
        """Test that common stop words are filtered out."""
        analyzer = ConversationAnalyzer()

        message = "I am working with the system and it is running"
        topics = analyzer.extract_topics(message)

        # Stop words should be filtered
        assert "the" not in topics
        assert "and" not in topics
        assert "with" not in topics
        assert "working" not in topics  # Now a stop word

        # Significant words should remain
        assert "system" in topics
        assert "running" in topics

    def test_should_trigger_recall_substantive_message(self):
        """Test triggering on substantive multi-topic messages."""
        analyzer = ConversationAnalyzer()

        message = "I'm implementing the STOPPER protocol for AI debugging workflows"
        should_trigger = analyzer.should_trigger_recall(message)

        assert should_trigger is True  # Multiple topics, substantive

    def test_should_trigger_recall_too_short(self):
        """Test no trigger on very short messages."""
        analyzer = ConversationAnalyzer()

        message = "Hi there"
        should_trigger = analyzer.should_trigger_recall(message)

        assert should_trigger is False  # Too short

    def test_should_trigger_recall_single_topic(self):
        """Test no trigger with single topic."""
        analyzer = ConversationAnalyzer()

        message = "Testing automation"
        should_trigger = analyzer.should_trigger_recall(message, min_topic_count=2)

        assert should_trigger is False  # Only 2 topics (testing, automation) - borderline

    def test_should_trigger_recall_pure_question(self):
        """Test no trigger on pure questions (handled by analyze_for_recall)."""
        analyzer = ConversationAnalyzer()

        message = "What did I say about STOPPER?"
        should_trigger = analyzer.should_trigger_recall(message)

        assert should_trigger is False  # Pure question

    def test_should_trigger_recall_discussion_with_question(self):
        """Test triggering on discussion that includes a question."""
        analyzer = ConversationAnalyzer()

        message = (
            "I'm implementing the STOPPER protocol. Should I add timing windows for the phases?"
        )
        should_trigger = analyzer.should_trigger_recall(message)

        assert should_trigger is True  # Discussion + question

    def test_get_context_tags(self):
        """Test context tag extraction from message."""
        analyzer = ConversationAnalyzer()

        message = "Working on JWT authentication with the API"
        tags = analyzer.get_context_tags(message)

        assert "jwt" in tags
        assert "authentication" in tags
        assert "api" in tags


class TestAutoRecallEngine:
    """Test auto-recall engine message processing."""

    def test_process_message_cooldown(self, temp_storage):
        """Test cooldown prevents too-frequent recalls."""
        config = Config(auto_recall_min_interval=5)  # 5 second cooldown
        set_config(config)

        engine = AutoRecallEngine(mode=RecallMode.SILENT)

        message = "Working on the STOPPER protocol implementation today"

        # First call should work
        result1 = engine.process_message(message, temp_storage)
        assert len(result1.topics_found) > 0

        # Immediate second call should be blocked by cooldown
        result2 = engine.process_message(message, temp_storage)
        assert len(result2.topics_found) == 0  # Cooldown prevented processing

    def test_process_message_extracts_topics(self, temp_storage):
        """Test topic extraction from message."""
        engine = AutoRecallEngine(mode=RecallMode.SILENT)

        message = "I'm working on the STOPPER Protocol for AI debugging"
        result = engine.process_message(message, temp_storage)

        assert len(result.topics_found) > 0
        assert "stopper" in [t.lower() for t in result.topics_found]
        assert "protocol" in [t.lower() for t in result.topics_found]

    def test_process_message_finds_related_memories(self, temp_storage):
        """Test finding and reinforcing related memories."""
        # Set lower relevance threshold for auto-recall (background reinforcement)
        config = Config(auto_recall_relevance_threshold=0.2)
        set_config(config)

        # Create a memory about STOPPER
        mem = Memory(
            id=make_test_uuid("mem-stopper"),
            content="STOPPER protocol has 7 phases for AI debugging",
            use_count=3,
            strength=1.0,
        )
        temp_storage.save_memory(mem)

        # Capture original use_count before auto-recall (mem object may be mutated)
        original_use_count = mem.use_count

        engine = AutoRecallEngine(mode=RecallMode.SILENT)

        message = "I'm implementing the STOPPER protocol workflow"
        result = engine.process_message(message, temp_storage)

        # Should find the STOPPER memory
        assert len(result.memories_found) > 0
        assert len(result.memories_reinforced) > 0

        # Check memory was reinforced
        updated = temp_storage.get_memory(mem.id)
        assert updated is not None
        assert updated.use_count > original_use_count  # Reinforcement incremented use_count

    def test_process_message_silent_mode_no_surfacing(self, temp_storage):
        """Test silent mode never surfaces memories."""
        # Create memory
        mem = Memory(
            id=make_test_uuid("mem-test"),
            content="Test memory content",
            use_count=3,
            strength=1.0,
        )
        temp_storage.save_memory(mem)

        engine = AutoRecallEngine(mode=RecallMode.SILENT)

        message = "Testing memory content retrieval"
        result = engine.process_message(message, temp_storage)

        # Phase 1: Silent mode - never surface
        assert result.should_surface is False
        assert result.surfacing_hint is None

    def test_process_message_no_related_memories(self, temp_storage):
        """Test behavior when no related memories found."""
        engine = AutoRecallEngine(mode=RecallMode.SILENT)

        message = "Discussing quantum entanglement in particle physics"
        result = engine.process_message(message, temp_storage)

        # Should extract topics but find no memories
        assert len(result.topics_found) > 0
        assert len(result.memories_found) == 0
        assert len(result.memories_reinforced) == 0

    def test_process_message_too_short_no_processing(self, temp_storage):
        """Test short messages don't trigger processing."""
        engine = AutoRecallEngine(mode=RecallMode.SILENT)

        message = "Hi"
        result = engine.process_message(message, temp_storage)

        # Too short - no processing
        assert len(result.topics_found) == 0
        assert len(result.memories_found) == 0


class TestAutoRecallTool:
    """Test MCP tool integration."""

    def test_auto_recall_disabled(self, temp_storage):
        """Test tool returns early when auto-recall disabled."""
        config = Config(auto_recall_enabled=False)
        set_config(config)

        result = auto_recall_process_message("Testing message")

        assert result["success"] is True
        assert result["enabled"] is False
        assert result["memories_found"] == 0
        assert "disabled" in result["message"].lower()

    def test_auto_recall_enabled(self, temp_storage):
        """Test tool processes message when enabled."""
        config = Config(auto_recall_enabled=True, auto_recall_min_interval=0)
        set_config(config)

        # Create a memory
        mem = Memory(
            id=make_test_uuid("mem-api"),
            content="JWT authentication for API endpoints",
            use_count=2,
            strength=1.0,
        )
        temp_storage.save_memory(mem)

        result = auto_recall_process_message("I'm working on JWT authentication implementation")

        assert result["success"] is True
        assert result["enabled"] is True
        assert len(result["topics_found"]) > 0
        assert result["mode"] == "silent"

    def test_auto_recall_validation_empty_message(self):
        """Test validation rejects empty messages."""
        config = Config(auto_recall_enabled=True)
        set_config(config)

        with pytest.raises(ValueError, match="cannot be empty"):
            auto_recall_process_message("")

    def test_auto_recall_validation_whitespace(self):
        """Test validation rejects whitespace-only messages."""
        config = Config(auto_recall_enabled=True)
        set_config(config)

        with pytest.raises(ValueError, match="cannot be empty"):
            auto_recall_process_message("   ")

    def test_auto_recall_result_format(self, temp_storage):
        """Test result dictionary has correct format."""
        config = Config(auto_recall_enabled=True, auto_recall_min_interval=0)
        set_config(config)

        result = auto_recall_process_message("Testing auto-recall functionality")

        assert "success" in result
        assert "enabled" in result
        assert "topics_found" in result
        assert "memories_found" in result
        assert "memories_reinforced" in result
        assert "mode" in result
        assert "message" in result

        assert isinstance(result["success"], bool)
        assert isinstance(result["enabled"], bool)
        assert isinstance(result["topics_found"], list)
        assert isinstance(result["memories_found"], int)
        assert isinstance(result["memories_reinforced"], list)
        assert isinstance(result["mode"], str)
        assert isinstance(result["message"], str)

    def test_auto_recall_respects_relevance_threshold(self, temp_storage):
        """Test that low-relevance memories are not recalled."""
        config = Config(
            auto_recall_enabled=True,
            auto_recall_relevance_threshold=0.9,  # Very high threshold
            auto_recall_min_interval=0,
        )
        set_config(config)

        # Create memory with different topic
        mem = Memory(
            id=make_test_uuid("mem-unrelated"),
            content="Quantum mechanics particle behavior",
            use_count=2,
            strength=1.0,
        )
        temp_storage.save_memory(mem)

        result = auto_recall_process_message("Working on JWT authentication system")

        # Should extract topics but not find memories (different domains)
        assert result["success"] is True
        assert len(result["topics_found"]) > 0
        assert result["memories_found"] == 0  # Below relevance threshold

    def test_auto_recall_respects_max_results(self, temp_storage):
        """Test that max_results limits recalled memories."""
        config = Config(
            auto_recall_enabled=True,
            auto_recall_max_results=2,
            auto_recall_min_interval=0,
        )
        set_config(config)

        # Create multiple related memories
        for i in range(5):
            mem = Memory(
                id=make_test_uuid(f"mem-auth-{i}"),
                content=f"JWT authentication implementation detail {i}",
                use_count=2,
                strength=1.0,
            )
            temp_storage.save_memory(mem)

        result = auto_recall_process_message("Implementing JWT authentication workflow")

        # Should limit to max_results
        assert result["success"] is True
        assert result["memories_found"] <= config.auto_recall_max_results
