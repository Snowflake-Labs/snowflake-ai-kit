"""Unit tests for discover_cortex.py script."""
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts import discover_cortex
from security.cache_manager import CacheManager


@pytest.fixture
def mock_cache_dir(tmp_path):
    """Create a temporary cache directory for testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def mock_capabilities():
    """Sample Cortex capabilities for testing."""
    return {
        "skill1": {
            "name": "Test Skill 1",
            "description": "A test skill",
            "triggers": ["trigger1", "trigger2"]
        },
        "skill2": {
            "name": "Test Skill 2",
            "description": "Another test skill",
            "triggers": ["trigger3"]
        }
    }


class TestCacheManagerIntegration:
    """Test CacheManager integration in discover_cortex."""

    def test_cache_manager_initialization(self, mock_cache_dir):
        """Test CacheManager is properly initialized with cache_dir."""
        cache_manager = CacheManager(mock_cache_dir)
        assert cache_manager.cache_dir == mock_cache_dir
        assert mock_cache_dir.exists()

    def test_write_capabilities_to_cache(self, mock_cache_dir, mock_capabilities):
        """Test writing capabilities to cache with TTL."""
        cache_manager = CacheManager(mock_cache_dir)

        # Write capabilities with 24-hour TTL
        cache_manager.write("cortex-capabilities", mock_capabilities, ttl=86400)

        # Verify cache file exists
        cache_file = mock_cache_dir / "cortex-capabilities.json"
        assert cache_file.exists()

        # Verify cache entry structure
        with open(cache_file, 'r') as f:
            cache_entry = json.load(f)

        assert "version" in cache_entry
        assert "created_at" in cache_entry
        assert "expires_at" in cache_entry
        assert "data" in cache_entry
        assert "fingerprint" in cache_entry
        assert cache_entry["data"] == mock_capabilities

    def test_read_capabilities_from_cache(self, mock_cache_dir, mock_capabilities):
        """Test reading capabilities from cache."""
        cache_manager = CacheManager(mock_cache_dir)

        # Write then read
        cache_manager.write("cortex-capabilities", mock_capabilities, ttl=86400)
        result = cache_manager.read("cortex-capabilities")

        assert result == mock_capabilities

    def test_cache_miss_returns_none(self, mock_cache_dir):
        """Test cache miss returns None."""
        cache_manager = CacheManager(mock_cache_dir)

        result = cache_manager.read("nonexistent-key")
        assert result is None

    def test_cache_expiration(self, mock_cache_dir, mock_capabilities):
        """Test expired cache returns None."""
        cache_manager = CacheManager(mock_cache_dir)

        # Write with TTL=0 (immediately expired)
        cache_manager.write("cortex-capabilities", mock_capabilities, ttl=0)

        # Small delay to ensure expiration
        import time
        time.sleep(0.1)

        result = cache_manager.read("cortex-capabilities")
        assert result is None

    def test_cache_integrity_validation(self, mock_cache_dir, mock_capabilities):
        """Test cache fingerprint validation detects tampering."""
        cache_manager = CacheManager(mock_cache_dir)

        # Write capabilities
        cache_manager.write("cortex-capabilities", mock_capabilities, ttl=86400)

        # Tamper with cache file (change data but not fingerprint)
        cache_file = mock_cache_dir / "cortex-capabilities.json"
        with open(cache_file, 'r') as f:
            cache_entry = json.load(f)

        cache_entry["data"]["skill1"]["name"] = "TAMPERED"

        with open(cache_file, 'w') as f:
            json.dump(cache_entry, f)

        # Read should return None due to invalid fingerprint
        result = cache_manager.read("cortex-capabilities")
        assert result is None


class TestDiscoverCortexScript:
    """Test discover_cortex.py main functionality."""

    @patch('scripts.discover_cortex.run_command')
    @patch('scripts.discover_cortex.read_skill_metadata')
    def test_discover_cortex_skills(self, mock_read_metadata, mock_run_command):
        """Test discovering Cortex skills."""
        # Mock cortex skill list output
        mock_run_command.return_value = (
            "skill1:\nskill2:\n",
            "",
            0
        )

        # Mock skill metadata
        mock_read_metadata.side_effect = [
            {
                "name": "Test Skill 1",
                "description": "A test skill",
                "triggers": ["trigger1"]
            },
            {
                "name": "Test Skill 2",
                "description": "Another test skill",
                "triggers": ["trigger2"]
            }
        ]

        result = discover_cortex.discover_cortex_skills()

        assert len(result) == 2
        assert "skill1" in result
        assert "skill2" in result
        assert result["skill1"]["name"] == "Test Skill 1"
        assert result["skill2"]["name"] == "Test Skill 2"

    @patch('scripts.discover_cortex.run_command')
    def test_discover_cortex_skills_command_failure(self, mock_run_command):
        """Test handling of cortex command failure."""
        # Mock command failure
        mock_run_command.return_value = ("", "Command not found", 1)

        result = discover_cortex.discover_cortex_skills()

        assert result == {}

    @patch('scripts.discover_cortex.discover_cortex_skills')
    def test_main_with_cache_manager(self, mock_discover, mock_cache_dir, mock_capabilities, capsys):
        """Test main() uses CacheManager for caching."""
        mock_discover.return_value = mock_capabilities

        # Mock sys.argv for argparse
        with patch('sys.argv', ['discover_cortex.py', '--cache-dir', str(mock_cache_dir)]):
            exit_code = discover_cortex.main()

        assert exit_code == 0

        # Verify cache was written
        cache_manager = CacheManager(mock_cache_dir)
        cached_data = cache_manager.read("cortex-capabilities")
        assert cached_data == mock_capabilities

        # Verify output
        captured = capsys.readouterr()
        assert "Discovered 2 Cortex skills" in captured.err

    @patch('scripts.discover_cortex.discover_cortex_skills')
    @patch('scripts.discover_cortex.ConfigManager')
    def test_main_with_default_cache_dir(self, mock_config_class, mock_discover, mock_capabilities, tmp_path):
        """Test main() uses default cache directory from config."""
        mock_discover.return_value = mock_capabilities

        # Create a temp home directory structure
        temp_cache = tmp_path / ".cache" / "cortex-skill"
        temp_cache.mkdir(parents=True)

        # Mock ConfigManager to return our temp cache directory
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = str(temp_cache)
        mock_config_class.return_value = mock_config_instance

        with patch('sys.argv', ['discover_cortex.py']):
            exit_code = discover_cortex.main()

        assert exit_code == 0

        # Verify cache file exists in default location
        default_cache_file = temp_cache / "cortex-capabilities.json"
        assert default_cache_file.exists()

    @patch('scripts.discover_cortex.discover_cortex_skills')
    @patch('scripts.discover_cortex.CacheManager')
    def test_cache_failure_graceful_handling(self, mock_cache_class, mock_discover, mock_capabilities, capsys):
        """Test graceful handling of cache failures."""
        mock_discover.return_value = mock_capabilities

        # Mock CacheManager to raise exception
        mock_cache_instance = Mock()
        mock_cache_instance.write.side_effect = Exception("Cache write failed")
        mock_cache_class.return_value = mock_cache_instance

        with patch('sys.argv', ['discover_cortex.py']):
            exit_code = discover_cortex.main()

        # Should still succeed even if cache fails
        assert exit_code == 0

        # Verify warning was logged
        captured = capsys.readouterr()
        assert "Warning" in captured.err or "warning" in captured.err.lower()


class TestBackwardCompatibility:
    """Test backward compatibility and migration from /tmp cache."""

    def test_cache_path_changed_from_tmp(self, mock_cache_dir):
        """Verify cache is no longer written to /tmp."""
        cache_manager = CacheManager(mock_cache_dir)

        # Write cache
        cache_manager.write("cortex-capabilities", {"test": "data"}, ttl=86400)

        # Verify NOT in /tmp
        tmp_cache = Path("/tmp/cortex-capabilities.json")
        assert not tmp_cache.exists()

        # Verify in specified cache_dir
        cache_file = mock_cache_dir / "cortex-capabilities.json"
        assert cache_file.exists()
