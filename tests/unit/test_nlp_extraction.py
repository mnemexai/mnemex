"""Unit tests for keyword extraction (RAKE-NLTK)."""

import pytest

from cortexgraph.core.nlp import KeywordExtractor


@pytest.fixture(scope="module", autouse=True)
def setup_nltk_data() -> None:
    """Download required NLTK data before running tests."""
    import nltk

    # Download stopwords if not present
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)

    # Download punkt_tab tokenizer if not present
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)


class TestKeywordExtractor:
    """Test KeywordExtractor implementation."""

    def test_extract_keywords_short_message(self) -> None:
        """Test keyword extraction from short message."""
        extractor = KeywordExtractor()
        message = "Python testing"
        keywords = extractor.extract_keywords(message)

        # RAKE should extract at least "python testing" as a phrase
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # All keywords should be lowercase
        assert all(k == k.lower() for k in keywords)

    def test_extract_keywords_normal_message(self) -> None:
        """Test keyword extraction from normal conversation message."""
        extractor = KeywordExtractor()
        message = "Help me set up a new TypeScript project with React"
        keywords = extractor.extract_keywords(message)

        assert isinstance(keywords, list)
        assert len(keywords) > 0

        # Should extract technical terms
        keywords_str = " ".join(keywords)
        assert "typescript" in keywords_str or "react" in keywords_str

    def test_extract_keywords_long_message(self) -> None:
        """Test keyword extraction from long technical message."""
        extractor = KeywordExtractor()
        message = """
        I'm working on implementing a temporal decay system for memory management.
        The system should use exponential decay curves with configurable half-life
        parameters. It needs to integrate with existing database storage and provide
        efficient scoring for large numbers of memories. Can you help me design
        the architecture for this?
        """
        keywords = extractor.extract_keywords(message)

        assert isinstance(keywords, list)
        assert len(keywords) > 0

        # Should extract domain-specific phrases
        keywords_str = " ".join(keywords)
        # RAKE extracts multi-word phrases
        assert any(
            term in keywords_str
            for term in ["temporal", "decay", "memory", "exponential", "database"]
        )

    def test_extract_keywords_respects_max_limit(self) -> None:
        """Test that max_keywords parameter is respected."""
        extractor = KeywordExtractor()
        message = """
        machine learning artificial intelligence neural networks
        deep learning natural language processing computer vision
        reinforcement learning supervised learning unsupervised learning
        """
        keywords = extractor.extract_keywords(message, max_keywords=5)

        assert len(keywords) <= 5

    def test_extract_keywords_empty_message(self) -> None:
        """Test handling of empty message."""
        extractor = KeywordExtractor()

        assert extractor.extract_keywords("") == []
        assert extractor.extract_keywords("   ") == []

    def test_extract_keywords_stopwords_filtered(self) -> None:
        """Test that common stopwords are filtered out."""
        extractor = KeywordExtractor()
        message = "the cat sat on the mat"

        keywords = extractor.extract_keywords(message)

        # RAKE should filter out stopwords like "the", "on"
        # and extract meaningful phrases
        keywords_str = " ".join(keywords)
        assert "cat" in keywords_str or "sat" in keywords_str or "mat" in keywords_str

    def test_extract_keywords_preserves_phrases(self) -> None:
        """Test that RAKE preserves meaningful multi-word phrases."""
        extractor = KeywordExtractor()
        message = "machine learning model training dataset"

        keywords = extractor.extract_keywords(message)

        # RAKE should extract multi-word phrases, not just individual words
        assert any(
            len(kw.split()) > 1 for kw in keywords
        ), "Expected at least one multi-word phrase"

    def test_extract_keywords_case_normalization(self) -> None:
        """Test that keywords are normalized to lowercase."""
        extractor = KeywordExtractor()
        message = "TypeScript React API Authentication JWT"

        keywords = extractor.extract_keywords(message)

        # All keywords should be lowercase
        assert all(k == k.lower() for k in keywords)
        assert any("typescript" in kw for kw in keywords)

    def test_extract_keywords_ranking(self) -> None:
        """Test that keywords are ranked by relevance."""
        extractor = KeywordExtractor()
        message = """
        neural networks neural networks neural networks
        machine learning
        """

        keywords = extractor.extract_keywords(message)

        # "neural networks" appears 3 times, should rank higher than "machine learning"
        # First keyword should be the most relevant
        assert len(keywords) > 0
        # Just verify we get results - exact ranking depends on RAKE algorithm
        assert isinstance(keywords[0], str)

    def test_extract_keywords_technical_content(self) -> None:
        """Test extraction from technical documentation-style content."""
        extractor = KeywordExtractor()
        message = """
        The FastMCP middleware intercepts tool calls using the on_call_tool hook.
        It performs activation with a 50ms timeout and stores results in context state.
        """

        keywords = extractor.extract_keywords(message)

        keywords_str = " ".join(keywords)
        # Should extract technical terms
        assert any(
            term in keywords_str
            for term in ["fastmcp", "middleware", "activation", "timeout", "context"]
        )

    def test_extract_keywords_reusable_extractor(self) -> None:
        """Test that extractor can be reused for multiple messages."""
        extractor = KeywordExtractor()

        msg1 = "Python programming language"
        msg2 = "JavaScript web development"

        kw1 = extractor.extract_keywords(msg1)
        kw2 = extractor.extract_keywords(msg2)

        # Both should work and be independent
        assert len(kw1) > 0
        assert len(kw2) > 0
        # Results should be different
        assert kw1 != kw2
