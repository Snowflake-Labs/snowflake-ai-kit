"""Base adapter interface for IDE integrations."""
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAdapter(ABC):
    """Abstract base class for IDE adapters.

    All IDE adapters must inherit from this class and implement
    the required methods.
    """

    @abstractmethod
    def generate_config(self, capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Generate IDE-specific configuration from capabilities.

        Args:
            capabilities: Discovered Cortex capabilities

        Returns:
            IDE-specific configuration dict
        """
        pass

    @abstractmethod
    def get_output_path(self) -> str:
        """Get the output path for generated config files.

        Returns:
            Relative or absolute path to config file
        """
        pass

    @abstractmethod
    def validate_capabilities(self, capabilities: Dict[str, Any]) -> bool:
        """Validate that capabilities contain required fields.

        Args:
            capabilities: Discovered Cortex capabilities

        Returns:
            True if capabilities are valid, False otherwise
        """
        pass

    def write_config(self, config: Dict[str, Any], output_path: str) -> None:
        """Write configuration to file.

        Default implementation writes JSON. Override for other formats.

        Args:
            config: Configuration dict to write
            output_path: Path to write config file
        """
        import json
        from pathlib import Path

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
