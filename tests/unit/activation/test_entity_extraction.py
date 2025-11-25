"""
Unit tests for entity extraction.

Tests EntityExtractor and extract_entities() for:
- Technology pattern matching (AI models, frameworks, languages, databases)
- spaCy entity detection (PERSON, ORG, PRODUCT, GPE, EVENT)
- Fallback regex patterns when spaCy unavailable
- max_entities limiting
- Stopword filtering
- Deduplication and sorting
"""

import pytest

from cortexgraph.activation.entity_extraction import EntityExtractor, extract_entities


class TestEntityExtractorInit:
    """Tests for EntityExtractor initialization."""

    def test_init_default_model(self):
        """Test EntityExtractor initializes with default model."""
        extractor = EntityExtractor()

        # Should have tech patterns compiled
        assert extractor.tech_regex is not None
        assert extractor.fallback_regex is not None

    def test_init_custom_model(self):
        """Test EntityExtractor with custom model name."""
        # This may fail to load, but should not raise
        extractor = EntityExtractor(model_name="en_core_web_md")

        assert extractor.tech_regex is not None

    def test_is_available_method(self):
        """Test is_available() indicates spaCy status."""
        extractor = EntityExtractor()

        # Should return bool
        available = extractor.is_available()
        assert isinstance(available, bool)


class TestTechnologyPatternMatching:
    """Tests for technology-specific pattern extraction."""

    def test_ai_model_detection(self):
        """Test AI model names are extracted."""
        extractor = EntityExtractor()
        text = "I prefer Claude over GPT-4 for coding tasks"

        entities = extractor.extract(text)

        assert "claude" in entities
        assert "gpt-4" in entities

    def test_framework_detection(self):
        """Test framework names are extracted."""
        extractor = EntityExtractor()
        text = "FastAPI and Django are Python frameworks"

        entities = extractor.extract(text)

        assert "fastapi" in entities
        assert "django" in entities
        assert "python" in entities

    def test_language_detection(self):
        """Test programming language names."""
        extractor = EntityExtractor()
        text = "I use Python, JavaScript, and Rust"

        entities = extractor.extract(text)

        assert "python" in entities
        assert "javascript" in entities
        assert "rust" in entities

    def test_protocol_detection(self):
        """Test protocol names are extracted."""
        extractor = EntityExtractor()
        text = "MCP uses HTTP and WebSocket for transport"

        entities = extractor.extract(text)

        assert "mcp" in entities
        assert "http" in entities
        assert "websocket" in entities

    def test_database_detection(self):
        """Test database names are extracted."""
        extractor = EntityExtractor()
        text = "I prefer PostgreSQL over MongoDB for my project"

        entities = extractor.extract(text)

        assert "postgresql" in entities
        assert "mongodb" in entities

    def test_case_insensitive_tech_matching(self):
        """Test technology patterns match case-insensitively."""
        extractor = EntityExtractor()
        text = "POSTGRESQL and fastapi and PyTorch"

        entities = extractor.extract(text)

        # All should be lowercase in output
        assert "postgresql" in entities
        assert "fastapi" in entities
        assert "pytorch" in entities


class TestSpacyEntityExtraction:
    """Tests for spaCy-based entity extraction (if available)."""

    def test_spacy_person_entity(self):
        """Test PERSON entities extracted if spaCy available."""
        extractor = EntityExtractor()

        if not extractor.is_available():
            pytest.skip("spaCy model not available")

        text = "Scot Campbell and Anthropic are working on Claude"

        entities = extractor.extract(text)

        # Should extract person name (if spaCy NER detects it)
        # Note: This may be flaky depending on spaCy model
        assert any("scot" in e or "campbell" in e for e in entities)

    def test_spacy_org_entity(self):
        """Test ORG entities extracted if spaCy available."""
        extractor = EntityExtractor()

        if not extractor.is_available():
            pytest.skip("spaCy model not available")

        text = "Anthropic and OpenAI are AI research companies"

        entities = extractor.extract(text)

        # Should extract organization names
        assert "anthropic" in entities or "openai" in entities

    def test_spacy_product_entity(self):
        """Test PRODUCT entities extracted if spaCy available."""
        extractor = EntityExtractor()

        if not extractor.is_available():
            pytest.skip("spaCy model not available")

        text = "I use ChatGPT and Claude for my research"

        entities = extractor.extract(text)

        # ChatGPT might be detected as PRODUCT
        # Claude will be detected by tech patterns
        assert "claude" in entities

    def test_spacy_gpe_entity(self):
        """Test GPE (location) entities extracted if spaCy available."""
        extractor = EntityExtractor()

        if not extractor.is_available():
            pytest.skip("spaCy model not available")

        text = "I live in Charlotte, North Carolina"

        entities = extractor.extract(text)

        # Should extract location names
        assert any("charlotte" in e or "carolina" in e for e in entities)


class TestFallbackPatternExtraction:
    """Tests for fallback regex patterns when spaCy unavailable."""

    def test_fallback_capitalized_words(self):
        """Test fallback extracts capitalized words."""
        extractor = EntityExtractor()

        # Force fallback by setting nlp to None
        original_nlp = extractor.nlp
        extractor.nlp = None

        text = "Remember this: John Smith works at Acme Corporation"

        entities = extractor.extract(text)

        # Should extract multi-word capitalized sequences as fallback
        # Regex pattern matches "John Smith" and "Acme Corporation" as single entities
        assert any(
            "john smith" in e or "acme corporation" in e or "remember" in e for e in entities
        )

        # Restore original nlp
        extractor.nlp = original_nlp

    def test_fallback_email_detection(self):
        """Test fallback extracts email addresses."""
        extractor = EntityExtractor()

        # Force fallback
        original_nlp = extractor.nlp
        extractor.nlp = None

        text = "Contact me at scot@prefrontal.systems for details"

        entities = extractor.extract(text)

        # Should extract email
        assert "scot@prefrontal.systems" in entities

        extractor.nlp = original_nlp

    def test_fallback_url_detection(self):
        """Test fallback extracts URLs."""
        extractor = EntityExtractor()

        # Force fallback
        original_nlp = extractor.nlp
        extractor.nlp = None

        test_url = "https://cortexgraph.dev"
        text = f"Check out {test_url} for documentation"

        entities = extractor.extract(text)

        # Should extract URL (this is entity extraction, not URL sanitization)
        # lgtm[py/incomplete-url-substring-sanitization]
        assert test_url in entities

        extractor.nlp = original_nlp


class TestEntityLimitingAndSorting:
    """Tests for max_entities limiting and sorting behavior."""

    def test_max_entities_default(self):
        """Test default max_entities=10."""
        extractor = EntityExtractor()
        text = "Python JavaScript TypeScript Rust Go Java PostgreSQL MongoDB Redis SQLite FastAPI Django React Vue PyTorch TensorFlow"

        entities = extractor.extract(text)

        # Should limit to 10
        assert len(entities) <= 10

    def test_max_entities_custom_limit(self):
        """Test custom max_entities limit."""
        extractor = EntityExtractor()
        text = "Python JavaScript TypeScript Rust Go Java"

        entities = extractor.extract(text, max_entities=3)

        # Should limit to 3
        assert len(entities) <= 3

    def test_sorting_by_length(self):
        """Test entities sorted by length (longest first)."""
        extractor = EntityExtractor()

        # Force fallback to get predictable results
        original_nlp = extractor.nlp
        extractor.nlp = None

        text = "PostgreSQL is better than Redis for my use case with TypeScript"

        entities = extractor.extract(text)

        # Longer tech names should come first
        # postgresql (10) > typescript (10) > redis (5)
        if len(entities) >= 2:
            # First should be at least as long as second
            assert len(entities[0]) >= len(entities[1])

        extractor.nlp = original_nlp

    def test_deduplication(self):
        """Test entities are deduplicated."""
        extractor = EntityExtractor()
        text = "Python and Python and Python"

        entities = extractor.extract(text)

        # Should only have one "python"
        assert entities.count("python") == 1


class TestStopwordFiltering:
    """Tests for stopword removal."""

    def test_stopwords_removed(self):
        """Test common stopwords are filtered out."""
        extractor = EntityExtractor()

        # Force fallback to test stopword filtering
        original_nlp = extractor.nlp
        extractor.nlp = None

        text = "The API is better than the REST protocol"

        entities = extractor.extract(text)

        # Stopwords should be removed
        assert "the" not in entities
        assert "is" not in entities
        assert "than" not in entities

        extractor.nlp = original_nlp

    def test_stopwords_list_coverage(self):
        """Test all defined stopwords are filtered."""
        extractor = EntityExtractor()

        # Force fallback
        original_nlp = extractor.nlp
        extractor.nlp = None

        text = "the a an and or but in on at to for"

        entities = extractor.extract(text)

        # All stopwords should be removed
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        for stopword in stopwords:
            assert stopword not in entities

        extractor.nlp = original_nlp


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_text(self):
        """Test extraction from empty text."""
        extractor = EntityExtractor()
        entities = extractor.extract("")

        assert entities == []

    def test_no_entities_text(self):
        """Test text with no extractable entities."""
        extractor = EntityExtractor()
        text = "this is just some regular text without any entities"

        entities = extractor.extract(text)

        # Should return empty or minimal list
        assert isinstance(entities, list)

    def test_special_characters_in_text(self):
        """Test extraction with special characters."""
        extractor = EntityExtractor()
        text = "I use PostgreSQL (v14.5) for my database! It's great."

        entities = extractor.extract(text)

        # Should extract PostgreSQL despite special characters
        assert "postgresql" in entities

    def test_multiline_text(self):
        """Test extraction from multiline text."""
        extractor = EntityExtractor()
        text = """
        I prefer PostgreSQL for databases.
        FastAPI is my framework of choice.
        Python is the language I use.
        """

        entities = extractor.extract(text)

        assert "postgresql" in entities
        assert "fastapi" in entities
        assert "python" in entities

    def test_unicode_text(self):
        """Test extraction with unicode characters."""
        extractor = EntityExtractor()
        text = "I use PostgreSQL for my café's database ☕"

        entities = extractor.extract(text)

        assert "postgresql" in entities

    def test_very_long_text(self):
        """Test extraction from very long text."""
        extractor = EntityExtractor()
        long_text = "I use Python " * 100 + "and PostgreSQL for databases"

        entities = extractor.extract(long_text)

        # Should handle long text without error
        assert "python" in entities
        assert "postgresql" in entities


class TestConvenienceFunction:
    """Tests for extract_entities() convenience function."""

    def test_extract_entities_function(self):
        """Test convenience function extract_entities()."""
        text = "I prefer PostgreSQL and FastAPI for my projects"

        entities = extract_entities(text)

        assert isinstance(entities, list)
        assert "postgresql" in entities
        assert "fastapi" in entities

    def test_extract_entities_max_limit(self):
        """Test convenience function with max_entities."""
        text = "Python JavaScript TypeScript Rust Go Java"

        entities = extract_entities(text, max_entities=3)

        assert len(entities) <= 3

    def test_extract_entities_empty_text(self):
        """Test convenience function with empty text."""
        entities = extract_entities("")

        assert entities == []

    def test_extract_entities_creates_new_instance(self):
        """Test convenience function creates new extractor each call."""
        # Two calls should work independently
        entities1 = extract_entities("PostgreSQL and FastAPI")
        entities2 = extract_entities("MongoDB and Django")

        assert "postgresql" in entities1
        assert "mongodb" in entities2
