# Architecture Notes:

This document outlines the high-level architecture, design decisions, and core components of the Code Quality Intelligence Agent (CRA).

### 1. High-Level Overview

The system is designed with a **modular and decoupled architecture**, separating the core analysis logic from the user-facing interfaces. The architecture is built around two primary pillars:

1.  **Core Logic Library (`cra`)**: A self-contained Python package that handles all static analysis, AI integration (summarization and chat), and report generation. It can be used independently.
2.  **Interfaces (CLI & Web)**: Two main ways for a user to interact with the core logic.
    *   **Command-Line Interface (CLI)**: For local development and scripting.
    *   **Web Interface (`cra_web`)**: For a user-friendly, browser-based experience, especially for analyzing GitHub repositories.

The design philosophy emphasizes using powerful, existing tools for their specific tasks (e.g., linters for analysis, LangChain for AI orchestration) and focusing the core logic on integrating them into a cohesive system.

### 2. Core Components

The system is broken down into several key components:

**a. Static Analysis Engine (`cra/lint_tool`)**
*   **Responsibility**: Executes a suite of external static analysis tools for both Python and JavaScript.
*   **Implementation**: It uses Python's `subprocess` module to run tools like Pylint, Bandit, ESLint, and Semgrep. It includes helper functions to detect the language of a given path (`has_python`, `has_javascript`) to ensure only relevant analyzers are run.
*   **Output**: Produces raw text output from each linter.

**b. Report Unification Layer (`cra/lint_tool/main.py`)**
*   **Responsibility**: Gathers the raw output from all the linters and compiles them into a single, well-formatted Markdown report.
*   **Implementation**: It structures the report with clear headings for each tool, making the raw data readable and organized.

**c. AI Integration Layer (`cra/chat.py`, `cra/llm_report.py`)**
This component contains the "intelligence" of the agent and is split into two parts:

*   **LLM Summarization**: Takes the unified Markdown report as input and uses a Large Language Model (Google Gemini) to generate a concise, human-readable summary of the key findings.
*   **Interactive Q&A (RAG Pipeline)**: This is the heart of the `chat` feature. It uses a Retrieval-Augmented Generation (RAG) architecture orchestrated by **LangChain**.
    *   **Indexing**: Code files are loaded, split into meaningful chunks (aware of code syntax), and converted into vector embeddings.
    *   **Storage**: These embeddings are stored in a local **ChromaDB** vector store for efficient similarity searches.
    *   **Retrieval**: When a user asks a question, the system retrieves the most relevant code chunks from ChromaDB.
    *   **Generation**: The retrieved chunks are passed to the Gemini LLM as context along with the user's question to generate an informed answer.

**d. Command-Line Interface (CLI) (`cra/main.py`)**
*   **Responsibility**: Provides the user entry point from the terminal.
*   **Implementation**: Built using the **Click** library. It exposes the `analyze` and `chat` commands and handles user arguments, passing them to the core logic.

**e. Web Interface (`cra_web`)**
*   **Responsibility**: Provides a web-based UI for analyzing GitHub repositories and interacting with the agent.
*   **Implementation**: A **FastAPI** backend serves a **Jinja2**-templated frontend. It handles GitHub OAuth for private repositories, clones the repo into a temporary directory, runs the core analysis logic, and serves the report and a chat interface.

### 3. Key Workflows & Data Flow (Diagram Descriptions)

Here’s how the components interact in the two main use cases.

**a. Report Generation Workflow**

1.  **User Input**: The user runs `cra report <path>`.
2.  **CLI**: The Click interface parses the command and arguments.
3.  **Static Analysis Engine**: The `run_linters` function is called. It detects the language(s) at the path and runs the appropriate set of linters (Pylint, ESLint, etc.) as separate subprocesses.
4.  **Report Unification**: The raw text outputs from each linter are collected and formatted into a single Markdown string.
5.  **LLM Summary (Optional)**: The Markdown string is sent to the Gemini API, which returns a summary. The summary is appended to the report.
6.  **Output**: The final report is saved to a `.md` file on the disk.
<p align="center">
<img width="500" height="500" alt="report_workflow" src="https://github.com/user-attachments/assets/add72905-8119-4534-892c-ba39b9475d5a" />
</p>

**b. Interactive Chat (RAG) Workflow**

**Part 1: Indexing (First time running `chat` on a new project)**
1.  **User Input**: User runs `cra chat <path>`.
2.  **CodebaseChat Initialization**: The system checks if an index exists for this path. If not:
3.  **Load & Split**: It scans the directory, loads all supported code and text files, and uses LangChain's splitters to break them into small, overlapping chunks.
4.  **Embed & Store**: Each chunk is passed to an embedding model, and the resulting vector is stored in a local ChromaDB database, creating a searchable index.

**Part 2: Querying**
1.  **User Question**: The user types a question into the interactive prompt.
2.  **Retrieve**: The question is embedded, and ChromaDB is searched to find the most semantically similar code chunks (the "context").
3.  **Generate**: A prompt containing the original question and the retrieved context is sent to the Gemini LLM.
4.  **Response**: The LLM generates an answer based on the provided context, which is then displayed to the user. The conversation history is updated.

<p align="center">
<img width="500" height="800" alt="chatt_workflow" src="https://github.com/user-attachments/assets/176223cc-bdf3-4821-b60b-1e45a108cc6a" />
</p>
### 4. Major Design Decisions & Trade-offs

*   **Retrieval-Augmented Generation (RAG) for Code Q&A**
    *   **Decision**: We used a RAG pipeline instead of just feeding entire files into an LLM's context window.
    *   **Reasoning**: RAG is far more scalable for large codebases. It allows the system to analyze repositories of any size by only retrieving and focusing on the most relevant code snippets. For this to be effective, we use **code-based chunking**, where the document splitters are language-aware and try to keep related code blocks (like functions or classes) together.
    *   **note**: The indexing doesnt seem to work very well for our coding task and doesnt always give appropriate context.

*   **Decoupled Core Logic and Interfaces**
    *   **Decision**: The `cra` logic is a standalone package, separate from the `cra_web` application.
    *   **Reasoning**: This separation of concerns makes the system much easier to maintain, test, and extend. The core analysis engine could be imported into a CI/CD pipeline, a different UI, or another tool without modification.
    *   **Trade-off**: Requires careful management of dependencies and clear API boundaries between the core library and the applications that consume it.

*   **OpenAI Compatibility for LLM Summaries**
    *   **Decision**: For the report summarization feature, we designed the LLM interaction to be compatible with any OpenAI-compliant API endpoint, not just a single provider.
    *   **Reasoning**: This provides flexibility. Users can switch between different model providers (like Google Gemini, OpenAI, or self-hosted models) by simply changing the base URL and API key in their `.env` file. This avoids vendor lock-in and allows users to leverage the best model for their needs.
