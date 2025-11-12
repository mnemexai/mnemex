"""Natural language processing utilities for memory activation.

This module provides keyword extraction and text processing for automatic
memory activation in CortexGraph.
"""

from rake_nltk import Rake


class KeywordExtractor:
    """Extract keywords from conversation messages for memory activation.

    Uses RAKE-NLTK (Rapid Automatic Keyword Extraction) with stopword filtering
    to identify meaningful concepts in user messages.
    """

    def __init__(self) -> None:
        """Initialize keyword extractor with RAKE and stopwords."""
        # Initialize RAKE with English stopwords
        # RAKE automatically downloads and uses NLTK stopwords
        self.rake = Rake()

    def extract_keywords(self, message: str, max_keywords: int = 20) -> list[str]:
        """Extract keywords from a message.

        Args:
            message: User message text to extract keywords from
            max_keywords: Maximum number of keywords to return (default: 20)

        Returns:
            List of extracted keywords, ranked by relevance (highest first)

        Example:
            >>> extractor = KeywordExtractor()
            >>> extractor.extract_keywords("Help me set up a TypeScript project")
            ['typescript project', 'set']  # Multi-word phrases preserved
        """
        if not message or not message.strip():
            return []

        # Extract keywords using RAKE
        self.rake.extract_keywords_from_text(message)

        # Get ranked keywords (by RAKE score, descending)
        keywords_with_scores = self.rake.get_ranked_phrases_with_scores()

        # Return top max_keywords phrases (RAKE returns tuples of (score, phrase))
        # Convert to lowercase for consistent matching
        keywords = [phrase.lower() for score, phrase in keywords_with_scores[:max_keywords]]

        return keywords
