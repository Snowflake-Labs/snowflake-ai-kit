"""Prompt sanitizer for PII removal and injection detection."""

import re
import unicodedata
from typing import List, Dict, Any


ZERO_WIDTH_CHARS = frozenset([
    '\u200b',  # zero-width space
    '\u200c',  # zero-width non-joiner
    '\u200d',  # zero-width joiner
    '\u2060',  # word joiner
    '\ufeff',  # BOM / zero-width no-break space
    '\u00ad',  # soft hyphen
    '\u180e',  # Mongolian vowel separator
])


class PromptSanitizer:
    """Sanitizes prompts by removing PII and detecting injection attempts."""

    # PII regex patterns
    CREDIT_CARD_PATTERN = re.compile(
        r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
    )

    SSN_PATTERN = re.compile(
        r'\b\d{3}-\d{2}-\d{4}\b|'
        r'\b\d{9}\b'
    )

    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    PHONE_PATTERN = re.compile(
        r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    )

    API_KEY_PATTERN = re.compile(
        r'\b[A-Za-z0-9]{32,}\b'
    )

    # Injection detection patterns
    INJECTION_PATTERNS = [
        re.compile(r'ignore\s+(?:all\s+|the\s+)?(previous|above|prior)\s+(instructions|directions|prompts?)', re.IGNORECASE),
        re.compile(r'(enter|enable|activate)\s+developer\s+mode', re.IGNORECASE),
        re.compile(r'you\s+are\s+now\s+in\s+developer\s+mode', re.IGNORECASE),
        re.compile(r'disregard\s+(?:all\s+|the\s+)?(previous|above|prior)', re.IGNORECASE),
        re.compile(r'bypass\s+(restrictions|rules|guidelines)', re.IGNORECASE),
    ]

    def _normalize_text(self, text: str) -> str:
        """Normalize Unicode and strip zero-width characters before pattern matching."""
        normalized = unicodedata.normalize('NFKD', text)
        return ''.join(c for c in normalized if c not in ZERO_WIDTH_CHARS)

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

        normalized = self._normalize_text(text)

        # Check for injection attempts on normalized text
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(normalized):
                return "[POTENTIAL INJECTION DETECTED - REMOVED]"

        # Remove PII from original text (preserving structure)
        text = self.CREDIT_CARD_PATTERN.sub('<CREDIT_CARD>', text)
        text = self.SSN_PATTERN.sub('<SSN>', text)
        text = self.EMAIL_PATTERN.sub('<EMAIL>', text)
        text = self.PHONE_PATTERN.sub('<PHONE>', text)
        # Note: API_KEY_PATTERN intentionally not applied due to high false positive rate
        # (matches common base64 strings, hashes, tokens that aren't API keys)

        return text

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

        limited_history = history[-max_items:] if len(history) > max_items else history

        sanitized = []
        for item in limited_history:
            sanitized_item = item.copy()
            if 'content' in sanitized_item:
                sanitized_item['content'] = self.sanitize(sanitized_item['content'])
            sanitized.append(sanitized_item)

        return sanitized
