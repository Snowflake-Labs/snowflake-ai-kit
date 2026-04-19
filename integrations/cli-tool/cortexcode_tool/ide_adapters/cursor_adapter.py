"""Cursor IDE adapter for generating .cursor/rules/*.mdc files.

DEPRECATED: Cursor now uses the Claude Code skill (~/.claude/skills/cortex-code/) instead
of the standalone CLI tool. This adapter is preserved for reference but should not be used.

For Cursor setup, manually configure .cursor/rules/cortexcode-tool.mdc to reference the skill.
"""
from typing import Dict, Any
from .base_adapter import BaseAdapter

class CursorAdapter(BaseAdapter):
    """Generate Cursor .mdc configuration from Cortex capabilities.

    DEPRECATED: This adapter is no longer recommended for Cursor.
    Cursor should use the Claude Code skill (~/.claude/skills/cortex-code/) instead.
    """

    def generate_config(self, capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Cursor .mdc file content.

        DEPRECATED: Raises a warning. Cursor should use the Claude Code skill instead.

        Args:
            capabilities: Discovered Cortex capabilities

        Returns:
            Dict with 'content' key containing MDC markdown

        Raises:
            DeprecationWarning: This adapter is deprecated for Cursor
        """
        import warnings
        warnings.warn(
            "CursorAdapter is deprecated. Cursor should use the Claude Code skill "
            "(~/.claude/skills/cortex-code/) instead of the standalone CLI tool. "
            "For VSCode/Windsurf, use VSCodeAdapter.",
            DeprecationWarning,
            stacklevel=2
        )
        skills = capabilities.get("skills", [])

        # Extract all triggers
        all_triggers = []
        for skill in skills:
            all_triggers.extend(skill.get("triggers", []))

        # Build MDC content
        content = self._build_mdc_content(skills, all_triggers)

        return {"content": content}

    def get_output_path(self) -> str:
        """Get output path for Cursor rules file."""
        return ".cursor/rules/cortexcode-tool.mdc"

    def validate_capabilities(self, capabilities: Dict[str, Any]) -> bool:
        """Validate capabilities have required fields."""
        return "skills" in capabilities and len(capabilities["skills"]) > 0

    def _build_mdc_content(self, skills, triggers) -> str:
        """Build MDC file content."""
        # Frontmatter
        content = "---\n"
        content += "alwaysApply: true\n"
        content += "---\n\n"

        # Header
        content += "# Cortexcode Tool Integration\n\n"
        content += "This project has access to cortexcode-tool, a CLI that provides Snowflake expertise via Cortex Code.\n\n"

        # When to suggest section
        content += "## When to suggest cortexcode-tool\n\n"
        content += "### ALWAYS suggest for questions about:\n"
        content += "- Snowflake databases, warehouses, schemas, tables, views\n"
        content += "- SQL queries for Snowflake data\n"
        content += "- Data quality checks, validation, profiling\n"
        content += "- Cortex AI features: Cortex Search, Cortex Analyst, ML functions\n"
        content += "- Semantic views, data modeling\n"
        content += "- Snowpark (Python/Scala), dynamic tables, streams, tasks\n"
        content += "- Snowflake security, roles, policies, governance\n\n"

        # Keywords section
        content += "### Keywords that trigger tool suggestion:\n"
        keywords = ", ".join(triggers[:20])  # Limit to avoid huge list
        content += f"{keywords}\n\n"

        # How to suggest section
        content += "### How to suggest:\n"
        content += 'When you detect a Snowflake-related question, respond:\n'
        content += '"I can help with that using cortexcode-tool. Run:\n'
        content += '```bash\n'
        content += 'cortexcode-tool \\"your question here\\"\n'
        content += '```"\n\n'

        # Usage examples
        content += "## Tool usage examples\n\n"
        content += '1. Query Snowflake data:\n'
        content += '   `cortexcode-tool "Show me top 10 customers by revenue"`\n\n'
        content += '2. Data quality check:\n'
        content += '   `cortexcode-tool "Check data quality for SALES_DATA table"`\n\n'
        content += '3. Create semantic view:\n'
        content += '   `cortexcode-tool "Create semantic view for customer analytics"`\n\n'

        # Security section
        content += "## Security\n"
        content += "- Tool will show approval prompt before executing (default)\n"
        content += "- Configure ~/.config/cortexcode-tool/config.yaml to change approval mode\n"
        content += "- All operations logged to ~/.config/cortexcode-tool/audit.log\n"

        return content

    def write_config(self, config: Dict[str, Any], output_path: str) -> None:
        """Write MDC file (override to write markdown, not JSON)."""
        from pathlib import Path

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            f.write(config["content"])
