"""Text utility functions."""


def truncate_content(content: str, max_length: int | None) -> str:
    """
    Truncate content to specified length with ellipsis.

    Args:
        content: The content to truncate.
        max_length: Maximum length (None or 0 = no truncation).

    Returns:
        Truncated content with "..." appended if truncated.
    """
    if max_length is None or max_length == 0 or len(content) <= max_length:
        return content

    return content[:max_length].rstrip() + "..."
