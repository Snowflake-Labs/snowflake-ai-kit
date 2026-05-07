"""Regression tests for predict_tools cache handling."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import predict_tools


def test_load_capabilities_uses_cache_manager_not_tmp_file():
    """Tool prediction should use CacheManager instead of predictable /tmp cache."""
    fake_cache = MagicMock()
    fake_cache.read.return_value = {"qa": {"triggers": ["data quality"]}}

    with patch.object(predict_tools, "CacheManager", return_value=fake_cache) as cache_cls:
        capabilities = predict_tools.load_capabilities()

    cache_cls.assert_called_once()
    fake_cache.read.assert_called_once_with("cortex-capabilities")
    assert capabilities == {"qa": {"triggers": ["data quality"]}}
