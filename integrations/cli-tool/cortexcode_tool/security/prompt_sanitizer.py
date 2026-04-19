"""Prompt sanitizer for PII removal and injection detection."""

import re
from typing import List, Dict, Any


class PromptSanitizer:
    """Sanitizes prompts by removing PII and detecting injection attempts."""

    def __init__(self, enabled: bool = True):
        """
        Initialize the PromptSanitizer.

        Args:
            enabled: Whether sanitization is enabled (default: True)
        """
        self.enabled = enabled

    # PII regex patterns
    CREDIT_CARD_PATTERN = re.compile(
        r'\b(?:\d{4}[-\s]?){3}\d{4}\b'  # Matches formats: 1234-5678-9012-3456 or 1234567890123456
    )

    SSN_PATTERN = re.compile(
        r'\b\d{3}-\d{2}-\d{4}\b|'  # Matches: 123-45-6789
        r'\b\d{9}\b'  # Matches: 123456789 (exactly 9 digits)
    )

    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    PHONE_PATTERN = re.compile(
        r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    )

    API_KEY_PATTERN = re.compile(
        r'\b[A-Za-z0-9]{32,}\b'  # Simple pattern for long alphanumeric strings
    )

    # Injection detection patterns
    INJECTION_PATTERNS = [
        re.compile(r'ignore\s+(?:all\s+|the\s+)?(previous|above|prior)\s+(instructions|directions|prompts?)', re.IGNORECASE),
        re.compile(r'(enter|enable|activate)\s+developer\s+mode', re.IGNORECASE),
        re.compile(r'you\s+are\s+now\s+in\s+developer\s+mode', re.IGNORECASE),
        re.compile(r'disregard\s+(?:all\s+|the\s+)?(previous|above|prior)', re.IGNORECASE),
        re.compile(r'bypass\s+(restrictions|rules|guidelines)', re.IGNORECASE),
    ]

    def sanitize(self, text: str) -> str:
        """
        Sanitize text by removing PII and detecting injection attempts.

        Args:
            text: The text to sanitize

        Returns:
            Sanitized text with PII removed and injection warnings added
        """
        if not text:
            return text

        # If sanitization is disabled, return original text
        if not self.enabled:
            return text

        # Check for injection attempts first
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(text):
                return "[POTENTIAL INJECTION DETECTED - REMOVED]"

        # Remove PII
        text = self.CREDIT_CARD_PATTERN.sub('<CREDIT_CARD>', text)
        text = self.SSN_PATTERN.sub('<SSN>', text)
        text = self.EMAIL_PATTERN.sub('<EMAIL>', text)
        text = self.PHONE_PATTERN.sub('<PHONE>', text)
        # Note: API_KEY_PATTERN intentionally not applied due to high false positive rate
        # (matches common base64 strings, hashes, tokens that aren't API keys)
        # text = self.API_KEY_PATTERN.sub('<API_KEY>', text)

        return text

    def detect_injection(self, text: str) -> bool:
        """
        Detect potential prompt injection attempts.

        Args:
            text: The text to check for injection patterns

        Returns:
            True if injection attempt detected, False otherwise
        """
        if not text:
            return False

        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(text):
                return True

        return False

    def sanitize_sql_literals(self, sql: str) -> str:
        """
        Sanitize SQL string by removing PII from literals.

        Args:
            sql: The SQL string to sanitize

        Returns:
            Sanitized SQL string
        """
        return self.sanitize(sql)

    def sanitize_history(self, history: List[Dict[str, Any]], max_items: int = 3) -> List[Dict[str, Any]]:
        """
        Sanitize conversation history by limiting items and removing PII.

        Args:
            history: List of conversation history items (dicts with 'role' and 'content')
            max_items: Maximum number of items to keep (default: 3)

        Returns:
            Sanitized and limited history list
        """
        if not history:
            return []

        # Keep only the last max_items
        limited_history = history[-max_items:] if len(history) > max_items else history

        # Sanitize each item's content
        sanitized = []
        for item in limited_history:
            sanitized_item = item.copy()
            if 'content' in sanitized_item:
                sanitized_item['content'] = self.sanitize(sanitized_item['content'])
            sanitized.append(sanitized_item)

        return sanitized
