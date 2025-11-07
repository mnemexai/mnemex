"""Secrets detection - identify potential secrets in memory content.

This module provides pattern-based detection of common secrets like API keys,
tokens, passwords, and credentials. It's designed to warn users before they
accidentally store sensitive data in memory.

Security Objectives:
1. Detect API keys, tokens, and credentials before storage
2. Warn users about potential secret exposure
3. Prevent accidental logging of secrets
4. Configurable detection (can be disabled if needed)

References:
- CWE-798: Use of Hard-coded Credentials
- CWE-312: Cleartext Storage of Sensitive Information
- OWASP: https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password
"""

import re
from dataclasses import dataclass

# Secret detection patterns
# These patterns are designed to minimize false positives while catching real secrets

PATTERNS = {
    # Generic API keys and tokens
    "api_key": re.compile(
        r"(?i)(api[_-]?key|apikey|api[_-]?token|access[_-]?key)[\s=:\"']+([a-zA-Z0-9_\-]{20,})",
        re.IGNORECASE,
    ),
    # AWS keys
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "aws_secret_key": re.compile(
        r"(?i)aws[_-]?secret[_-]?access[_-]?key[\s=:\"']+([a-zA-Z0-9/+=]{40})"
    ),
    # GitHub tokens
    "github_token": re.compile(r"gh[pours]_[a-zA-Z0-9]{36,}"),
    "github_classic": re.compile(r"ghp_[a-zA-Z0-9]{36,}"),
    # OpenAI API keys
    "openai_key": re.compile(r"sk-[a-zA-Z0-9]{48,}"),
    # Anthropic API keys
    "anthropic_key": re.compile(r"sk-ant-[a-zA-Z0-9\-]{95,}"),
    # Google API keys
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    # Slack tokens
    "slack_token": re.compile(r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,}"),
    # Generic tokens
    "bearer_token": re.compile(r"(?i)bearer[\s]+([a-zA-Z0-9_\-\.]{20,})"),
    # JWT tokens
    "jwt_token": re.compile(r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+"),
    # Private keys (PEM format)
    "private_key": re.compile(
        r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
        re.IGNORECASE,
    ),
    # Database connection strings
    "database_url": re.compile(
        r"(?i)(postgres|mysql|mongodb|redis)://[^\s@]+:[^\s@]+@[^\s]+",
    ),
    # Generic password patterns (conservative to avoid false positives)
    "password_assignment": re.compile(
        r"(?i)(password|passwd|pwd)[\s=:\"']+([^\s\"']{8,})",
    ),
    # Generic secret patterns
    "secret_assignment": re.compile(
        r"(?i)(secret|token|credential)[\s=:\"']+([a-zA-Z0-9_\-\.]{20,})",
    ),
}


@dataclass
class SecretMatch:
    """Represents a detected secret."""

    secret_type: str
    """Type of secret detected (e.g., 'api_key', 'aws_access_key')"""

    position: int
    """Character position in the text where secret was found"""

    context: str
    """Surrounding context (truncated, with secret partially redacted)"""


def detect_secrets(
    text: str,
    *,
    max_matches: int = 10,
    context_chars: int = 40,
) -> list[SecretMatch]:
    """Detect potential secrets in text using pattern matching.

    This function scans text for common secret patterns like API keys, tokens,
    and passwords. It's designed to be conservative to minimize false positives
    while catching real secrets.

    Args:
        text: Text to scan for secrets
        max_matches: Maximum number of matches to return (default: 10)
        context_chars: Number of context characters to include (default: 40)

    Returns:
        List of SecretMatch objects for detected secrets

    Examples:
        >>> text = "My API key is sk-1234567890abcdef"
        >>> matches = detect_secrets(text)
        >>> matches[0].secret_type
        'openai_key'
    """
    matches: list[SecretMatch] = []

    for secret_type, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            if len(matches) >= max_matches:
                break

            # Get context around the match
            start = max(0, match.start() - context_chars)
            end = min(len(text), match.end() + context_chars)
            context = text[start:end]

            # Partially redact the matched secret in context
            matched_text = match.group(0)
            if len(matched_text) > 10:
                redacted = matched_text[:4] + "..." + matched_text[-4:]
            else:
                redacted = "***"

            context = context.replace(matched_text, redacted)

            matches.append(
                SecretMatch(
                    secret_type=secret_type,
                    position=match.start(),
                    context=context.strip(),
                )
            )

        if len(matches) >= max_matches:
            break

    return matches


def scan_file_for_secrets(
    file_path: str,
    *,
    max_matches: int = 10,
) -> list[SecretMatch]:
    """Scan a file for potential secrets.

    Args:
        file_path: Path to file to scan
        max_matches: Maximum number of matches to return

    Returns:
        List of SecretMatch objects for detected secrets

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file can't be read
    """
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {file_path}") from e
    except PermissionError as e:
        raise PermissionError(f"Permission denied reading file: {file_path}") from e

    return detect_secrets(content, max_matches=max_matches)


def format_secret_warning(matches: list[SecretMatch]) -> str:
    """Format a user-friendly warning message about detected secrets.

    Args:
        matches: List of detected secrets

    Returns:
        Formatted warning message

    Examples:
        >>> matches = [SecretMatch("api_key", 10, "key = sk-...")]
        >>> print(format_secret_warning(matches))
        ⚠️  WARNING: Detected 1 potential secret in content!
        ...
    """
    if not matches:
        return ""

    lines = [
        f"⚠️  WARNING: Detected {len(matches)} potential secret{'s' if len(matches) != 1 else ''} in content!",
        "",
        "Secret types detected:",
    ]

    # Group by type
    by_type: dict[str, int] = {}
    for match in matches:
        by_type[match.secret_type] = by_type.get(match.secret_type, 0) + 1

    for secret_type, count in sorted(by_type.items()):
        lines.append(f"  - {secret_type}: {count}")

    lines.extend(
        [
            "",
            "This content may contain sensitive information that should not be stored.",
            "Consider:",
            "  1. Using environment variables for secrets",
            "  2. Using a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)",
            "  3. Removing secrets from memory content",
            "",
            "To disable secrets detection, set CORTEXGRAPH_DETECT_SECRETS=false in your .env file.",
        ]
    )

    return "\n".join(lines)


def should_warn_about_secrets(
    matches: list[SecretMatch],
    *,
    min_confidence_types: set[str] | None = None,
) -> bool:
    """Determine if we should warn the user about detected secrets.

    This function applies heuristics to reduce false positives. For example,
    we might be more confident about AWS keys than generic "api_key" patterns.

    Args:
        matches: List of detected secrets
        min_confidence_types: Set of secret types we're very confident about
                              (default: AWS, GitHub, OpenAI, Anthropic, etc.)

    Returns:
        True if we should warn the user, False otherwise
    """
    if not matches:
        return False

    # High-confidence secret types (very unlikely to be false positives)
    if min_confidence_types is None:
        min_confidence_types = {
            "aws_access_key",
            "aws_secret_key",
            "github_token",
            "github_classic",
            "openai_key",
            "anthropic_key",
            "google_api_key",
            "slack_token",
            "private_key",
            "database_url",
            "jwt_token",
        }

    # Warn if ANY high-confidence type detected
    for match in matches:
        if match.secret_type in min_confidence_types:
            return True

    # For lower-confidence types, only warn if multiple matches
    return len(matches) >= 2


def redact_secrets(text: str, replacement: str = "***REDACTED***") -> str:
    """Redact detected secrets from text for safe logging.

    This function is useful for sanitizing log messages to prevent
    accidental secret exposure in logs.

    Args:
        text: Text to redact secrets from
        replacement: Replacement string for secrets (default: "***REDACTED***")

    Returns:
        Text with secrets replaced by redaction string

    Examples:
        >>> text = "My API key is sk-1234567890"
        >>> redact_secrets(text)
        'My API key is ***REDACTED***'
    """
    redacted = text

    for pattern in PATTERNS.values():
        redacted = pattern.sub(replacement, redacted)

    return redacted


def main() -> int:
    """CLI entry point for secrets detection."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Scan text or files for potential secrets")
    parser.add_argument(
        "input",
        nargs="?",
        help="File to scan (if omitted, reads from stdin)",
    )
    parser.add_argument(
        "--max-matches",
        type=int,
        default=10,
        help="Maximum matches to report (default: 10)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output if secrets found (exit code 1)",
    )
    parser.add_argument(
        "--redact",
        action="store_true",
        help="Output text with secrets redacted",
    )

    args = parser.parse_args()

    try:
        # Read input
        if args.input:
            matches = scan_file_for_secrets(args.input, max_matches=args.max_matches)
            with open(args.input, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        else:
            content = sys.stdin.read()
            matches = detect_secrets(content, max_matches=args.max_matches)

        # Redact mode
        if args.redact:
            print(redact_secrets(content))
            return 0

        # Report mode
        if matches:
            if not args.quiet:
                print(format_secret_warning(matches), file=sys.stderr)
            return 1
        else:
            if not args.quiet:
                print("✓ No secrets detected", file=sys.stderr)
            return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
