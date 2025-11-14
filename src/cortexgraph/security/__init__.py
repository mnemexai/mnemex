"""Security utilities for CortexGraph."""

from .paths import (
    ensure_within_directory,
    sanitize_filename,
    validate_folder_path,
    validate_vault_path,
)
from .permissions import (
    check_permissions,
    ensure_secure_storage,
    secure_config_file,
    secure_directory,
    secure_file,
)
from .secrets import (
    SecretMatch,
    detect_secrets,
    format_secret_warning,
    redact_secrets,
    scan_file_for_secrets,
    should_warn_about_secrets,
)
from .validators import (
    MAX_CONTENT_LENGTH,
    MAX_ENTITIES_COUNT,
    MAX_TAG_LENGTH,
    MAX_TAGS_COUNT,
    validate_entity,
    validate_list_length,
    validate_positive_int,
    validate_relation_type,
    validate_score,
    validate_string_length,
    validate_tag,
    validate_target,
    validate_uuid,
)

__all__ = [
    # Constants
    "MAX_CONTENT_LENGTH",
    "MAX_TAG_LENGTH",
    "MAX_TAGS_COUNT",
    "MAX_ENTITIES_COUNT",
    # Input Validators
    "validate_uuid",
    "validate_string_length",
    "validate_score",
    "validate_positive_int",
    "validate_list_length",
    "validate_tag",
    "validate_entity",
    "validate_relation_type",
    "validate_target",
    # Path Validators
    "validate_folder_path",
    "validate_vault_path",
    "sanitize_filename",
    "ensure_within_directory",
    # Permission Security
    "secure_file",
    "secure_directory",
    "secure_config_file",
    "ensure_secure_storage",
    "check_permissions",
    # Secrets Detection
    "SecretMatch",
    "detect_secrets",
    "scan_file_for_secrets",
    "format_secret_warning",
    "should_warn_about_secrets",
    "redact_secrets",
]
