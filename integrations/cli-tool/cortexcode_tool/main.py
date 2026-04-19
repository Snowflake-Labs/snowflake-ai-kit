#!/usr/bin/env python3
"""
Cortexcode Tool - Multi-IDE CLI for Cortex Code integration.

Main entry point for the CLI tool.
"""
import sys
import argparse
import logging
from typing import List, Optional
from pathlib import Path

from cortexcode_tool import __version__
from cortexcode_tool.security.config_manager import ConfigManager
from cortexcode_tool.security.cache_manager import CacheManager
from cortexcode_tool.security.audit_logger import AuditLogger
from cortexcode_tool.core.discover_cortex import discover_cortex_skills

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Cortexcode Tool - Multi-IDE CLI for Cortex Code integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cortexcode-tool "Show me top 10 customers by revenue"
  cortexcode-tool --envelope RO "List databases"
  cortexcode-tool --discover-capabilities
  cortexcode-tool --generate-ide-config vscode

Note: Cursor users should use the Claude Code skill (/cortex-code) instead.
        """
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Snowflake query or question"
    )

    parser.add_argument(
        "--envelope",
        choices=["RO", "RW", "RESEARCH", "DEPLOY", "NONE"],
        help="Security envelope (default from config)"
    )

    parser.add_argument(
        "--config",
        help="Path to config file (default: ~/.config/cortexcode-tool/config.yaml)"
    )

    parser.add_argument(
        "--discover-capabilities",
        action="store_true",
        help="Force rediscovery of Cortex capabilities"
    )

    parser.add_argument(
        "--generate-ide-config",
        nargs="?",
        const="all",
        choices=["cursor", "vscode", "all"],
        help="Generate IDE integration files"
    )

    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration file"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    return parser.parse_args(argv)


def execute_query(
    query: str,
    config: ConfigManager,
    cache: CacheManager,
    logger_instance: Optional[AuditLogger]
) -> int:
    """Execute a Snowflake query via Cortex Code.

    Returns:
        Exit code (0 for success)
    """
    from .core.discover_cortex import discover_cortex_skills
    from .core.route_request import analyze_with_llm_logic, load_cortex_capabilities, check_credential_allowlist
    from .core.execute_cortex import execute_cortex_streaming
    from .security.approval_handler import ApprovalHandler

    # Check credential allowlist first
    credential_check = check_credential_allowlist(query)
    if credential_check.get("blocked"):
        print(f"⛔ BLOCKED: Credential file detected")
        print(f"   Pattern: {credential_check['pattern_matched']}")
        print(f"   Reason: {credential_check['reason']}")
        return 1

    # Get capabilities
    capabilities = cache.read("cortex-capabilities")
    if not capabilities:
        print("Discovering Cortex capabilities...", file=sys.stderr)
        capabilities = discover_cortex_skills()
        cache.write("cortex-capabilities", capabilities, ttl=86400)

    # Route the request
    route, confidence = analyze_with_llm_logic(query, capabilities)

    if route != "cortex":
        print(f"This query should be handled by your coding agent, not Cortex.", file=sys.stderr)
        print(f"Route: {route}, Confidence: {confidence:.2%}", file=sys.stderr)
        return 1

    print(f"✓ Routing to Cortex Code (confidence: {confidence:.2%})", file=sys.stderr)

    # Write an immediate stdout marker so the result file is never empty while running.
    # Codex polls the file during background execution — without this it sees an empty
    # file for ~45s and gives up before Cortex returns the actual answer.
    print("Querying Snowflake via Cortex Code...", flush=True)

    # Handle approval if needed
    approval_mode = config.get("security.approval_mode", "prompt")

    if approval_mode == "prompt":
        # Show approval prompt
        handler = ApprovalHandler()
        predicted_tools = handler.predict_tools(query)
        envelope = config.get("cortex.default_envelope", "RW")

        result = handler.request_approval(
            tools=predicted_tools,
            envelope=envelope,
            confidence=confidence
        )

        if not result.approved:
            print("Execution cancelled by user")
            return 1

    # Execute via Cortex
    connection = config.get("cortex.connection_name", "default")
    envelope = config.get("cortex.default_envelope", "RW")

    results = execute_cortex_streaming(
        prompt=query,
        connection=connection,
        envelope=envelope
    )
    exit_code = 0 if results.get("error") is None else 1

    # Log to audit if needed
    if logger_instance:
        import getpass
        logger_instance.log_execution(
            event_type="query_execution",
            user=getpass.getuser(),
            routing={
                "route": route,
                "confidence": confidence,
                "query": query
            },
            execution={
                "connection": connection,
                "envelope": envelope,
                "approval_mode": approval_mode
            },
            result={
                "exit_code": exit_code,
                "session_id": results.get("session_id")
            }
        )

    return exit_code


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point.

    Returns:
        Exit code
    """
    try:
        args = parse_args(argv)

        # Load configuration
        if args.config:
            config_path = Path(args.config)
        else:
            # Auto-detect config: check next to the installed package first,
            # then fall back to XDG config dir (~/.config/cortexcode-tool/)
            _lib_config = Path(__file__).parent.parent / "config.yaml"
            _xdg_config = Path.home() / ".config" / "cortexcode-tool" / "config.yaml"
            if _lib_config.exists():
                config_path = _lib_config
            elif _xdg_config.exists():
                config_path = _xdg_config
            else:
                config_path = None

        config = ConfigManager(
            config_path=config_path,
            org_policy_path=None  # Auto-detected
        )

        # Initialize components
        cache = CacheManager(
            cache_dir=config.get("security.cache_dir")
        )

        # Handle different commands
        if args.discover_capabilities:
            # Force capability rediscovery
            capabilities = discover_cortex_skills()
            cache.write("cortex-capabilities", capabilities, ttl=86400)
            print(f"Discovered {len(capabilities)} Cortex skills")
            return 0

        elif args.generate_ide_config:
            # Generate IDE configuration files
            capabilities = cache.read("cortex-capabilities")
            if not capabilities:
                capabilities = discover_cortex_skills()
                cache.write("cortex-capabilities", capabilities, ttl=86400)

            target = args.generate_ide_config

            # Cursor uses npx skills add (not this CLI tool) — skip silently
            if target == "cursor":
                return 0
            if target == "all":
                pass  # Continue with VSCode generation

            # TODO: Implement VSCode config generation
            if target in ["vscode", "all"]:
                print(f"Generating IDE config for: vscode")
                print("   VSCode integration: .vscode/tasks.json and .vscode/cortexcode.code-snippets")
                print("   (Generation not yet implemented - use existing templates)")

            return 0

        elif args.validate_config:
            # Validate configuration
            print("Configuration valid")
            print(f"  Approval mode: {config.get('security.approval_mode')}")
            print(f"  Default envelope: {config.get('cortex.default_envelope')}")
            return 0

        elif args.query:
            # Execute query
            audit_logger = None
            if config.get("security.approval_mode") in ["auto", "envelope_only"]:
                audit_logger = AuditLogger(
                    log_path=config.get("security.audit_log_path")
                )

            return execute_query(args.query, config, cache, audit_logger)

        else:
            # No command provided
            print("Error: No query or command provided", file=sys.stderr)
            print("Run 'cortexcode-tool --help' for usage", file=sys.stderr)
            return 1

    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        logger.exception("Unexpected error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
