"""Configuration manager with 3-layer precedence."""
import copy
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional, Dict

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


SECURITY_FLOOR = {
    "approval_mode": "prompt",
    "allowed_envelopes": frozenset(["RO", "RW", "RESEARCH"]),
}


DEFAULT_CONFIG_PATH = Path.home() / ".claude" / "skills" / "cortex-code" / "config.yaml"
DEFAULT_ORG_POLICY_PATH = Path.home() / ".snowflake" / "cortex" / "claude-skill-policy.yaml"


class ConfigManager:
    """Manages security configuration with precedence: org policy > user config > defaults."""

    DEFAULT_CONFIG = {
        "security": {
            "approval_mode": "prompt",
            "tool_prediction_confidence_threshold": 0.7,
            "allow_tool_expansion": True,
            "audit_log_path": "~/.claude/skills/cortex-code/audit.log",
            "audit_log_rotation": "10MB",
            "audit_log_retention": 30,
            "sanitize_conversation_history": True,
            "sanitize_session_files": True,
            "max_history_items": 3,
            "cache_dir": "~/.cache/cortex-skill",
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
        """Initialize config manager.

        Auto-discovers config files from documented default paths when not
        explicitly provided. Env vars CORTEX_SKILL_CONFIG and
        CORTEX_SKILL_ORG_POLICY override the defaults.
        """
        env_config = os.environ.get("CORTEX_SKILL_CONFIG")
        env_policy = os.environ.get("CORTEX_SKILL_ORG_POLICY")
        config_required = config_path is not None or bool(env_config)
        policy_required = org_policy_path is not None or bool(env_policy)
        if config_path is None:
            config_path = Path(env_config) if env_config else DEFAULT_CONFIG_PATH
        if org_policy_path is None:
            org_policy_path = Path(env_policy) if env_policy else DEFAULT_ORG_POLICY_PATH
        self._config = self._load_config(
            Path(config_path).expanduser(), Path(org_policy_path).expanduser(),
            config_required, policy_required,
        )

    def _validate_config(self, config: Dict) -> None:
        """Validate configuration values."""
        if not isinstance(config, dict):
            raise ConfigValidationError("Configuration must be a mapping.")
        security = config.get("security", {})
        if not isinstance(security, dict):
            raise ConfigValidationError("security must be a mapping.")

        # Validate each source before merging or applying the security floor.
        for key, default in self.DEFAULT_CONFIG["security"].items():
            if key not in security:
                continue
            value = security[key]
            if isinstance(default, bool) and not isinstance(value, bool):
                raise ConfigValidationError(f"security.{key} must be a boolean.")
            if isinstance(default, str) and (not isinstance(value, str) or not value.strip()):
                raise ConfigValidationError(f"security.{key} must be a non-empty string.")
            if isinstance(default, list) and (
                not isinstance(value, list) or any(not isinstance(item, str) for item in value)
            ):
                raise ConfigValidationError(f"security.{key} must be a list of strings.")
        if "override_user_config" in security and not isinstance(security["override_user_config"], bool):
            raise ConfigValidationError("security.override_user_config must be a boolean.")
        for key in ("audit_log_retention", "max_history_items", "cache_ttl"):
            if key in security and (type(security[key]) is not int or security[key] < 0):
                raise ConfigValidationError(f"security.{key} must be a non-negative integer.")
        rotation = security.get("audit_log_rotation")
        if rotation is not None and not re.fullmatch(
            r"(?:[0-9]+(?:\.[0-9]+)?(?:KB|MB|GB)|[0-9]+)", rotation.upper()
        ):
            raise ConfigValidationError("security.audit_log_rotation must be a size, e.g. 10MB.")
        permissions = security.get("cache_permissions")
        if permissions is not None and not re.fullmatch(r"0?[0-7]{3}", permissions):
            raise ConfigValidationError("security.cache_permissions must be an octal mode, e.g. 0600.")

        # Validate approval_mode
        approval_mode = security.get("approval_mode")
        if "approval_mode" in security and approval_mode not in ["prompt", "auto", "envelope_only"]:
            raise ConfigValidationError(
                f"Invalid approval_mode: {approval_mode}. "
                f"Must be one of: prompt, auto, envelope_only"
            )

        # Validate allowed_envelopes
        valid_envelopes = {"RO", "RW", "RESEARCH", "DEPLOY"}
        allowed_envelopes = security.get("allowed_envelopes", [])
        for envelope in allowed_envelopes:
            if envelope not in valid_envelopes:
                raise ConfigValidationError(
                    f"Invalid envelope: {envelope}. "
                    f"Must be one of: {', '.join(sorted(valid_envelopes))}"
                )

        # Validate numeric values
        confidence = security.get("tool_prediction_confidence_threshold")
        if "tool_prediction_confidence_threshold" in security:
            if type(confidence) not in (int, float):
                raise ConfigValidationError(
                    f"tool_prediction_confidence_threshold must be a number, got {type(confidence).__name__}"
                )
            if not (0 <= confidence <= 1):
                raise ConfigValidationError(
                    f"tool_prediction_confidence_threshold must be between 0 and 1, got {confidence}"
                )

    def _enforce_security_floor(self, config: Dict, has_org_policy: bool) -> Dict:
        """User config cannot relax security below floor without org policy.

        Without an org policy present, user config is capped at the security floor:
        - approval_mode cannot be relaxed from 'prompt' to 'auto' or 'envelope_only'
        - allowed_envelopes cannot include DEPLOY
        """
        if has_org_policy:
            return config

        security = config.get("security", {})

        if security.get("approval_mode") in ("auto", "envelope_only"):
            security["approval_mode"] = SECURITY_FLOOR["approval_mode"]

        user_envelopes = set(security.get("allowed_envelopes", []))
        security["allowed_envelopes"] = sorted(
            user_envelopes & SECURITY_FLOOR["allowed_envelopes"]
        )

        config["security"] = security
        return config

    def _expand_paths(self, config: Dict) -> Dict:
        """Expand ~ and environment variables in file paths."""
        security = config.get("security", {})

        if "audit_log_path" in security:
            security["audit_log_path"] = os.path.expanduser(security["audit_log_path"])

        if "cache_dir" in security:
            security["cache_dir"] = os.path.expanduser(security["cache_dir"])

        config["security"] = security
        return config

    def _read_config(self, path: Path, required: bool) -> Optional[Dict]:
        """Only an absent optional default file may fall back to defaults."""
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            if not required and not path.is_symlink():
                return None
            raise ConfigValidationError(f"Configuration file not found: {path}") from error
        except (OSError, UnicodeError) as error:
            raise ConfigValidationError(f"Cannot read configuration file: {path}") from error

        if not HAS_YAML:
            raise ConfigValidationError(
                f"Cannot load {path}: PyYAML is not installed for {sys.executable}. "
                f'Install it in this Python environment with "{sys.executable}" -m pip install PyYAML '
                "(use a virtual environment if this Python is externally managed). "
                "Execution stopped; configuration was not ignored."
            )
        try:
            document = yaml.safe_load(content)
        except yaml.YAMLError as error:
            # Parser messages can include policy contents; report location only.
            mark = getattr(error, "problem_mark", None)
            location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
            raise ConfigValidationError(f"Invalid YAML in {path}{location}.") from error
        try:
            self._validate_config(document)
        except ConfigValidationError as error:
            raise ConfigValidationError(f"Invalid configuration in {path}: {error}") from error
        return document

    def _load_config(
        self,
        config_path: Path,
        org_policy_path: Path,
        config_required: bool = False,
        policy_required: bool = False,
    ) -> Dict:
        """Load configuration with 3-layer precedence."""
        config = copy.deepcopy(self.DEFAULT_CONFIG)
        has_org_policy = False

        user_config = self._read_config(config_path, config_required)
        if user_config is not None:
            config = self._merge_config(config, user_config)

        org_policy = self._read_config(org_policy_path, policy_required)
        if org_policy is not None:
            has_org_policy = True
            if org_policy.get("security", {}).get("override_user_config"):
                config = copy.deepcopy(self.DEFAULT_CONFIG)
            config = self._merge_config(config, org_policy)

        # Enforce security floor BEFORE validation
        config = self._enforce_security_floor(config, has_org_policy)

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
