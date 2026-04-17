"""Configuration manager with 3-layer precedence."""
import copy
import os
import sys
from pathlib import Path
from typing import Any, Optional, Dict
import yaml


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigManager:
    """Manages security configuration with precedence: org policy > user config > defaults."""

    DEFAULT_CONFIG = {
        "security": {
            "approval_mode": "prompt",
            "tool_prediction_confidence_threshold": 0.7,
            "allow_tool_expansion": True,
            "audit_log_path": "~/.cache/cortexcode-tool/audit.log",
            "audit_log_rotation": "10MB",
            "audit_log_retention": 30,
            "sanitize_conversation_history": True,
            "sanitize_session_files": True,
            "max_history_items": 3,
            "cache_dir": "~/.cache/cortexcode-tool",
            "cache_permissions": "0600",
            "allowed_envelopes": ["RO", "RW", "RESEARCH"],
            "deploy_envelope_confirmation": True,
            "credential_file_allowlist": [
                "~/.ssh/*",
                "~/.snowflake/*",
                "**/.env",
                "**/.env.*",
                "**/credentials.json",
                "**/*_key.p8",
                "**/*_key.pem",
                "~/.aws/credentials",
                "~/.kube/config"
            ]
        }
    }

    def __init__(
        self,
        config_path: Optional[Path] = None,
        org_policy_path: Optional[Path] = None
    ):
        """Initialize config manager."""
        self._config = self._load_config(config_path, org_policy_path)

    def _validate_config(self, config: Dict) -> None:
        """Validate configuration values."""
        security = config.get("security", {})

        # Validate approval_mode
        approval_mode = security.get("approval_mode")
        if approval_mode not in ["prompt", "auto", "envelope_only"]:
            raise ConfigValidationError(
                f"Invalid approval_mode: {approval_mode}. "
                f"Must be one of: prompt, auto, envelope_only"
            )

        # Validate allowed_envelopes
        valid_envelopes = {"RO", "RW", "RESEARCH", "DEPLOY", "NONE"}
        allowed_envelopes = security.get("allowed_envelopes", [])
        for envelope in allowed_envelopes:
            if envelope not in valid_envelopes:
                raise ConfigValidationError(
                    f"Invalid envelope: {envelope}. "
                    f"Must be one of: {', '.join(valid_envelopes)}"
                )

        # Validate numeric values
        confidence = security.get("tool_prediction_confidence_threshold")
        if confidence is not None:
            if not isinstance(confidence, (int, float)):
                raise ConfigValidationError(
                    f"tool_prediction_confidence_threshold must be a number, got {type(confidence).__name__}"
                )
            if not (0 <= confidence <= 1):
                raise ConfigValidationError(
                    f"tool_prediction_confidence_threshold must be between 0 and 1, got {confidence}"
                )

        retention = security.get("audit_log_retention")
        if retention is not None:
            if not isinstance(retention, int):
                raise ConfigValidationError(
                    f"audit_log_retention must be an integer, got {type(retention).__name__}"
                )
            if retention < 0:
                raise ConfigValidationError(
                    f"audit_log_retention must be >= 0, got {retention}"
                )

        # Validate audit_log_rotation format
        audit_rotation = security.get("audit_log_rotation")
        if audit_rotation:
            import re
            if not re.match(r'^\d+(MB|GB|KB)$', audit_rotation):
                raise ConfigValidationError(
                    f"Invalid audit_log_rotation format: {audit_rotation}. "
                    "Expected format: <number><unit> (e.g., '10MB', '5GB')"
                )

        # Validate cache_permissions format (octal string)
        cache_perms = security.get("cache_permissions")
        if cache_perms:
            if not isinstance(cache_perms, str) or not re.match(r'^0[0-7]{3}$', cache_perms):
                raise ConfigValidationError(
                    f"Invalid cache_permissions format: {cache_perms}. "
                    "Expected octal string like '0600', '0700', '0755'"
                )

    def _expand_paths(self, config: Dict) -> Dict:
        """Expand ~ and environment variables in file paths."""
        security = config.get("security", {})

        # Expand audit_log_path
        if "audit_log_path" in security:
            security["audit_log_path"] = os.path.expanduser(security["audit_log_path"])

        # Expand cache_dir
        if "cache_dir" in security:
            security["cache_dir"] = os.path.expanduser(security["cache_dir"])

        config["security"] = security
        return config

    def _load_config(
        self,
        config_path: Optional[Path],
        org_policy_path: Optional[Path]
    ) -> Dict:
        """Load configuration with 3-layer precedence."""
        # Start with defaults
        config = copy.deepcopy(self.DEFAULT_CONFIG)

        # Load user config if exists
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    try:
                        user_config = yaml.safe_load(f) or {}
                        config = self._merge_config(config, user_config)
                    except yaml.YAMLError as e:
                        print(f"Warning: Failed to parse user config {config_path}: {e}", file=sys.stderr)
            except OSError as e:
                print(f"Warning: Failed to read user config {config_path}: {e}", file=sys.stderr)

        # Load org policy if exists
        if org_policy_path and org_policy_path.exists():
            try:
                with open(org_policy_path, 'r') as f:
                    try:
                        org_policy = yaml.safe_load(f) or {}

                        # If override flag set, org policy wins completely
                        if org_policy.get("security", {}).get("override_user_config"):
                            # Merge org policy over defaults (skip user config)
                            config = self._merge_config(copy.deepcopy(self.DEFAULT_CONFIG), org_policy)
                        else:
                            # Normal merge: org policy > user config > defaults
                            config = self._merge_config(config, org_policy)
                    except yaml.YAMLError as e:
                        print(f"Warning: Failed to parse org policy {org_policy_path}: {e}", file=sys.stderr)
            except OSError as e:
                print(f"Warning: Failed to read org policy {org_policy_path}: {e}", file=sys.stderr)

        # Validate configuration
        self._validate_config(config)

        # Expand file paths
        config = self._expand_paths(config)

        return config

    def _merge_config(self, base: Dict, override: Dict) -> Dict:
        """Deep merge override into base."""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key."""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value
