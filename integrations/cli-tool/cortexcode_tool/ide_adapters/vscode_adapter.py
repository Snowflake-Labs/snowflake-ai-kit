"""VSCode IDE adapter for generating .vscode/ configuration."""
from typing import Dict, Any, List
from .base_adapter import BaseAdapter

class VSCodeAdapter(BaseAdapter):
    """Generate VSCode tasks and snippets from Cortex capabilities."""

    def generate_config(self, capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Generate VSCode tasks.json and snippets.

        Args:
            capabilities: Discovered Cortex capabilities

        Returns:
            Dict with 'tasks.json' and 'snippets.json' keys
        """
        tasks = self._build_tasks_json()
        snippets = self._build_snippets_json()

        return {
            "tasks.json": tasks,
            "snippets.json": snippets
        }

    def get_output_path(self) -> str:
        """Not used - VSCode has multiple output files."""
        return ".vscode/"

    def get_output_paths(self) -> List[str]:
        """Get all output paths for VSCode files."""
        return [
            ".vscode/tasks.json",
            ".vscode/cortexcode.code-snippets"
        ]

    def validate_capabilities(self, capabilities: Dict[str, Any]) -> bool:
        """Validate capabilities have required fields."""
        return "skills" in capabilities

    def _build_tasks_json(self) -> Dict[str, Any]:
        """Build tasks.json configuration."""
        return {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "Cortex: Query Snowflake",
                    "type": "shell",
                    "command": "cortexcode-tool",
                    "args": ["${input:userQuery}"],
                    "presentation": {
                        "echo": True,
                        "reveal": "always",
                        "panel": "new"
                    },
                    "problemMatcher": []
                },
                {
                    "label": "Cortex: Data Quality Check",
                    "type": "shell",
                    "command": "cortexcode-tool",
                    "args": ["Check data quality for ${input:tableName}"],
                    "presentation": {
                        "echo": True,
                        "reveal": "always",
                        "panel": "new"
                    },
                    "problemMatcher": []
                }
            ],
            "inputs": [
                {
                    "id": "userQuery",
                    "type": "promptString",
                    "description": "Enter your Snowflake question"
                },
                {
                    "id": "tableName",
                    "type": "promptString",
                    "description": "Enter table name (e.g., SALES_DATA)"
                }
            ]
        }

    def _build_snippets_json(self) -> Dict[str, Any]:
        """Build code snippets configuration."""
        return {
            "Cortex Query": {
                "prefix": "cortex",
                "body": ["cortexcode-tool \"$1\""],
                "description": "Run Cortex Code query for Snowflake"
            },
            "Cortex Data Quality": {
                "prefix": "cortex-dq",
                "body": ["cortexcode-tool \"Check data quality for ${1:TABLE_NAME}\""],
                "description": "Run data quality check"
            },
            "Cortex Semantic View": {
                "prefix": "cortex-sv",
                "body": ["cortexcode-tool \"Create semantic view for ${1:dataset}\""],
                "description": "Create semantic view"
            }
        }

    def write_config(self, config: Dict[str, Any], output_path: str) -> None:
        """Write multiple VSCode config files."""
        import json
        from pathlib import Path

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write tasks.json
        tasks_file = output_dir / "tasks.json"
        with open(tasks_file, 'w') as f:
            json.dump(config["tasks.json"], f, indent=2)

        # Write snippets
        snippets_file = output_dir / "cortexcode.code-snippets"
        with open(snippets_file, 'w') as f:
            json.dump(config["snippets.json"], f, indent=2)
