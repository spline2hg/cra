from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from cra_web.database import Base


class ChatMessage(Base):
    """Model for storing chat messages."""

    __tablename__ = "chat_messages"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    job_id = Column(String, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert chat message to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(Base):
    """Model for storing user information."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    github_id = Column(String, unique=True, nullable=False)
    github_username = Column(String, nullable=False)
    github_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "github_id": self.github_id,
            "github_username": self.github_username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class OAuthState(Base):
    """Model for storing OAuth state parameters for CSRF protection."""

    __tablename__ = "oauth_states"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    state = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert OAuth state to dictionary."""
        return {
            "id": self.id,
            "state": self.state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Job(Base):
    """Model for storing job information."""

    __tablename__ = "jobs"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    github_url = Column(String, nullable=False)
    repo_name = Column(String, nullable=False)
    folder_path = Column(String, nullable=False)
    report_path = Column(String, nullable=False)
    user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    visibility = Column(
        String, default="private", nullable=False
    )  # "private" or "public"


class Report(Base):
    """Model for storing analysis reports."""

    __tablename__ = "reports"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    github_url = Column(String)
    report_content = Column(Text)
    visibility = Column(
        String, default="private", nullable=False
    )  # "private" or "public"

    def to_dict(self):
        """Convert report to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "github_url": self.github_url,
            "report_content": self.report_content,
        }
