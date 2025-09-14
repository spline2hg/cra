import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def get_project_root():
    """Get the project root directory."""
    current_path = Path(__file__).parent.absolute()
    while current_path != current_path.parent:
        if (current_path / "pyproject.toml").exists():
            return current_path
        current_path = current_path.parent
    return Path.cwd()


class Settings:
    """Application settings and configuration."""

    def __init__(self):
        project_root = get_project_root()
        
        self.codebase_path = os.getenv("CODEBASE_PATH", str(project_root))
        self.cache_dir = os.getenv("CACHE_DIR", str(project_root / ".cra_cache_temp"))
        self.reports_dir = os.getenv("REPORTS_DIR", str(project_root / "Reports"))
        self.keep_reports = int(os.getenv("CRA_KEEP_REPORTS", "10"))
        self.secret_key = os.getenv(
            "SECRET_KEY", "maybe-secret-key"
        )

        # GitHub OAuth Configuration
        self.github_client_id = os.getenv("GITHUB_CLIENT_ID")
        self.github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")

        # LLM Configuration
        self.llm_base_url = os.getenv("LLM_BASE_URL")
        self.llm_api_key = os.getenv("LLM_API_KEY")
        self.llm_model = os.getenv("MODEL", "gemini-2.0-flash")

        # Embedding Configuration
        self.embed_model = os.getenv("EMBED_MODEL", "models/embedding-001")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        # Document Processing
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "800"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "120"))

        # Ensure directories exist
        Path(self.cache_dir).mkdir(exist_ok=True)
        Path(self.reports_dir).mkdir(exist_ok=True)

    @property
    def latest_report_path(self):
        """Path to the latest report file."""
        return os.path.join(self.reports_dir, ".latest_report.md")

    @property
    def reports_dir_path(self):
        """Pathlib Path object for the reports directory."""
        return Path(self.reports_dir)


settings = Settings()
