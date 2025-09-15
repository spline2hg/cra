from sqlalchemy.orm import Session
from cra_web import models
from cra_web.models import Job, Issue
from sqlalchemy.sql import func


def add_issue(
    db: Session, job_id: str, issue: Issue
) -> models.Issue:
    """Add a new issue to the database."""
    db_issue = models.Issue(
        job_id=job_id,
        file=issue.file,
        line=issue.line,
        severity=issue.severity,
        rule=issue.rule,
        description=issue.description,
        fix=issue.fix
    )
    db.add(db_issue)
    db.commit()
    db.refresh(db_issue)
    return db_issue


def get_issues_by_job_id(db: Session, job_id: str):
    """Retrieve issues by job ID."""
    return db.query(models.Issue).filter(models.Issue.job_id == job_id).all()


def add_report(
    db: Session, report_id: str, github_url: str, content: str, user_id: int = None
) -> models.Report:
    """Add a new report to the database."""
    # Set visibility to private by default if user is logged in, otherwise public
    visibility = "private" if user_id is not None else "public"
    report = models.Report(
        id=report_id,
        github_url=github_url,
        report_content=content,
        user_id=user_id,
        visibility=visibility,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_recent_reports(db: Session, limit: int = 10, user_id: int = None):
    """Retrieve recent reports from the database, filtered by user if specified."""
    query = db.query(models.Report).order_by(models.Report.created_at.desc())
    if user_id is not None:
        # For logged-in users, show their private reports and all public reports
        query = query.filter(
            (models.Report.user_id == user_id) | (models.Report.visibility == "public")
        )
    else:
        # For anonymous users, show only public reports
        query = query.filter(models.Report.visibility == "public")
    return query.limit(limit).all()


def add_chat_message(
    db: Session, job_id: str, role: str, content: str
) -> models.ChatMessage:
    """Add a new chat message to the database."""
    msg = models.ChatMessage(job_id=job_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_chat_history(db: Session, job_id: str):
    """Retrieve chat history for a specific job."""
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.job_id == job_id)
        .order_by(models.ChatMessage.created_at)
        .all()
    )


def create_job(
    db: Session,
    job_id: str,
    github_url: str,
    repo_name: str,
    folder_path: str,
    report_path: str,
    user_id: int = None,
) -> Job:
    """Create a new job in the database."""
    # Set visibility to private by default if user is logged in, otherwise public
    visibility = "private" if user_id is not None else "public"
    job = Job(
        id=job_id,
        github_url=github_url,
        repo_name=repo_name,
        folder_path=folder_path,
        report_path=report_path,
        user_id=user_id,
        visibility=visibility,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: str, user_id: int = None) -> Job | None:
    """Retrieve a job by its ID, optionally checking user ownership."""
    query = db.query(Job).filter(Job.id == job_id)
    if user_id is not None:
        # For logged-in users, show their private jobs and all public jobs
        query = query.filter((Job.user_id == user_id) | (Job.visibility == "public"))
    else:
        # For anonymous users, show only public jobs
        query = query.filter(Job.visibility == "public")
    return query.first()


def create_user(
    db: Session, github_id: str, github_username: str, github_token: str = None
) -> models.User:
    """Create a new user in the database."""
    user = models.User(
        github_id=github_id, github_username=github_username, github_token=github_token
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_github_id(db: Session, github_id: str) -> models.User | None:
    """Retrieve a user by their GitHub ID."""
    return db.query(models.User).filter(models.User.github_id == github_id).first()


def update_user_token(db: Session, user_id: int, github_token: str) -> models.User:
    """Update a user's GitHub token."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.github_token = github_token
        user.last_login = func.now()
        db.commit()
        db.refresh(user)
    return user


def create_oauth_state(db: Session, state: str) -> models.OAuthState:
    """Create a new OAuth state in the database."""
    oauth_state = models.OAuthState(state=state)
    db.add(oauth_state)
    db.commit()
    db.refresh(oauth_state)
    return oauth_state


def get_oauth_state(db: Session, state: str) -> models.OAuthState | None:
    """Retrieve an OAuth state by its value."""
    return db.query(models.OAuthState).filter(models.OAuthState.state == state).first()


def delete_oauth_state(db: Session, state: str) -> bool:
    """Delete an OAuth state from the database."""
    oauth_state = (
        db.query(models.OAuthState).filter(models.OAuthState.state == state).first()
    )
    if oauth_state:
        db.delete(oauth_state)
        db.commit()
        return True
    return False
