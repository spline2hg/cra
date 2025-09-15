
# Code Quality Intelligence Agent (CRA: code review agent)

**CRA (Code Review Agent)** is a Python-based CLI tool that automates static code analysis for **Python and JavaScript** projects. It integrates tools like **Pylint, Bandit, ESLint, Radon, Semgrep, Vulture, and jscpd** to scan files or entire directories, generating a structured **Markdown report** with categorized issues (e.g., **security vulnerabilities, code complexity, duplication, dead code, and style problems**).

### **Key Features**:
#### **1. Static Analysis & Reporting**
- Runs **multiple linters/analyzers** on codebases and compiles findings into a **detailed, categorized report**.
- Uses an **LLM** to generate a **high-level summary** of code quality, risks, and trends.

#### **2. Interactive Chat**
- Chat with the **codebase** (RAG-powered with **vector embeddings and semantic search**).
- Ask natural-language questions about the **analysis report** or **codebase history** (e.g., *"Why was this function flagged?"* or *"Show me all security issues in this module"*).

#### **3. Git-Inspired Recommendations**
- Provides **actionable, git diff-style suggestions** for fixes, prioritized by severity.

#### **4. Web UI (Public & Private Repos)**
- **Public Repos**: Generate reports, view **LLM-powered summaries**, and explore **visualizations** of issues.
- **Private Repos**: Secure **GitHub OAuth authentication** for confidential projects.
- **Features**:
  - Filter and navigate issues by **category** (security, complexity, duplication, etc.).
  - Search across the codebase or report.
  - Chat with the **codebase** or **report** directly.


## Setup and Installation

First, ensure you have **Python** and **Node.js** installed.

### 1. Clone the Repository

```bash
git clone https://github.com/spline2hg/cra.git
cd cra
```

### 2. Environment Configuration

Create a `.env` file in the project root by copying the example file:

```bash
cp .env.example .env
```

Now, open the `.env` file and add your API keys. You'll need a **Google API Key** for the chat and summary features.

```ini
# .env
GOOGLE_API_KEY=your_google_api_key_here
LLM_API_KEY=can_be_same_as_google_api_key
# ... other keys if needed
```

### 3. Install Dependencies

You can use either `uv` (recommended for speed) or `pip` for the Python packages.

**First, install Python dependencies:**

*   **Option A (uv):**
    ```bash
    uv pip install -e .
    ```
*   **Option B (pip):**
    ```bash
    pip install -e .
    ```

**Then, install JavaScript dependencies:**
```bash
npm install
```
This installs the project in editable mode and makes the `cra` command available.

## Usage (CLI)

CRA provides a simple command-line interface.

### Generating a Report

To run a full analysis on your code and save a markdown report. The path can point to a single file or an entire directory.

```bash
cra analyze <path-to-your-code>
```

**Options:**

*   `-o, --output <file_path>`: Specify a custom path to save the report file.
*   `--llm-summary`: (Default: True) Appends an AI-generated summary to the report.
*   `--diff`: Generates and displays AI-powered refactoring recommendations for major issues in the console.
Example:
<img width="1242" height="288" alt="image" src="https://github.com/user-attachments/assets/516aac2a-ac95-477b-8dfc-e15283f80c17" />

**Example:**

```bash
# Analyze a project and show AI refactoring suggestions
cra analyze ./my-project --diff
```

### Chatting with Your Codebase

Start an interactive session to ask questions about your code. The path can point to a single file or an entire directory. The first time you run this, it will create an index of your code.

```bash
cra chat <path-to-your-code>
```
The agent maintains your **conversation history** throughout the session, allowing for follow-up questions.

**Special Feature: Ask about the report**
To ask a question specifically about the latest analysis report, include `@report` in your query. This tells the agent to add the report's content to the context.

```
> Can you summarize the findings in the latest report? @report
```

**Options:**

*   `-q, --question <question>`: Ask an initial question without entering interactive mode.
*   `--reindex`: Forces the agent to re-scan and re-index the entire codebase.
*   `--clear-history`: Starts a new conversation, clearing any previous chat history.

## Web Interface

The CRA web interface provides a user-friendly way to analyze GitHub repositories directly from your browser. You can paste in a URL to any **public GitHub repository** to generate a report and start a chat session.

For **private repositories**, you can securely log in with your GitHub account to grant access for analysis.

To run the web server:
```bash
uvicorn cra_web.app:app --reload
```
Open your browser and navigate to **http://127.0.0.1:8000**.

## Tech Stack

This project is built with a modern set of tools and frameworks:

*   **CLI**:
    *   **Click**: A simple and powerful library for creating the command-line interface.
*   **AI & Language Models**:
    *   **LangChain**: The core framework for building the RAG pipeline and managing LLM interactions.
    *   **Google Gemini**: The primary Large Language Model used for summarization and Q&A.
    *   **ChromaDB**: A local vector database for storing code embeddings efficiently.
*   **Backend & Web**:
    *   **FastAPI**: A high-performance Python framework for building the web server and API.
    *   **SQLAlchemy**: Used for database interactions in the web application.
*   **Analysis Tools**:
    *   **Python**: Pylint, Flake8, Bandit, Radon, Vulture.
    *   **JavaScript**: ESLint, Semgrep, jscpd.


## How It Works

1.  **Code Analysis**: The `report` command invokes a set of established static analysis tools (`Pylint`, `Flake8`, `Bandit`, `Radon` for Python; `ESLint`, `Semgrep`, `jscpd` for JavaScript). The outputs are combined into a single markdown report.
2.  **Summarization**: The generated report content is sent to an LLM to produce a high-level summary, identifying critical issues and recurring patterns.
3.  **RAG Pipeline for Q&A**: The `chat` command uses a Retrieval-Augmented Generation (RAG) architecture:
    *   **Loading & Splitting**: The target codebase is scanned, and code/text files are loaded and split into smaller, manageable chunks.
    *   **Embedding & Indexing**: Each chunk is converted into a vector embedding and stored in a local ChromaDB vector store. This index is cached for fast retrieval.
    *   **Retrieval & Generation**: When you ask a question, the agent searches the vector store for the most relevant code chunks. These chunks are then passed to the Gemini LLM as context along with your question to generate a well-informed answer.

## Major User-Facing API

If you want to integrate CRA's functionality into your own tools, here are the main entry points:

*   `cra.lint_tool.main.run_linters(file_path: str) -> str`:
    *   The core analysis function. It takes a file or directory path and returns a complete markdown report as a string.

*   `cra.chat.CodebaseChat(codebase_path: str)`:
    *   The main class for handling the Q&A functionality.
    *   `.initialize()`: Loads, splits, and indexes the documents in the specified path.
    *   `.ask(query: str) -> str`: The primary method for asking questions.

*   `cra.llm_report.generate_llm_summary(report_content: str) -> str`:
    *   Takes the raw markdown report content and returns the AI-generated summary.

### **Why CRA?**
Simplify code reviews with **AI-driven insights**, **actionable recommendations**, and **convenience** whether via **CLI** or **web UI**.
