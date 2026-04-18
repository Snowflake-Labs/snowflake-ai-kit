#!/usr/bin/env python3
"""
Security wrapper orchestrator for cortex-code skill.

Coordinates all security components:
- ConfigManager: Load and validate configuration
- AuditLogger: Log all executions
- CacheManager: Secure caching
- PromptSanitizer: Remove PII and detect injection
- ApprovalHandler: Tool prediction and user approval

This is the main entry point for secure Cortex execution.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from security.config_manager import ConfigManager
from security.audit_logger import AuditLogger
from security.cache_manager import CacheManager
from security.prompt_sanitizer import PromptSanitizer
from security.approval_handler import ApprovalHandler

# Import routing functions
sys.path.insert(0, str(Path(__file__).parent))
from route_request import analyze_with_llm_logic, load_cortex_capabilities


def execute_with_security(
    prompt: str,
    config_path: Optional[str] = None,
    org_policy_path: Optional[str] = None,
    dry_run: bool = False,
    envelope: Optional[Dict[str, Any]] = None,
    mock_user_approval: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute prompt with full security orchestration.

    This function:
    1. Loads configuration (with org policy override)
    2. Initializes all security components
    3. Sanitizes prompt if enabled
    4. Determines approval mode
    5. In dry-run mode: returns initialization status
    6. In live mode: Full execution with approval flow

    Args:
        prompt: User prompt to execute
        config_path: Path to user config file (optional)
        org_policy_path: Path to organization policy file (optional)
        dry_run: If True, only initialize and validate (don't execute)
        envelope: Cortex envelope dict (optional)
        mock_user_approval: For testing - "approve" or "deny" (optional)

    Returns:
        Dict with execution results or initialization status
    """
    # Step 1: Load configuration
    config_path_obj = Path(config_path) if config_path else None
    org_policy_path_obj = Path(org_policy_path) if org_policy_path else None

    config_manager = ConfigManager(
        config_path=config_path_obj,
        org_policy_path=org_policy_path_obj
    )

    # Extract config values
    approval_mode = config_manager.get("security.approval_mode")
    audit_log_path = Path(config_manager.get("security.audit_log_path"))
    audit_log_rotation = config_manager.get("security.audit_log_rotation")
    audit_log_retention = config_manager.get("security.audit_log_retention")
    cache_dir = Path(config_manager.get("security.cache_dir"))
    sanitize_enabled = config_manager.get("security.sanitize_conversation_history")
    confidence_threshold = config_manager.get("security.tool_prediction_confidence_threshold")
    allowed_envelopes = config_manager.get("security.allowed_envelopes")

    # Step 2: Initialize security components
    audit_logger = AuditLogger(
        log_path=audit_log_path,
        rotation_size=audit_log_rotation,
        retention_days=audit_log_retention
    )

    cache_manager = CacheManager(cache_dir=cache_dir)

    prompt_sanitizer = PromptSanitizer()

    approval_handler = ApprovalHandler(confidence_threshold=confidence_threshold)

    # Step 3: Sanitize prompt if enabled
    sanitized_prompt = prompt
    if sanitize_enabled:
        sanitized_prompt = prompt_sanitizer.sanitize(prompt)

    # Step 4: Check credential file allowlist (on original prompt)
    credential_allowlist = config_manager.get("security.credential_file_allowlist")
    for pattern in credential_allowlist:
        # Simple pattern matching - strip wildcards and check for contains
        pattern_check = pattern.replace('~/', '').replace('**/', '').replace('*', '')
        if pattern_check and pattern_check in prompt.lower():
            return {
                "status": "blocked",
                "reason": "Prompt contains credential file path from allowlist",
                "pattern_matched": pattern,
                "message": "Cannot route prompts containing credential file paths for security"
            }

    # Step 5: Determine routing (cortex vs claude) on sanitized prompt
    capabilities = load_cortex_capabilities()
    route_decision, route_confidence = analyze_with_llm_logic(sanitized_prompt, capabilities)

    # Step 6: Determine approval mode
    # In prompt mode, user must approve tools
    # In auto mode, tools are auto-approved
    # In deny mode, execution is blocked

    # Step 7: Dry-run mode - return initialization status
    if dry_run:
        return {
            "status": "initialized",
            "dry_run": True,
            "prompt": prompt,
            "sanitized_prompt": sanitized_prompt,
            "routing": {
                "decision": route_decision,
                "confidence": route_confidence
            },
            "config": {
                "approval_mode": approval_mode,
                "audit_log_path": str(audit_log_path),
                "cache_dir": str(cache_dir),
                "sanitize_enabled": sanitize_enabled,
                "confidence_threshold": confidence_threshold,
                "allowed_envelopes": allowed_envelopes
            },
            "audit_logger": str(type(audit_logger).__name__),
            "cache_manager": str(type(cache_manager).__name__),
            "prompt_sanitizer": str(type(prompt_sanitizer).__name__),
            "approval_handler": str(type(approval_handler).__name__)
        }

    # Step 8: Full execution flow
    # Route to Claude Code for non-Snowflake requests
    if route_decision == "claude":
        return {
            "status": "routed_to_claude",
            "message": "Request routed to Claude Code for local handling",
            "routing": {"decision": route_decision, "confidence": route_confidence}
        }

    # Step 9: Tool prediction for Cortex execution
    prediction = approval_handler.predict_tools(sanitized_prompt, envelope)
    predicted_tools = prediction["tools"]
    tool_confidence = prediction["confidence"]

    # Step 10: Handle approval mode
    allowed_tools = []
    approval_result = None

    if approval_mode == "prompt":
        # Prompt mode: require user approval
        if mock_user_approval:
            # Testing mode - mock approval
            if mock_user_approval == "approve":
                allowed_tools = predicted_tools
            elif mock_user_approval == "deny":
                return {
                    "status": "denied",
                    "message": "User denied execution",
                    "predicted_tools": predicted_tools
                }
        else:
            # Real mode - format approval prompt
            approval_prompt = approval_handler.format_approval_prompt(
                predicted_tools,
                tool_confidence,
                envelope,
                prediction.get("reasoning", "")
            )

            # Return prompt for user - actual approval happens externally
            return {
                "status": "awaiting_approval",
                "approval_prompt": approval_prompt,
                "predicted_tools": predicted_tools,
                "confidence": tool_confidence,
                "envelope": envelope
            }

    elif approval_mode == "auto":
        # Auto mode: auto-approve all tools
        allowed_tools = predicted_tools

    elif approval_mode == "envelope_only":
        # Envelope only mode: no tool prediction
        allowed_tools = None  # None means rely on envelope only

    # Step 11: Execute with Cortex (simplified for now - actual execution via execute_cortex.py would go here)
    # For now, return success with mock execution
    execution_result = {
        "status": "success",
        "message": "Execution simulated (full Cortex integration in next phase)",
        "tools_used": allowed_tools or ["envelope-controlled"],
        "duration_ms": 100
    }

    # Step 12: Audit logging
    audit_id = audit_logger.log_execution(
        event_type="cortex_execution",
        user=os.environ.get("USER", "unknown"),
        routing={"decision": route_decision, "confidence": route_confidence},
        execution={
            "envelope": envelope,
            "approval_mode": approval_mode,
            "auto_approved": approval_mode in ["auto", "envelope_only"],
            "predicted_tools": predicted_tools,
            "allowed_tools": allowed_tools
        },
        result=execution_result,
        security={
            "sanitized": sanitize_enabled,
            "pii_removed": sanitize_enabled and prompt != sanitized_prompt
        }
    )

    # Step 13: Cache result (optional - for future optimization)
    # For now, skip caching

    return {
        "status": "executed",
        "audit_id": audit_id,
        "routing": {"decision": route_decision, "confidence": route_confidence},
        "approval_mode": approval_mode,
        "predicted_tools": predicted_tools,
        "allowed_tools": allowed_tools,
        "result": execution_result,
        "security": {
            "sanitized": sanitize_enabled,
            "pii_removed": sanitize_enabled and prompt != sanitized_prompt
        }
    }


def main():
    """CLI entry point for security wrapper."""
    parser = argparse.ArgumentParser(
        description="Security wrapper for cortex-code skill"
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="User prompt to execute"
    )
    parser.add_argument(
        "--config",
        help="Path to user config file"
    )
    parser.add_argument(
        "--org-policy",
        help="Path to organization policy file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run mode: initialize and validate only"
    )
    parser.add_argument(
        "--envelope",
        help="Cortex envelope JSON string"
    )

    args = parser.parse_args()

    # Parse envelope if provided
    envelope = None
    if args.envelope:
        try:
            envelope = json.loads(args.envelope)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "status": "error",
                "message": f"Invalid envelope JSON: {e}"
            }))
            sys.exit(1)

    # Execute with security
    try:
        result = execute_with_security(
            prompt=args.prompt,
            config_path=args.config,
            org_policy_path=args.org_policy,
            dry_run=args.dry_run,
            envelope=envelope
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": str(e)
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
