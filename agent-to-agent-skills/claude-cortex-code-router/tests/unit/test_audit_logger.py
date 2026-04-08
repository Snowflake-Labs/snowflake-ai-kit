"""Unit tests for audit logger."""
import json
import os
import stat
from pathlib import Path

import pytest

from security.audit_logger import AuditLogger


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for test logs."""
    return tmp_path


def test_create_audit_entry(temp_dir):
    """Test creating audit log entry."""
    log_path = temp_dir / "audit.log"
    logger = AuditLogger(log_path)

    # Log an execution event
    audit_id = logger.log_execution(
        event_type="cortex_complete",
        user="test_user",
        routing={
            "model": "mistral-large2",
            "warehouse": "COMPUTE_WH"
        },
        execution={
            "prompt": "SELECT 1",
            "duration_ms": 123
        },
        result={
            "status": "success",
            "tokens": 50
        }
    )

    # Verify audit_id returned
    assert audit_id is not None
    assert isinstance(audit_id, str)

    # Verify file exists
    assert log_path.exists()

    # Read and parse JSON
    with open(log_path, 'r') as f:
        line = f.readline()
        entry = json.loads(line)

    # Check all required fields present
    assert entry["event_type"] == "cortex_complete"
    assert entry["user"] == "test_user"
    assert entry["routing"]["model"] == "mistral-large2"
    assert entry["execution"]["prompt"] == "SELECT 1"
    assert entry["result"]["status"] == "success"
    assert "timestamp" in entry
    assert entry["version"] == "2.0.0"
    assert entry["audit_id"] == audit_id


def test_audit_log_format_validation(temp_dir):
    """Test multiple entries are valid JSON."""
    log_path = temp_dir / "audit.log"
    logger = AuditLogger(log_path)

    # Log 3 entries
    for i in range(3):
        logger.log_execution(
            event_type=f"test_event_{i}",
            user=f"user_{i}",
            routing={"model": "test"},
            execution={"id": i},
            result={"status": "ok"}
        )

    # Read file line-by-line and parse each as JSON
    with open(log_path, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 3

    for line in lines:
        try:
            entry = json.loads(line)
            assert "timestamp" in entry
            assert "version" in entry
            assert "event_type" in entry
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in audit log: {e}")


def test_audit_log_permissions(temp_dir):
    """Test file has 0600 permissions."""
    log_path = temp_dir / "audit.log"
    logger = AuditLogger(log_path)

    # Create audit log by logging an entry
    logger.log_execution(
        event_type="test",
        user="test_user",
        routing={},
        execution={},
        result={}
    )

    # Check file permissions
    file_stat = os.stat(log_path)
    file_mode = stat.filemode(file_stat.st_mode)

    # Assert permissions are owner read/write only
    assert file_mode == "-rw-------", f"Expected -rw-------, got {file_mode}"
