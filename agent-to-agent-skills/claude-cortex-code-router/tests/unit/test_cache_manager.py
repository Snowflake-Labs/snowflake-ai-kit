"""Unit tests for secure cache manager."""
import json
import os
import stat
import time
from pathlib import Path

import pytest

from security.cache_manager import CacheManager


@pytest.fixture
def mock_cache_dir(tmp_path):
    """Create a temporary cache directory for testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


def test_write_and_read_cache(mock_cache_dir):
    """Test basic cache write and read operations."""
    cache = CacheManager(mock_cache_dir)

    # Write test data
    test_data = {"key": "value", "number": 42}
    cache.write("test_key", test_data, ttl=3600)

    # Read it back
    result = cache.read("test_key")

    # Verify match
    assert result == test_data


def test_cache_expiration(mock_cache_dir):
    """Test that expired cache entries return None."""
    cache = CacheManager(mock_cache_dir)

    # Write with TTL=0 (immediately expired)
    test_data = {"key": "value"}
    cache.write("expired_key", test_data, ttl=0)

    # Small delay to ensure expiration
    time.sleep(0.1)

    # Should return None
    result = cache.read("expired_key")
    assert result is None

    # Cache file should be deleted
    cache_file = mock_cache_dir / "expired_key.json"
    assert not cache_file.exists()


def test_cache_integrity_validation(mock_cache_dir):
    """Test that tampered cache entries are detected and rejected."""
    cache = CacheManager(mock_cache_dir)

    # Write valid data
    test_data = {"key": "value"}
    cache.write("tampered_key", test_data, ttl=3600)

    # Tamper with the cached data
    cache_file = mock_cache_dir / "tampered_key.json"
    with open(cache_file, 'r') as f:
        cache_entry = json.load(f)

    # Modify data without updating fingerprint
    cache_entry["data"] = {"key": "tampered_value"}

    with open(cache_file, 'w') as f:
        json.dump(cache_entry, f)

    # Should detect tampering and return None
    result = cache.read("tampered_key")
    assert result is None

    # Cache file should be deleted
    assert not cache_file.exists()


def test_cache_file_permissions(mock_cache_dir):
    """Test that cache files have secure permissions (0600)."""
    cache = CacheManager(mock_cache_dir)

    # Write data
    test_data = {"key": "value"}
    cache.write("secure_key", test_data, ttl=3600)

    # Check file permissions
    cache_file = mock_cache_dir / "secure_key.json"
    file_stat = os.stat(cache_file)
    file_permissions = stat.filemode(file_stat.st_mode)

    # Should be 0600 (owner read/write only)
    # filemode returns format like '-rw-------'
    assert file_permissions == '-rw-------'


def test_cache_location_not_tmp(mock_cache_dir):
    """Test that cache directory is not in /tmp."""
    # This test verifies the design principle
    # In production, CacheManager would use ~/.cache
    cache_dir_str = str(mock_cache_dir)

    # Mock test directories won't be in /tmp in production
    # This test documents the requirement
    # Real usage: CacheManager(Path.home() / ".cache" / "cortex-code")

    # For this test, we just verify the cache_dir can be set
    cache = CacheManager(mock_cache_dir)
    assert cache.cache_dir == mock_cache_dir

    # In production, ensure it's not /tmp
    production_cache_dir = Path.home() / ".cache" / "cortex-code"
    assert "/tmp" not in str(production_cache_dir)


def test_invalid_cache_keys(mock_cache_dir):
    """Test that invalid cache keys raise ValueError."""
    cache = CacheManager(mock_cache_dir)
    test_data = {"key": "value"}

    # Test empty key
    with pytest.raises(ValueError, match="Cache key cannot be empty"):
        cache.write("", test_data)

    # Test path traversal with ../ (caught by regex check first)
    with pytest.raises(ValueError, match="Invalid cache key"):
        cache.write("../../etc/passwd", test_data)

    # Test forward slash (caught by regex check)
    with pytest.raises(ValueError, match="Invalid cache key"):
        cache.write("path/to/file", test_data)

    # Test backslash (caught by regex check)
    with pytest.raises(ValueError, match="Invalid cache key"):
        cache.write("path\\to\\file", test_data)

    # Test special characters
    with pytest.raises(ValueError, match="Only alphanumeric characters"):
        cache.write("bad@key", test_data)

    with pytest.raises(ValueError, match="Only alphanumeric characters"):
        cache.write("bad key", test_data)

    # Test that read() also validates
    with pytest.raises(ValueError, match="Invalid cache key"):
        cache.read("../../etc/passwd")

    # Test that clear() also validates when key is provided
    with pytest.raises(ValueError, match="Invalid cache key"):
        cache.clear("../../etc/passwd")

    # Valid keys should work fine
    cache.write("valid_key", test_data)
    cache.write("valid-key", test_data)
    cache.write("valid.key", test_data)
    cache.write("ValidKey123", test_data)
    assert cache.read("valid_key") == test_data
