"""
Comprehensive tests for the `cortexgraph.security.secrets` module.

This test suite is designed to ensure the effectiveness of the secret
detection and handling capabilities within the application. It covers a
wide array of secret patterns, including API keys from various services
(AWS, OpenAI, GitHub), private keys, database URLs, and generic password
or token assignments.

The tests verify:
- The `detect_secrets` function's ability to identify different secret
  formats in text.
- The `scan_file_for_secrets` function for file-based scanning.
- The `redact_secrets` function to ensure secrets are properly removed
  from text.
- The logic for warning users about found secrets (`should_warn_about_secrets`
  and `format_secret_warning`).
- The command-line interface for scanning files and stdin, including
  redaction and quiet modes.
- The structural integrity of the `SecretMatch` data class.
"""

import io
import sys
import tempfile
from pathlib import Path

import pytest

from cortexgraph.security.secrets import (
    SecretMatch,
    detect_secrets,
    format_secret_warning,
    main,
    redact_secrets,
    scan_file_for_secrets,
    should_warn_about_secrets,
)


class TestSecretMatch:
    """
    Tests for the `SecretMatch` dataclass.

    These tests ensure that the `SecretMatch` dataclass, which is used to
    store information about a found secret, is correctly instantiated and
    has the expected attributes.
    """

    def test_create_secret_match_instance(self):
        """Test creating a SecretMatch instance."""
        match = SecretMatch(
            secret_type="api_key",
            position=10,
            context="API key: sk-...",
        )

        assert match.secret_type == "api_key"
        assert match.position == 10
        assert match.context == "API key: sk-..."

    def test_secret_match_attributes(self):
        """Test SecretMatch has correct attributes."""
        match = SecretMatch(
            secret_type="aws_access_key",
            position=42,
            context="AWS key: AKIA...",
        )

        assert hasattr(match, "secret_type")
        assert hasattr(match, "position")
        assert hasattr(match, "context")

    def test_secret_match_with_different_types(self):
        """Test creating SecretMatch with various secret types."""
        types = ["openai_key", "github_token", "database_url", "jwt_token"]

        for secret_type in types:
            match = SecretMatch(
                secret_type=secret_type,
                position=0,
                context="test context",
            )
            assert match.secret_type == secret_type


class TestDetectSecretsAPIKeys:
    """
    Tests for `detect_secrets` focusing on generic API key patterns.

    This class verifies the detection of common, non-vendor-specific API
    key and token formats.
    """

    def test_detect_generic_api_key_uppercase(self):
        """Test detecting generic API_KEY pattern."""
        text = "API_KEY=abcd1234efgh5678ijkl9012mnop3456qrst"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "api_key" for m in matches)

    def test_detect_generic_api_key_lowercase(self):
        """Test detecting lowercase api_key pattern."""
        text = "api_key: abcd1234efgh5678ijkl9012mnop3456qrst"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "api_key" for m in matches)

    def test_detect_api_token(self):
        """Test detecting API_TOKEN pattern."""
        text = "API_TOKEN = xyz123abc456def789ghi012jkl345mno"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "api_key" for m in matches)

    def test_detect_access_key(self):
        """Test detecting ACCESS_KEY pattern."""
        text = 'ACCESS_KEY="test1234567890abcdefghij"'
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "api_key" for m in matches)


class TestDetectSecretsAWS:
    """
    Tests for `detect_secrets` focusing on AWS credential patterns.

    This class ensures that AWS-specific secret formats, such as Access Key IDs
    and Secret Access Keys, are correctly identified.
    """

    def test_detect_aws_access_key_id(self):
        """Test detecting AWS access key (AKIA...)."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "aws_access_key" for m in matches)

    def test_detect_aws_access_key_in_sentence(self):
        """Test detecting AWS access key embedded in text."""
        text = "My access key is AKIAI44QH8DHBEXAMPLE and it's secret"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "aws_access_key" for m in matches)

    def test_detect_aws_secret_access_key(self):
        """Test detecting AWS secret access key."""
        text = "aws_secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "aws_secret_key" for m in matches)

    def test_detect_aws_secret_with_equals(self):
        """Test detecting AWS secret with equals sign."""
        text = "AWS_SECRET_ACCESS_KEY=abcd1234efgh5678ijkl9012mnop3456qrst7890"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "aws_secret_key" for m in matches)


class TestDetectSecretsGitHub:
    """
    Tests for `detect_secrets` focusing on GitHub token patterns.

    This class verifies the detection of various GitHub token formats,
    including Personal Access Tokens (classic and fine-grained) and OAuth tokens.
    """

    def test_detect_github_personal_access_token(self):
        """Test detecting GitHub personal access token (ghp_)."""
        text = "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyzABCDEF"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type in ("github_token", "github_classic") for m in matches)

    def test_detect_github_oauth_token(self):
        """Test detecting GitHub OAuth token (gho_)."""
        text = "token: gho_abcdefghijklmnopqrstuvwxyz1234567890ABCDEF"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "github_token" for m in matches)

    def test_detect_github_user_to_server_token(self):
        """Test detecting GitHub user-to-server token (ghu_)."""
        text = "Authorization: ghu_1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "github_token" for m in matches)

    def test_detect_github_server_to_server_token(self):
        """Test detecting GitHub server-to-server token (ghs_)."""
        text = "GH_TOKEN=ghs_abcdefghijklmnopqrstuvwxyz1234567890ABCD"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "github_token" for m in matches)

    def test_detect_github_refresh_token(self):
        """Test detecting GitHub refresh token (ghr_)."""
        text = "refresh_token=ghr_1234567890abcdefghijklmnopqrstuvwxyzABCDEF"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "github_token" for m in matches)


class TestDetectSecretsOpenAI:
    """
    Tests for `detect_secrets` focusing on OpenAI API key patterns.

    This class ensures that OpenAI's specific key format (`sk-...`) is
    correctly identified.
    """

    def test_detect_openai_api_key(self):
        """Test detecting OpenAI API key (sk-)."""
        text = "OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "openai_key" for m in matches)

    def test_detect_openai_key_in_code(self):
        """Test detecting OpenAI key in code snippet."""
        text = 'client = OpenAI(api_key="sk-abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNO")'
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "openai_key" for m in matches)


class TestDetectSecretsAnthropic:
    """
    Tests for `detect_secrets` focusing on Anthropic API key patterns.

    This class ensures that Anthropic's specific key format (`sk-ant-...`)
    is correctly identified.
    """

    def test_detect_anthropic_api_key(self):
        """Test detecting Anthropic API key (sk-ant-)."""
        text = "ANTHROPIC_API_KEY=sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqr"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "anthropic_key" for m in matches)

    def test_detect_anthropic_key_with_hyphens(self):
        """Test detecting Anthropic key with hyphens."""
        text = "api_key: sk-ant-api03-abcd-efgh-ijkl-mnop-qrst-uvwx-yzAB-CDEF-GHIJ-KLMN-OPQR-STUV-WXYZ-1234-5678-90ab-cdef-ghij-klmn"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "anthropic_key" for m in matches)


class TestDetectSecretsGoogle:
    """
    Tests for `detect_secrets` focusing on Google API key patterns.

    This class ensures that Google's specific key format (`AIza...`) is
    correctly identified.
    """

    def test_detect_google_api_key(self):
        """Test detecting Google API key (AIza...)."""
        text = "GOOGLE_API_KEY=AIzaSyD1234567890abcdefghijklmnopqrstuv"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "google_api_key" for m in matches)

    def test_detect_google_key_in_url(self):
        """Test detecting Google API key in URL."""
        text = "https://maps.googleapis.com/maps/api/geocode/json?key=AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567&address=test"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "google_api_key" for m in matches)


class TestDetectSecretsSlack:
    """
    Tests for `detect_secrets` focusing on Slack token patterns.

    This class verifies the detection of various Slack token formats,
    including bot, user, and app tokens.
    """

    def test_detect_slack_bot_token(self):
        """Test detecting Slack bot token (xoxb-)."""
        text = "SLACK_BOT_TOKEN=xoxb-1234567890-1234567890123-abcdefghijklmnopqrstuvwx"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "slack_token" for m in matches)

    def test_detect_slack_user_token(self):
        """Test detecting Slack user token (xoxp-)."""
        text = "token: xoxp-1234567890-1234567890-abcdefghijklmnopqrstuvwx"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "slack_token" for m in matches)

    def test_detect_slack_app_token(self):
        """Test detecting Slack app token (xoxa-)."""
        text = "SLACK_APP_TOKEN=xoxa-1234567890-1234567890123-abcdefghijklmnopqrstuvwx"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "slack_token" for m in matches)


class TestDetectSecretsBearerTokens:
    """
    Tests for `detect_secrets` focusing on Bearer token patterns.

    This class ensures that generic Bearer tokens, often used in
    Authorization headers, are correctly identified.
    """

    def test_detect_bearer_token_uppercase(self):
        """Test detecting Bearer token (uppercase)."""
        text = "Authorization: Bearer abcdef1234567890ghijkl"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "bearer_token" for m in matches)

    def test_detect_bearer_token_lowercase(self):
        """Test detecting bearer token (lowercase)."""
        text = "auth: bearer xyz123456789012345678901234567890"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "bearer_token" for m in matches)

    def test_detect_bearer_token_with_underscores_hyphens(self):
        """Test detecting bearer token with underscores and hyphens."""
        text = "Bearer abc-def_123-456_789-012_345-678_901-234"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "bearer_token" for m in matches)


class TestDetectSecretsJWT:
    """
    Tests for `detect_secrets` focusing on JSON Web Token (JWT) patterns.

    This class verifies that the three-part structure of a JWT is correctly
    identified as a potential secret.
    """

    def test_detect_jwt_token(self):
        """Test detecting JWT token."""
        text = "token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "jwt_token" for m in matches)

    def test_detect_jwt_in_header(self):
        """Test detecting JWT in Authorization header."""
        text = "Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJodHRwczovL2V4YW1wbGUuYXV0aDAuY29tLyJ9.abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "jwt_token" for m in matches)


class TestDetectSecretsPrivateKeys:
    """
    Tests for `detect_secrets` focusing on private key block patterns.

    This class ensures that standard PEM-encoded private key formats
    (e.g., `-----BEGIN ... PRIVATE KEY-----`) are detected.
    """

    def test_detect_rsa_private_key(self):
        """Test detecting RSA private key."""
        text = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdefghijklmnop
-----END RSA PRIVATE KEY-----"""
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "private_key" for m in matches)

    def test_detect_private_key_generic(self):
        """Test detecting generic private key."""
        text = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC
-----END PRIVATE KEY-----"""
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "private_key" for m in matches)

    def test_detect_private_key_lowercase(self):
        """Test detecting private key with lowercase."""
        text = "-----begin private key-----\ndata\n-----end private key-----"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "private_key" for m in matches)


class TestDetectSecretsDatabaseURLs:
    """
    Tests for `detect_secrets` focusing on database connection strings.

    This class verifies that URLs containing credentials for common databases
    like PostgreSQL, MySQL, MongoDB, and Redis are identified.
    """

    def test_detect_postgres_url(self):
        """Test detecting PostgreSQL connection string."""
        text = "DATABASE_URL=postgres://user:password123@localhost:5432/mydb"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "database_url" for m in matches)

    def test_detect_mysql_url(self):
        """Test detecting MySQL connection string."""
        text = "DB_URL: mysql://admin:secretpass@db.example.com:3306/production"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "database_url" for m in matches)

    def test_detect_mongodb_url(self):
        """Test detecting MongoDB connection string."""
        text = "MONGO_URI=mongodb://dbuser:dbpass123@mongo.example.com:27017/myapp"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "database_url" for m in matches)

    def test_detect_redis_url(self):
        """Test detecting Redis connection string."""
        text = "REDIS_URL=redis://default:redispass@redis.local:6379/0"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "database_url" for m in matches)

    def test_detect_postgres_scheme(self):
        """Test detecting postgres:// scheme (not postgresql)."""
        text = "postgres://user:pass@host/db"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "database_url" for m in matches)


class TestDetectSecretsPasswords:
    """
    Tests for `detect_secrets` focusing on password assignments.

    This class ensures that common variable assignments for passwords
    (e.g., `password = ...`) are detected.
    """

    def test_detect_password_equals(self):
        """Test detecting password with equals sign."""
        text = "password=MySecretPass123!"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "password_assignment" for m in matches)

    def test_detect_passwd_colon(self):
        """Test detecting passwd with colon."""
        text = "passwd: SuperSecret456"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "password_assignment" for m in matches)

    def test_detect_pwd_quoted(self):
        """Test detecting pwd in quotes."""
        text = 'PWD="MyPassword789"'
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "password_assignment" for m in matches)

    def test_detect_password_case_insensitive(self):
        """Test detecting PASSWORD in uppercase."""
        text = "PASSWORD = AdminPass2023"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "password_assignment" for m in matches)


class TestDetectSecretsSecretAssignments:
    """
    Tests for `detect_secrets` focusing on generic secret assignments.

    This class verifies the detection of assignments using keywords like
    `secret`, `token`, or `credential`.
    """

    def test_detect_secret_assignment(self):
        """Test detecting secret assignment."""
        text = "secret=abc123def456ghi789jkl012mno"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "secret_assignment" for m in matches)

    def test_detect_token_assignment(self):
        """Test detecting token assignment."""
        text = "token: xyz987wvu654tsr321qpo098nml"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type in ("secret_assignment", "api_key") for m in matches)

    def test_detect_credential_assignment(self):
        """Test detecting credential assignment."""
        text = 'credential="abcdefghijklmnopqrstuvwxyz123456"'
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert any(m.secret_type == "secret_assignment" for m in matches)


class TestDetectSecretsMultipleAndEdgeCases:
    """
    Tests for `detect_secrets` covering multiple detections and edge cases.

    This class ensures the detector handles text with multiple secrets,
    no secrets, and respects parameters like `max_matches`.
    """

    def test_multiple_secrets_in_same_text(self):
        """Test detecting multiple different secrets in same text."""
        text = """
        API_KEY=abcd1234efgh5678ijkl9012mnop
        AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
        OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN
        password=MySecretPass123
        """
        matches = detect_secrets(text)

        assert len(matches) >= 4
        secret_types = {m.secret_type for m in matches}
        assert "api_key" in secret_types or "secret_assignment" in secret_types
        assert "aws_access_key" in secret_types
        assert "openai_key" in secret_types
        assert "password_assignment" in secret_types

    def test_text_with_no_secrets(self):
        """Test text containing no secrets."""
        text = "This is just normal text without any secrets. Hello world!"
        matches = detect_secrets(text)

        assert len(matches) == 0

    def test_empty_text(self):
        """Test empty text input."""
        text = ""
        matches = detect_secrets(text)

        assert len(matches) == 0

    def test_max_matches_parameter(self):
        """Test max_matches parameter limits results."""
        text = "\n".join([f"api_key_{i}=abcd1234efgh5678ijkl9012mnop{i:04d}" for i in range(20)])

        matches = detect_secrets(text, max_matches=5)
        assert len(matches) <= 5

    def test_context_chars_parameter(self):
        """Test context_chars parameter affects context length."""
        text = "x" * 100 + "API_KEY=abcd1234efgh5678ijkl9012mnop" + "y" * 100

        matches_small = detect_secrets(text, context_chars=10)
        matches_large = detect_secrets(text, context_chars=50)

        assert len(matches_small) >= 1
        assert len(matches_large) >= 1
        assert len(matches_large[0].context) > len(matches_small[0].context)

    def test_secret_position_tracking(self):
        """Test that position is correctly tracked."""
        text = "prefix text API_KEY=abcd1234efgh5678ijkl9012mnop suffix"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert matches[0].position >= 0
        assert matches[0].position < len(text)

    def test_context_includes_redaction(self):
        """Test that context includes redacted secret."""
        text = "API_KEY=abcd1234efgh5678ijkl9012mnop3456qrst"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert "..." in matches[0].context

    def test_short_secret_redaction(self):
        """Test redaction of short secrets."""
        text = "secret=abcd1234efgh5678ijkl9012"
        matches = detect_secrets(text)

        assert len(matches) >= 1
        assert "***" in matches[0].context or "..." in matches[0].context


class TestScanFileForSecrets:
    """
    Tests for the `scan_file_for_secrets` function.

    This class verifies that the function correctly scans files for secrets,
    handles file I/O, and respects function parameters.
    """

    def test_scan_file_with_secrets(self):
        """Test scanning a file containing secrets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "config.txt"
            test_file.write_text("API_KEY=abcd1234efgh5678ijkl9012mnop\nOTHER=value")

            matches = scan_file_for_secrets(str(test_file))

            assert len(matches) >= 1
            assert any(m.secret_type == "api_key" for m in matches)

    def test_scan_file_without_secrets(self):
        """Test scanning a file with no secrets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "normal.txt"
            test_file.write_text("This is normal content\nNo secrets here")

            matches = scan_file_for_secrets(str(test_file))

            assert len(matches) == 0

    def test_scan_nonexistent_file_raises_error(self):
        """Test scanning non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            scan_file_for_secrets("/nonexistent/path/file.txt")

    def test_scan_file_max_matches(self):
        """Test max_matches parameter in file scanning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "many_secrets.txt"
            content = "\n".join(
                [f"api_key_{i}=abcd1234efgh5678ijkl9012mnop{i:04d}" for i in range(20)]
            )
            test_file.write_text(content)

            matches = scan_file_for_secrets(str(test_file), max_matches=3)

            assert len(matches) <= 3

    def test_scan_file_with_encoding_errors(self):
        """Test scanning file with encoding errors is handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "binary.txt"
            test_file.write_bytes(b"API_KEY=test1234567890abcdef\xff\xfe")

            matches = scan_file_for_secrets(str(test_file))

            assert isinstance(matches, list)


class TestFormatSecretWarning:
    """
    Tests for the `format_secret_warning` function.

    This class ensures that the user-facing warning message is formatted
    correctly based on the secrets found, including grouping by type and
    providing helpful recommendations.
    """

    def test_format_warning_with_single_secret(self):
        """Test formatting warning with one secret."""
        matches = [SecretMatch(secret_type="api_key", position=10, context="key=abc...xyz")]

        warning = format_secret_warning(matches)

        assert "WARNING" in warning
        assert "1 potential secret" in warning
        assert "api_key" in warning

    def test_format_warning_with_multiple_secrets(self):
        """Test formatting warning with multiple secrets."""
        matches = [
            SecretMatch(secret_type="api_key", position=10, context="key1"),
            SecretMatch(secret_type="aws_access_key", position=50, context="key2"),
            SecretMatch(secret_type="openai_key", position=100, context="key3"),
        ]

        warning = format_secret_warning(matches)

        assert "WARNING" in warning
        assert "3 potential secrets" in warning
        assert "api_key" in warning
        assert "aws_access_key" in warning
        assert "openai_key" in warning

    def test_format_warning_with_no_secrets(self):
        """Test formatting warning with empty list."""
        matches = []

        warning = format_secret_warning(matches)

        assert warning == ""

    def test_format_warning_groups_by_type(self):
        """Test warning groups secrets by type."""
        matches = [
            SecretMatch(secret_type="api_key", position=10, context="key1"),
            SecretMatch(secret_type="api_key", position=20, context="key2"),
            SecretMatch(secret_type="aws_access_key", position=30, context="key3"),
        ]

        warning = format_secret_warning(matches)

        assert "api_key: 2" in warning
        assert "aws_access_key: 1" in warning

    def test_format_warning_includes_recommendations(self):
        """Test warning includes security recommendations."""
        matches = [SecretMatch(secret_type="api_key", position=10, context="key")]

        warning = format_secret_warning(matches)

        assert "environment variables" in warning
        assert "secrets manager" in warning
        assert "CORTEXGRAPH_DETECT_SECRETS" in warning


class TestShouldWarnAboutSecrets:
    """
    Tests for the `should_warn_about_secrets` function.

    This class verifies the logic that determines whether a warning should be
    issued, based on the type and number of secrets found. This helps avoid
    false positives for low-confidence matches.
    """

    def test_warn_for_high_confidence_aws_key(self):
        """Test warning for high-confidence AWS key."""
        matches = [SecretMatch(secret_type="aws_access_key", position=10, context="key")]

        assert should_warn_about_secrets(matches) is True

    def test_warn_for_high_confidence_openai_key(self):
        """Test warning for high-confidence OpenAI key."""
        matches = [SecretMatch(secret_type="openai_key", position=10, context="key")]

        assert should_warn_about_secrets(matches) is True

    def test_warn_for_high_confidence_github_token(self):
        """Test warning for high-confidence GitHub token."""
        matches = [SecretMatch(secret_type="github_token", position=10, context="key")]

        assert should_warn_about_secrets(matches) is True

    def test_warn_for_private_key(self):
        """Test warning for private key."""
        matches = [SecretMatch(secret_type="private_key", position=10, context="key")]

        assert should_warn_about_secrets(matches) is True

    def test_warn_for_database_url(self):
        """Test warning for database URL."""
        matches = [SecretMatch(secret_type="database_url", position=10, context="url")]

        assert should_warn_about_secrets(matches) is True

    def test_no_warn_for_single_low_confidence_match(self):
        """Test no warning for single low-confidence match."""
        matches = [SecretMatch(secret_type="api_key", position=10, context="key")]

        assert should_warn_about_secrets(matches) is False

    def test_warn_for_multiple_low_confidence_matches(self):
        """Test warning for multiple low-confidence matches."""
        matches = [
            SecretMatch(secret_type="api_key", position=10, context="key1"),
            SecretMatch(secret_type="password_assignment", position=20, context="key2"),
        ]

        assert should_warn_about_secrets(matches) is True

    def test_no_warn_for_empty_matches(self):
        """Test no warning for empty matches."""
        matches = []

        assert should_warn_about_secrets(matches) is False

    def test_custom_min_confidence_types(self):
        """Test custom min_confidence_types parameter."""
        matches = [SecretMatch(secret_type="api_key", position=10, context="key")]

        custom_types = {"api_key"}
        assert should_warn_about_secrets(matches, min_confidence_types=custom_types) is True

    def test_custom_min_confidence_excludes_others(self):
        """Test custom min_confidence_types excludes non-listed types."""
        matches = [SecretMatch(secret_type="aws_access_key", position=10, context="key")]

        custom_types = {"api_key"}
        assert should_warn_about_secrets(matches, min_confidence_types=custom_types) is False


class TestRedactSecrets:
    """
    Tests for the `redact_secrets` function.

    This class ensures that found secrets are correctly replaced with a
    redaction placeholder, and that the rest of the text remains intact.
    """

    def test_redact_api_key(self):
        """Test redacting API key."""
        text = "API_KEY=abcd1234efgh5678ijkl9012mnop"
        redacted = redact_secrets(text)

        assert "abcd1234efgh5678ijkl9012mnop" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_aws_access_key(self):
        """Test redacting AWS access key."""
        text = "AWS key: AKIAIOSFODNN7EXAMPLE"
        redacted = redact_secrets(text)

        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_openai_key(self):
        """Test redacting OpenAI key."""
        text = "OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
        redacted = redact_secrets(text)

        assert "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_github_token(self):
        """Test redacting GitHub token."""
        text = "token: ghp_1234567890abcdefghijklmnopqrstuv"
        redacted = redact_secrets(text)

        assert "ghp_1234567890abcdefghijklmnopqrstuv" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_jwt_token(self):
        """Test redacting JWT token."""
        text = "JWT: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        redacted = redact_secrets(text)

        assert "eyJhbGciOiJIUzI1NiJ9" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_database_url(self):
        """Test redacting database URL."""
        text = "DB: postgres://user:pass@localhost/db"
        redacted = redact_secrets(text)

        assert "postgres://user:pass@localhost/db" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_private_key(self):
        """Test redacting private key."""
        text = "Key: -----BEGIN PRIVATE KEY-----\ndata"
        redacted = redact_secrets(text)

        assert "-----BEGIN PRIVATE KEY-----" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_multiple_secrets(self):
        """Test redacting multiple secrets."""
        text = "API_KEY=abc123def456ghi789jkl012 and PASSWORD=MySecret123"
        redacted = redact_secrets(text)

        assert "abc123def456ghi789jkl012" not in redacted
        assert "MySecret123" not in redacted
        assert redacted.count("***REDACTED***") >= 2

    def test_redact_with_custom_replacement(self):
        """Test redacting with custom replacement string."""
        text = "API_KEY=abcd1234efgh5678ijkl9012mnop"
        redacted = redact_secrets(text, replacement="[HIDDEN]")

        assert "abcd1234efgh5678ijkl9012mnop" not in redacted
        assert "[HIDDEN]" in redacted
        assert "***REDACTED***" not in redacted

    def test_redact_text_without_secrets(self):
        """Test redacting text with no secrets."""
        text = "This is normal text without secrets"
        redacted = redact_secrets(text)

        assert redacted == text

    def test_redact_preserves_text_structure(self):
        """Test redacting preserves overall text structure."""
        text = "Before API_KEY=abc123def456ghi789jkl012 after"
        redacted = redact_secrets(text)

        assert redacted.startswith("Before")
        assert redacted.endswith("after")
        assert "***REDACTED***" in redacted

    def test_redact_empty_text(self):
        """Test redacting empty text."""
        text = ""
        redacted = redact_secrets(text)

        assert redacted == ""


class TestCLIMain:
    """
    Tests for the `main()` command-line interface function.

    This class mocks `sys.argv` and `sys.stdin` to simulate command-line
    usage of the secret scanning script, verifying exit codes and output
    to stdout/stderr.
    """

    def test_cli_scan_file_with_secrets(self, monkeypatch, capsys):
        """Test CLI scanning a file with secrets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "config.txt"
            test_file.write_text("API_KEY=abcd1234efgh5678ijkl9012mnop")

            monkeypatch.setattr(sys, "argv", ["secrets", str(test_file)])

            exit_code = main()

            assert exit_code == 1
            captured = capsys.readouterr()
            assert "WARNING" in captured.err
            assert "api_key" in captured.err

    def test_cli_scan_file_without_secrets(self, monkeypatch, capsys):
        """Test CLI scanning a file without secrets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "normal.txt"
            test_file.write_text("This is normal content")

            monkeypatch.setattr(sys, "argv", ["secrets", str(test_file)])

            exit_code = main()

            assert exit_code == 0
            captured = capsys.readouterr()
            assert "No secrets detected" in captured.err

    def test_cli_scan_stdin_with_secrets(self, monkeypatch, capsys):
        """Test CLI scanning stdin with secrets."""
        stdin_data = "OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_data))
        monkeypatch.setattr(sys, "argv", ["secrets"])

        exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "WARNING" in captured.err

    def test_cli_scan_stdin_without_secrets(self, monkeypatch, capsys):
        """Test CLI scanning stdin without secrets."""
        stdin_data = "Normal text without secrets"
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_data))
        monkeypatch.setattr(sys, "argv", ["secrets"])

        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No secrets detected" in captured.err

    def test_cli_redact_mode_file(self, monkeypatch, capsys):
        """Test CLI redact mode with file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "config.txt"
            test_file.write_text("API_KEY=abcd1234efgh5678ijkl9012mnop and more text")

            monkeypatch.setattr(sys, "argv", ["secrets", str(test_file), "--redact"])

            exit_code = main()

            assert exit_code == 0
            captured = capsys.readouterr()
            assert "***REDACTED***" in captured.out
            assert "abcd1234efgh5678ijkl9012mnop" not in captured.out

    def test_cli_redact_mode_stdin(self, monkeypatch, capsys):
        """Test CLI redact mode with stdin."""
        stdin_data = "password=MySecret123 and other data"
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_data))
        monkeypatch.setattr(sys, "argv", ["secrets", "--redact"])

        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "***REDACTED***" in captured.out
        assert "MySecret123" not in captured.out

    def test_cli_quiet_mode_with_secrets(self, monkeypatch, capsys):
        """Test CLI quiet mode when secrets are found."""
        stdin_data = "API_KEY=abcd1234efgh5678ijkl9012mnop"
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_data))
        monkeypatch.setattr(sys, "argv", ["secrets", "--quiet"])

        exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_cli_quiet_mode_without_secrets(self, monkeypatch, capsys):
        """Test CLI quiet mode when no secrets found."""
        stdin_data = "Normal text"
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_data))
        monkeypatch.setattr(sys, "argv", ["secrets", "--quiet"])

        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_cli_max_matches_parameter(self, monkeypatch, capsys):
        """Test CLI with --max-matches parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "many.txt"
            content = "\n".join([f"API_KEY=abcd1234efgh5678ijkl9012mnop{i:04d}" for i in range(10)])
            test_file.write_text(content)

            monkeypatch.setattr(sys, "argv", ["secrets", str(test_file), "--max-matches", "3"])

            exit_code = main()

            assert exit_code == 1

    def test_cli_file_not_found_error(self, monkeypatch, capsys):
        """Test CLI with non-existent file."""
        monkeypatch.setattr(sys, "argv", ["secrets", "/nonexistent/file.txt"])

        exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_cli_combined_redact_and_quiet(self, monkeypatch, capsys):
        """Test CLI with both --redact and --quiet flags."""
        stdin_data = "API_KEY=abcd1234efgh5678ijkl9012mnop"
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_data))
        monkeypatch.setattr(sys, "argv", ["secrets", "--redact", "--quiet"])

        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "***REDACTED***" in captured.out
