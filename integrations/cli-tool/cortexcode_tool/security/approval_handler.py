"""Approval handler for tool prediction and user approval flow.

Predicts which tools Cortex needs and formats approval prompts for users.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ApprovalResult:
    """Result of approval process."""
    approved: bool
    approve_all: bool
    user_response: str


class ApprovalHandler:
    """Handles tool prediction and user approval flow.

    Predicts which tools Cortex needs based on user prompts,
    formats approval prompts with confidence scores and warnings,
    and parses user responses.
    """

    def __init__(self):
        """Initialize approval handler."""
        self.last_confidence: float = 0.0

    def format_prompt(
        self,
        tools: List[str],
        envelope: str,
        confidence: float
    ) -> str:
        """Format approval prompt for user.

        Args:
            tools: List of tool names to approve
            envelope: Envelope type (RO/RW)
            confidence: Prediction confidence (0-1)

        Returns:
            Formatted approval prompt string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("CORTEX TOOL APPROVAL REQUEST")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Predicted Tools ({len(tools)}):")
        for tool in tools:
            lines.append(f"  - {tool}")
        lines.append("")
        lines.append(f"Envelope: {envelope}")
        lines.append(f"Prediction Confidence: {confidence * 100:.0f}%")
        lines.append("")
        lines.append("=" * 70)
        lines.append("APPROVAL OPTIONS:")
        lines.append("  yes         - Approve these tools for this request")
        lines.append("  yes to all  - Approve all (bypass future approvals)")
        lines.append("  no          - Reject this request")
        lines.append("=" * 70)
        lines.append("")
        lines.append("Your response: ")

        return "\n".join(lines)

    def request_approval(
        self,
        tools: List[str],
        envelope: str,
        confidence: float
    ) -> ApprovalResult:
        """Request approval from user via interactive prompt.

        Args:
            tools: List of tool names to approve
            envelope: Envelope type (RO/RW)
            confidence: Prediction confidence (0-1)

        Returns:
            ApprovalResult with approval decision
        """
        prompt = self.format_prompt(tools, envelope, confidence)
        print(prompt, end="")

        response = input().strip().lower()

        if response == "yes":
            return ApprovalResult(
                approved=True,
                approve_all=False,
                user_response="yes"
            )
        elif response == "yes to all":
            return ApprovalResult(
                approved=True,
                approve_all=True,
                user_response="yes to all"
            )
        elif response == "no":
            return ApprovalResult(
                approved=False,
                approve_all=False,
                user_response="no"
            )
        else:
            # Unknown response - treat as deny for safety
            return ApprovalResult(
                approved=False,
                approve_all=False,
                user_response=response
            )

    def predict_tools(self, query: str) -> List[str]:
        """Predict which tools will be needed for the given query.

        This is a simplified implementation that uses keyword matching.
        In production, this could be enhanced with ML-based prediction.

        Args:
            query: User query to analyze

        Returns:
            List of predicted tool names
        """
        query_lower = query.lower()
        predicted = []

        # Simple keyword-based prediction
        if any(word in query_lower for word in ["show", "select", "query", "databases", "tables", "revenue", "customers"]):
            predicted.append("snowflake_sql_execute")
            self.last_confidence = 0.85

        if any(word in query_lower for word in ["read", "view", "show"]):
            if "Read" not in predicted:
                predicted.append("Read")

        if any(word in query_lower for word in ["write", "create", "update"]):
            predicted.append("Write")

        # Default to reasonable confidence
        if not hasattr(self, 'last_confidence') or self.last_confidence == 0.0:
            self.last_confidence = 0.7

        return predicted
