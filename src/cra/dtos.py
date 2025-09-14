import os
from typing import List

from pydantic import BaseModel, Field


class CodeChange(BaseModel):
    """Schema for a single code change recommendation."""

    file_path: str = Field(description="Path to the file being changed")
    line_number: int = Field(description="Line number where change should be made")
    original_code: str = Field(description="Original code that should be changed")
    recommended_code: str = Field(description="Recommended replacement code")
    reason: str = Field(description="Explanation for why this change is recommended")
    issue_type: str = Field(
        description="Type of issue being fixed (e.g., 'pylint', 'flake8', 'complexity', 'security')"
    )


class DiffRecommendations(BaseModel):
    """Schema for all diff-style recommendations."""

    summary: str = Field(description="Brief summary of all recommended changes")
    changes: List[CodeChange] = Field(description="List of specific code changes")
    priority_order: List[str] = Field(
        description="List of issue types in order of priority (highest first)"
    )
