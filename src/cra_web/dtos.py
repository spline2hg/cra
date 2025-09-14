from pydantic import BaseModel
from typing import List


class Issue(BaseModel):
    """Model for representing a code issue."""

    file: str
    line: int
    severity: str
    rule: str
    description: str
    fix: str


class AnalysisResult(BaseModel):
    """Model for representing the analysis result."""

    total_issues: int
    severity_counts: dict
    language_split: dict
    issues: List[Issue]
