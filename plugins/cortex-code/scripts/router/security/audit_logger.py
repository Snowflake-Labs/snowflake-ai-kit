"""Structured JSON audit logging with rotation and integrity chain."""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLogger:
    """Audit logger with structured JSON format, file rotation, and hash chain.

    Each log entry includes a hash of the previous entry, making tampering
    detectable: modifying or deleting any entry breaks the chain for all
    subsequent entries.

    Note: This implementation is designed for single-process use only.
    Concurrent writes from multiple processes may result in interleaved
    JSON lines or race conditions during rotation. For multi-process
    scenarios, consider using a log aggregation service or file locking.
    """

    VERSION = "2.1.0"

    def __init__(
        self,
        log_path: Path,
        rotation_size: str = "10MB",
        retention_days: int = 30
    ):
        """Initialize audit logger.

        Args:
            log_path: Path to audit log file
            rotation_size: Size threshold for rotation (e.g., "10MB", "1GB")
            retention_days: Days to retain rotated logs (NOT YET IMPLEMENTED)
        """
        self.log_path = Path(log_path)
        self.rotation_size = self._parse_size(rotation_size)
        self.retention_days = retention_days

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.log_path.exists():
            self.log_path.touch(mode=0o600)
        else:
            os.chmod(self.log_path, 0o600)

    def log_execution(
        self,
        event_type: str,
        user: str,
        routing: Dict[str, Any],
        execution: Dict[str, Any],
        result: Dict[str, Any],
        session_id: Optional[str] = None,
        cortex_session_id: Optional[str] = None,
        security: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a cortex execution event."""
        audit_id = str(uuid.uuid4())

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": self.VERSION,
            "audit_id": audit_id,
            "event_type": event_type,
            "user": user,
            "session_id": session_id,
            "cortex_session_id": cortex_session_id,
            "routing": routing,
            "execution": execution,
            "result": result,
            "security": security or {}
        }

        self._write_entry(entry)
        self._rotate_if_needed()

        return audit_id

    def _get_last_hash(self) -> str:
        """Read the hash of the last log entry for chain continuity.

        Reads up to 8KB from the end of the file to find the last complete
        JSON line, avoiding byte-by-byte seeking on large files.
        """
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return "GENESIS"

        try:
            with open(self.log_path, 'rb') as f:
                f.seek(0, 2)
                size = f.tell()
                # Read last 8KB (more than enough for one audit entry)
                read_size = min(size, 8192)
                f.seek(size - read_size)
                chunk = f.read(read_size)

            # Find the last complete line
            lines = chunk.split(b'\n')
            # Walk backwards to find last non-empty line
            for line in reversed(lines):
                line = line.strip()
                if line:
                    last_entry = json.loads(line)
                    return last_entry.get("entry_hash", "GENESIS")
        except (json.JSONDecodeError, OSError, KeyError):
            pass
        return "GENESIS"

    def _write_entry(self, entry: Dict[str, Any]) -> None:
        """Write entry with hash chain linking to previous entry.

        Verification algorithm: to verify entry N, strip 'entry_hash' from
        the dict, serialize with sort_keys=True, and SHA-256 the result.
        Compare against the stored entry_hash. Then verify entry N's
        prev_hash matches entry N-1's entry_hash.
        """
        prev_hash = self._get_last_hash()
        entry["prev_hash"] = prev_hash

        entry_json = json.dumps(entry, sort_keys=True)
        entry_hash = hashlib.sha256(entry_json.encode()).hexdigest()
        entry["entry_hash"] = entry_hash

        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes."""
        size_str = size_str.upper()
        multipliers = {
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        }

        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    value = float(size_str[:-len(suffix)])
                    return int(value * multiplier)
                except ValueError:
                    pass

        try:
            return int(size_str)
        except ValueError:
            return 10 * 1024 * 1024

    def _rotate_if_needed(self) -> None:
        """Rotate log file if exceeds size limit."""
        if not self.log_path.exists():
            return

        size = self.log_path.stat().st_size
        if size >= self.rotation_size:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            rotated_path = self.log_path.with_suffix(f".{timestamp}.log")
            self.log_path.rename(rotated_path)
            self.log_path.touch(mode=0o600)
