"""
Entity extraction for natural language activation.

This module re-exports the CortexGraph entity extractor for use in
activation detection. The extractor uses spaCy NER when available,
with fallback to regex patterns for technology-specific entities.

Entity types extracted:
- Technology names (frameworks, languages, protocols, databases)
- People (PERSON)
- Organizations (ORG)
- Products/tools (PRODUCT)
- Locations (GPE)
- Events (EVENT)
- URLs and email addresses
"""

from cortexgraph.preprocessing.entity_extractor import EntityExtractor

__all__ = ["EntityExtractor", "extract_entities"]


def extract_entities(text: str, max_entities: int = 10) -> list[str]:
    """Extract named entities from text using default extractor.

    Convenience function for one-off entity extraction without creating
    an extractor instance.

    Args:
        text: Natural language text to analyze
        max_entities: Maximum entities to return (default: 10)

    Returns:
        List of entity strings (lowercase, deduplicated)

    Example:
        >>> entities = extract_entities("I prefer PostgreSQL for databases")
        >>> "postgresql" in entities
        True

    Note:
        This creates a new EntityExtractor each call. For repeated extractions,
        create an EntityExtractor instance and reuse it.
    """
    extractor = EntityExtractor()
    return extractor.extract(text, max_entities=max_entities)
