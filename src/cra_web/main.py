import os
import uuid
import subprocess
import re
from urllib.parse import urlencode

import markdown
import httpx
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from cra_web.parsers import parse_lint_report
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from cra.lint_tool.main import run_linters
from cra.chat import CodebaseChat
from cra.llm_report import generate_llm_summary
from cra_web.database import get_db, engine, Base
from cra_web import crud
from cra_web.models import Issue as IssueModel
from cra_web.dtos import Issue
from cra.config import settings
from langchain_core.messages import HumanMessage, AIMessage

BASE_DIR = os.path.dirname(__file__)
TMP_BASE_DIR = os.path.join(settings.cache_dir, "cra-tmp")

app = FastAPI(title="CRA Web Interface")

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def markdown_to_html(md_text):
    """Convert markdown text to HTML."""
    return markdown.markdown(md_text, extensions=["fenced_code", "tables"])


Base.metadata.create_all(bind=engine)


def extract_repo_name(github_url: str) -> str:
    """Extract repository name from GitHub URL."""
    match = re.search(r"github\.com[/:]([^/]+)/([^/.]+)", github_url)
    if match:
        return f"{match.group(1)}_{match.group(2)}"
    return "unknown_repo"


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request, db: Session = Depends(get_db)):
    # Get user ID from session if available
    user_id = request.session.get("user_id")

    # Get reports filtered by user
    reports = crud.get_recent_reports(db, 10, user_id)
    past_reports = [(r.id, r.created_at, r.github_url, r.visibility) for r in reports]

    # Check if user is logged in
    github_token = request.session.get("github_token")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "github_token": github_token,
            "github_client_id": settings.github_client_id,
            "past_reports": past_reports,
        },
    )


@app.get("/login/github")
async def github_login(request: Request, db: Session = Depends(get_db)):
    if not settings.github_client_id:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    github_oauth_url = "https://github.com/login/oauth/authorize"

    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/auth/github/callback"

    state = str(uuid.uuid4())

    crud.create_oauth_state(db, state)

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": redirect_uri,
        "scope": "repo",
        "state": state,
    }

    redirect_url = f"{github_oauth_url}?{urlencode(params)}"
    return RedirectResponse(url=redirect_url)


@app.get("/auth/github/callback")
async def github_callback(
    request: Request, code: str = None, state: str = None, db: Session = Depends(get_db)
):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")

    if not state:
        raise HTTPException(status_code=400, detail="State parameter not provided")

    oauth_state = crud.get_oauth_state(db, state)
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    crud.delete_oauth_state(db, state)

    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    token_url = "https://github.com/login/oauth/access_token"

    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/auth/github/callback"

    token_data = {
        "client_id": settings.github_client_id,
        "client_secret": settings.github_client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url, data=token_data, headers={"Accept": "application/json"}
        )
        token_json = response.json()

    if "access_token" not in token_json:
        raise HTTPException(status_code=400, detail="Failed to obtain access token")

    access_token = token_json["access_token"]

    user_info_url = "https://api.github.com/user"
    headers = {"Authorization": f"token {access_token}"}

    async with httpx.AsyncClient() as client:
        user_response = await client.get(user_info_url, headers=headers)
        user_info = user_response.json()

    github_id = str(user_info["id"])
    github_username = user_info["login"]

    user = crud.get_user_by_github_id(db, github_id)
    if user:
        crud.update_user_token(db, user.id, access_token)
    else:
        user = crud.create_user(db, github_id, github_username, access_token)

    request.session["github_token"] = access_token
    request.session["user_id"] = user.id

    return RedirectResponse(url="/")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@app.get("/repos")
async def get_user_repos(request: Request):
    github_token = request.session.get("github_token")
    if not github_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    repos_url = "https://api.github.com/user/repos"

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            repos_url, headers=headers, params={"per_page": 100}
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, detail="Failed to fetch repositories"
        )

    repos = response.json()

    repo_list = [
        {
            "name": repo["full_name"],
            "url": repo["html_url"],
            "private": repo["private"],
            "description": repo["description"],
        }
        for repo in repos
    ]

    return JSONResponse(content={"repositories": repo_list})


@app.post("/analyze")
async def analyze_repo(
    request: Request, github_url: str = Form(None), db: Session = Depends(get_db)
):
    github_token = request.session.get("github_token")
    user_id = request.session.get("user_id")

    if not github_url:
        raise HTTPException(status_code=400, detail="Repository URL must be provided")

    job_id = str(uuid.uuid4())

    repo_name_extracted = extract_repo_name(github_url)
    unique_name = f"{repo_name_extracted}_{job_id[:8]}"

    os.makedirs(TMP_BASE_DIR, exist_ok=True)
    tmp_folder = os.path.join(TMP_BASE_DIR, unique_name)
    os.makedirs(tmp_folder, exist_ok=True)

    results_folder = settings.reports_dir
    os.makedirs(results_folder, exist_ok=True)

    try:
        clone_command = ["git", "clone", "--depth", "1"]

        if github_token and github_url.startswith("https://github.com/"):
            auth_repo_url = github_url.replace(
                "https://github.com/",
                f"https://x-access-token:{github_token}@github.com/",
            )
            clone_command.extend([auth_repo_url, tmp_folder])
        else:
            clone_command.extend([github_url, tmp_folder])

        subprocess.run(
            clone_command, check=True, capture_output=True, text=True, timeout=300
        )

        report_content = run_linters(tmp_folder)

        # Generate LLM summary and add it to the report
        try:
            llm_summary = generate_llm_summary(report_content)
            report_content += f"\n\n## LLM Summary\n\n{llm_summary}\n"
        except Exception as e:
            print(f"Error generating LLM summary: {e}")
            report_content += (
                f"\n\n## LLM Summary\n\nError generating summary: {str(e)}\n"
            )

        chat_system = CodebaseChat(codebase_path=tmp_folder)
        if not chat_system.load_existing_index():
            chat_system.initialize()

        report_file_path = os.path.join(results_folder, f"{unique_name}.md")
        with open(report_file_path, "w") as f:
            f.write(report_content)

        job = crud.create_job(
            db,
            job_id,
            github_url,
            repo_name_extracted,
            tmp_folder,
            report_file_path,
            user_id,
        )

        full_report_content = f"{report_content}"

        crud.add_report(db, job_id, github_url, full_report_content, user_id)

        # Parse issues and save them to the database
        try:
            from cra.lint_tool.py_linters import has_python
            from cra.lint_tool.js_linters import has_javascript, get_js_issues
            import pathlib
            
            issues = []
            path_obj = pathlib.Path(tmp_folder)
            
            # Get Python issues using existing parsers
            if has_python(path_obj):
                try:
                    py_issues = parse_lint_report(report_content)
                    issues.extend(py_issues)
                except Exception as e:
                    print(f"Error parsing Python issues: {e}")

            if has_javascript(path_obj):
                try:
                    js_issues_list = get_js_issues(tmp_folder)
                    issues.extend(js_issues_list)
                except Exception as e:
                    print(f"Error getting JavaScript issues: {e}")
            
            for issue in issues:
                crud.add_issue(db, job_id, issue)
        except Exception as e:
            print(f"Error saving issues to database: {e}")

        return RedirectResponse(url=f"/report/{job_id}", status_code=303)

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Repository cloning timed out")
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to clone repository: {e.stderr}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/report/{job_id}", response_class=HTMLResponse)
async def report_page(request: Request, job_id: str, db: Session = Depends(get_db)):
    # Get user ID from session if available
    user_id = request.session.get("user_id")

    # Retrieve job with access control
    job = crud.get_job(db, job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or access denied")

    # Read report content from file (this contains both report and LLM summary)
    try:
        with open(job.report_path, "r") as f:
            report_content = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report file not found")

    # Extract LLM summary from the report content
    llm_summary = ""
    lint_report_content = report_content

    # Check if LLM Summary section exists
    if "## LLM Summary" in report_content:
        parts = report_content.split("## LLM Summary")
        lint_report_content = parts[0].strip()
        llm_summary = "## LLM Summary" + parts[1] if len(parts) > 1 else ""

        # Get issues from database instead of parsing them every time
        db_issues = crud.get_issues_by_job_id(db, job_id)
        issues = []
        for db_issue in db_issues:
            issue = Issue(
                file=db_issue.file,
                line=db_issue.line,
                severity=db_issue.severity,
                rule=db_issue.rule,
                description=db_issue.description,
                fix=db_issue.fix
            )
            issues.append(issue)

        total_issues = len(issues)

    # Calculate severity and language distribution
    severity_counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        if issue.severity in severity_counts:
            severity_counts[issue.severity] += 1

    language_split = {"python": 0, "javascript": 0, "other": 0}
    if issues:
        python_files = sum(1 for issue in issues if issue.file.endswith(".py"))
        js_files = sum(1 for issue in issues if issue.file.endswith((".js", ".jsx")))
        language_split = {
            "python": python_files,
            "javascript": js_files,
            "other": len(issues) - python_files - js_files,
        }

    unique_files = list(set(issue.file for issue in issues))

    # Convert markdown reports to HTML
    lint_report_html = markdown_to_html(lint_report_content)
    llm_summary_html = markdown_to_html(llm_summary) if llm_summary else ""

    # Get chat history
    chat_history = crud.get_chat_history(db, job_id)

    return templates.TemplateResponse(
        "report.html",
        {
            "request": request,
            "job_id": job_id,
            "report_content": report_content,
            "report_html": markdown_to_html(report_content),
            "lint_report_content": lint_report_content,
            "lint_report_html": lint_report_html,
            "llm_summary": llm_summary,
            "llm_summary_html": llm_summary_html,
            "total_issues": total_issues,
            "severity_counts": severity_counts,
            "language_split": language_split,
            "issues": issues,
            "unique_files": unique_files,
            "chat_history": chat_history,
        },
    )


@app.post("/chat/{job_id}")
async def chat_endpoint(
    request: Request,
    job_id: str,
    question: str = Form(...),
    db: Session = Depends(get_db),
):
    # Get user ID from session if available
    user_id = request.session.get("user_id")

    # Retrieve job with access control
    job = crud.get_job(db, job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or access denied")

    # Save user question to chat history
    crud.add_chat_message(db, job_id, "user", question)

    # Initialize chat system for conversational AI
    chat_system = CodebaseChat(codebase_path=job.folder_path)
    if not chat_system.load_existing_index():
        chat_system.initialize()

    # Restore conversation history from database (excluding the current question)
    chat_history = crud.get_chat_history(db, job_id)
    for message in chat_history[:-1]:  # Exclude the current question we just added
        if message.role == "user":
            chat_system.chat_history.add_message(HumanMessage(content=message.content))
        elif message.role == "assistant":
            chat_system.chat_history.add_message(AIMessage(content=message.content))

    answer = chat_system.ask(question)

    # Save AI response to chat history
    crud.add_chat_message(db, job_id, "assistant", answer)

    # Convert markdown in answer to HTML
    answer_html = markdown_to_html(answer)

    return JSONResponse(content={"answer": answer, "answer_html": answer_html})


@app.get("/ping")
async def ping():
    return {"msg": "pong"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
