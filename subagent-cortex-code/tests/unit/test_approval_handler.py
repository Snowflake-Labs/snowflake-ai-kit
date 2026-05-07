#!/usr/bin/env python3
"""
Unit tests for approval handler with tool prediction.
"""

import pytest
from security.approval_handler import ApprovalHandler, ApprovalResult


class TestApprovalHandler:
    """Test approval handler functionality."""

    def test_predict_tools_for_prompt(self):
        """Test tool prediction works correctly."""
        handler = ApprovalHandler()

        # Test SQL query prediction
        result = handler.predict_tools(
            "Query Snowflake for sales data",
            envelope={}
        )

        assert "tools" in result
        assert "confidence" in result
        assert "reasoning" in result
        assert "snowflake_sql_execute" in result["tools"]
        assert result["confidence"] > 0.5

    def test_format_approval_prompt(self):
        """Test formatting includes all required information."""
        handler = ApprovalHandler()

        tools = ["snowflake_sql_execute", "bash", "read", "write"]
        confidence = 0.85
        envelope = {
            "user_prompt": "Query Snowflake for sales data and save to CSV",
            "session_id": "test-session"
        }
        reasoning = "Matched patterns: query, save"

        prompt = handler.format_approval_prompt(tools, confidence, envelope, reasoning)

        # Verify all components are present
        assert "Query Snowflake for sales data and save to CSV" in prompt
        assert "snowflake_sql_execute" in prompt
        assert "bash" in prompt
        assert "read" in prompt
        assert "write" in prompt
        assert "85%" in prompt or "0.85" in prompt
        assert reasoning in prompt
        assert "approve" in prompt.lower()
        assert "deny" in prompt.lower()

    def test_low_confidence_warning(self):
        """Test warning for low confidence predictions."""
        handler = ApprovalHandler(confidence_threshold=0.7)

        tools = ["snowflake_sql_execute"]
        confidence = 0.5  # Below threshold
        envelope = {"user_prompt": "Do something"}
        reasoning = "No clear patterns"

        prompt = handler.format_approval_prompt(tools, confidence, envelope, reasoning)

        # Should include warning about low confidence
        assert "warning" in prompt.lower() or "uncertain" in prompt.lower() or "low confidence" in prompt.lower()

    def test_approval_result_structure(self):
        """Test ApprovalResult dataclass structure."""
        result = ApprovalResult(
            approved=True,
            allowed_tools=["snowflake_sql_execute", "bash"],
            user_response="approve"
        )

        assert result.approved is True
        assert result.allowed_tools == ["snowflake_sql_execute", "bash"]
        assert result.user_response == "approve"


class TestToolPredictionScoring:
    """Test tool prediction confidence scoring."""

    def test_high_confidence_clear_patterns(self):
        """Test high confidence for clear patterns."""
        handler = ApprovalHandler()

        result = handler.predict_tools(
            "SELECT data FROM sales_table WHERE date > '2024-01-01' and write results to CSV file",
            envelope={}
        )

        assert result["confidence"] >= 0.7
        assert "snowflake_sql_execute" in result["tools"]
        assert "write" in result["tools"]

    def test_medium_confidence_ambiguous(self):
        """Test medium confidence for ambiguous prompts."""
        handler = ApprovalHandler()

        result = handler.predict_tools(
            "Process the data",
            envelope={}
        )

        assert 0.4 <= result["confidence"] <= 0.8
        assert "bash" in result["tools"]  # Base tools always present
        assert "read" in result["tools"]

    def test_base_tools_always_included(self):
        """Test base Snowflake tools are always included."""
        handler = ApprovalHandler()

        result = handler.predict_tools(
            "Random unrelated request",
            envelope={}
        )

        # Base tools should always be present
        assert "snowflake_sql_execute" in result["tools"]
        assert "bash" in result["tools"]
        assert "read" in result["tools"]
