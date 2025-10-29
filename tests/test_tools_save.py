"""Tests for save_memory tool."""

import time
from unittest.mock import MagicMock, patch

import pytest

from mnemex.tools.save import save_memory


class TestSaveMemory:
    """Test suite for save_memory tool."""

    def test_save_basic_memory(self, temp_storage):
        """Test saving a basic memory with just content."""
        result = save_memory(content="This is a test memory")

        assert result["success"] is True
        assert "memory_id" in result
        assert "Memory saved with ID:" in result["message"]
        assert result["has_embedding"] is False

        # Verify memory was actually saved
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory is not None
        assert memory.content == "This is a test memory"
        assert memory.use_count == 0
        assert memory.entities == []
        assert memory.meta.tags == []

    def test_save_memory_with_tags(self, temp_storage):
        """Test saving memory with tags."""
        result = save_memory(content="Tagged memory", tags=["python", "testing", "mnemex"])

        assert result["success"] is True
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.meta.tags == ["python", "testing", "mnemex"]

    def test_save_memory_with_entities(self, temp_storage):
        """Test saving memory with entities."""
        result = save_memory(content="Memory about Claude", entities=["Claude", "Anthropic", "AI"])

        assert result["success"] is True
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.entities == ["Claude", "Anthropic", "AI"]

    def test_save_memory_with_source_and_context(self, temp_storage):
        """Test saving memory with source and context."""
        result = save_memory(
            content="Memory with metadata",
            source="user-input",
            context="During code review session",
        )

        assert result["success"] is True
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.meta.source == "user-input"
        assert memory.meta.context == "During code review session"

    def test_save_memory_with_custom_metadata(self, temp_storage):
        """Test saving memory with custom metadata."""
        custom_meta = {"priority": "high", "project": "mnemex"}
        result = save_memory(content="Memory with custom meta", meta=custom_meta)

        assert result["success"] is True
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.meta.extra == custom_meta

    def test_save_memory_all_fields(self, temp_storage):
        """Test saving memory with all optional fields."""
        result = save_memory(
            content="Complete memory",
            tags=["tag1", "tag2"],
            entities=["Entity1"],
            source="test-source",
            context="test-context",
            meta={"key": "value"},
        )

        assert result["success"] is True
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.content == "Complete memory"
        assert memory.meta.tags == ["tag1", "tag2"]
        assert memory.entities == ["Entity1"]
        assert memory.meta.source == "test-source"
        assert memory.meta.context == "test-context"
        assert memory.meta.extra == {"key": "value"}

    def test_save_memory_timestamps(self, temp_storage):
        """Test that timestamps are set correctly."""
        before = int(time.time())
        result = save_memory(content="Timestamp test")
        after = int(time.time())

        memory = temp_storage.get_memory(result["memory_id"])
        assert before <= memory.created_at <= after
        assert before <= memory.last_used <= after
        assert memory.created_at == memory.last_used

    def test_save_memory_unique_ids(self, temp_storage):
        """Test that each memory gets a unique ID."""
        result1 = save_memory(content="Memory 1")
        result2 = save_memory(content="Memory 2")
        result3 = save_memory(content="Memory 3")

        assert result1["memory_id"] != result2["memory_id"]
        assert result2["memory_id"] != result3["memory_id"]
        assert result1["memory_id"] != result3["memory_id"]

    # Validation tests
    def test_save_empty_content_fails(self):
        """Test that empty content fails validation."""
        with pytest.raises(ValueError, match="content.*empty"):
            save_memory(content="")

    def test_save_content_too_long_fails(self):
        """Test that content exceeding max length fails."""
        long_content = "x" * 50001  # MAX_CONTENT_LENGTH is 50000
        with pytest.raises(ValueError, match="content.*exceeds maximum"):
            save_memory(content=long_content)

    def test_save_too_many_tags_fails(self):
        """Test that too many tags fails validation."""
        too_many_tags = [f"tag{i}" for i in range(51)]  # MAX_TAGS_COUNT is 50
        with pytest.raises(ValueError, match="tags.*exceeds maximum"):
            save_memory(content="Test", tags=too_many_tags)

    def test_save_tag_too_long_fails(self):
        """Test that tags exceeding max length fail validation."""
        long_tag = "x" * 101  # Tags are limited to 100 chars
        with pytest.raises(ValueError, match="tag.*exceeds maximum"):
            save_memory(content="Test", tags=[long_tag])

    def test_save_invalid_tag_characters_sanitized(self, temp_storage):
        """Test that tags with invalid characters are auto-sanitized (MCP-friendly)."""
        result = save_memory(content="Test", tags=["invalid tag!"])
        assert result["success"] is True
        # Verify memory was saved with sanitized tag ("invalid tag!" -> "invalid_tag")
        memory = temp_storage.get_memory(result["memory_id"])
        assert "invalid_tag" in memory.meta.tags

    def test_save_too_many_entities_fails(self):
        """Test that too many entities fails validation."""
        too_many_entities = [f"entity{i}" for i in range(101)]  # MAX_ENTITIES_COUNT is 100
        with pytest.raises(ValueError, match="entities.*exceeds maximum"):
            save_memory(content="Test", entities=too_many_entities)

    def test_save_source_too_long_fails(self):
        """Test that source exceeding max length fails."""
        long_source = "x" * 501  # Source max is 500
        with pytest.raises(ValueError, match="source.*exceeds maximum"):
            save_memory(content="Test", source=long_source)

    def test_save_context_too_long_fails(self):
        """Test that context exceeding max length fails."""
        long_context = "x" * 1001  # Context max is 1000
        with pytest.raises(ValueError, match="context.*exceeds maximum"):
            save_memory(content="Test", context=long_context)

    # Edge cases
    def test_save_memory_with_none_tags(self, temp_storage):
        """Test that None tags are converted to empty list."""
        result = save_memory(content="Test", tags=None)
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.meta.tags == []

    def test_save_memory_with_empty_tags(self, temp_storage):
        """Test saving with empty tags list."""
        result = save_memory(content="Test", tags=[])
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.meta.tags == []

    def test_save_memory_with_none_entities(self, temp_storage):
        """Test that None entities are converted to empty list."""
        result = save_memory(content="Test", entities=None)
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.entities == []

    def test_save_memory_with_unicode_content(self, temp_storage):
        """Test saving memory with Unicode characters."""
        content = "Unicode test: 你好 🎉 café"
        result = save_memory(content=content)
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.content == content

    def test_save_memory_with_special_characters(self, temp_storage):
        """Test saving memory with special characters."""
        content = "Special chars: <tag> & \"quotes\" 'apostrophe' \\backslash"
        result = save_memory(content=content)
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.content == content

    # Secret detection tests (when enabled)
    @patch("mnemex.tools.save.get_config")
    @patch("mnemex.tools.save.detect_secrets")
    def test_save_warns_about_secrets_when_detected(
        self, mock_detect, mock_config, temp_storage, caplog
    ):
        """Test that secret detection warns but still saves memory."""
        from mnemex.security.secrets import SecretMatch

        # Setup mocks
        mock_config.return_value.detect_secrets = True
        # Mock a high-confidence secret to trigger the warning without patching should_warn_about_secrets
        mock_detect.return_value = [
            SecretMatch(secret_type="openai_key", position=0, context="...")
        ]

        result = save_memory(content="API key: sk-xxx123")

        # Memory should still be saved
        assert result["success"] is True

        # But warning should be logged
        assert "Secrets detected" in caplog.text

    # Embedding tests
    @patch("mnemex.tools.save.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("mnemex.tools.save.get_config")
    @patch("mnemex.tools.save.SentenceTransformer")
    def test_save_memory_with_embeddings_enabled(self, mock_transformer, mock_config, temp_storage):
        """Test that embeddings are generated when enabled."""
        # Setup mocks
        mock_config.return_value.enable_embeddings = True
        mock_config.return_value.embed_model = "test-model"
        mock_model = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = mock_embedding
        mock_transformer.return_value = mock_model

        result = save_memory(content="Test embedding")

        assert result["has_embedding"] is True
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.embed == [0.1, 0.2, 0.3]

    @patch("mnemex.tools.save.get_config")
    def test_save_memory_with_embeddings_disabled(self, mock_config, temp_storage):
        """Test that embeddings are not generated when disabled."""
        mock_config.return_value.enable_embeddings = False

        result = save_memory(content="Test no embedding")

        assert result["has_embedding"] is False
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.embed is None

    @patch("mnemex.tools.save.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("mnemex.tools.save.get_config")
    @patch("mnemex.tools.save.SentenceTransformer")
    def test_save_memory_embedding_import_error(self, mock_transformer, mock_config, temp_storage):
        """Test that import error in embedding generation is handled gracefully."""
        mock_config.return_value.enable_embeddings = True
        mock_transformer.side_effect = ImportError("No model found")

        result = save_memory(content="Test")

        # Should still save without embedding
        assert result["success"] is True
        assert result["has_embedding"] is False
