"""Utility functions for report generation and management."""

import os
from datetime import datetime
from pathlib import Path

from cra.config import settings


def build_report_name(path: str) -> str:
    """repo_YYYY-MM-DD_HHMM_<4-char-uid>.md"""
    repo = Path(path).resolve().name
    now = datetime.utcnow()
    uid = os.urandom(2).hex()[:4]  # 4 hex chars
    return f"{repo}_{now:%Y-%m-%d_%H%M}_{uid}.md"


def gc_reports():
    """Delete oldest reports past KEEP limit."""
    reports = sorted(
        settings.reports_dir_path.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in reports[settings.keep_reports :]:
        old.unlink(missing_ok=True)


def update_latest_report(new_file: Path):
    """Update the latest.md symlink to point to the new file."""
    latest = settings.reports_dir_path / "latest.md"
    latest.unlink(missing_ok=True)
    latest.symlink_to(new_file.name)
