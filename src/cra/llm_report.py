from openai import OpenAI
from cra.config import settings

def generate_llm_summary(report_content: str) -> str:
    """Generate an enhanced, developer-focused code quality summary."""
    if not settings.llm_base_url:
        raise ValueError("LLM_BASE_URL not configured")

    if not settings.llm_api_key:
        raise ValueError("LLM_API_KEY not configured")

    client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

    # Enhanced, detailed prompt aligned with the project description
    prompt = f"""
As a Code Quality Intelligence Agent, your task is to analyze the provided static analysis and linting report. Transform this raw data into a human-readable, actionable, and developer-friendly intelligence report.

Your output must be structured, insightful, and prioritize clarity for a software development audience. Follow the markdown structure below precisely.

**Linting and Static Analysis Report:**

{report_content}


**Your Generated Intelligence Report:**

# 📈 Code Quality Intelligence Report

## 🚦 Executive Summary: Quick Action List
This section is for busy developers. Immediately highlight the most critical issues that require urgent attention. Use a markdown table.

| Severity | File & Line Number(s) | Recommendation |
|----------|-----------------------|----------------|
| 🔴 **Critical** | `example/path.py:42` | Brief, direct fix description. |
| 🟡 **High**     | `another/file.js:101` | Brief, direct fix description. |

*This is a summary of the most pressing issues. Full details are provided below.*

---

## 🛠️ Actionable Recommendations & Fixes
Provide a prioritized list of issues. For each issue, you must:
1.  **Explain the "Why":** Clearly describe the problem and its potential impact (e.g., security risk, performance bottleneck, maintainability issue).
2.  **Show the "How":** Provide clear, concise code snippets demonstrating the fix. Use "Before" and "After" blocks.
3.  **Categorize the Issue:** Label each finding (e.g., Security, Performance, Code Smell, Complexity).

### 🔴 Critical Issues
*(Issues that could lead to security breaches, data loss, or system failure)*

**1. [Issue Title - e.g., SQL Injection Vulnerability]**
- **File:** `user_manager.py:101`
- **Category:** Security
- **Impact:** This vulnerability allows attackers to execute arbitrary SQL queries, potentially leading to unauthorized data access or modification.
- **Fix Example:**
  **Before**
  ```python
  query = f"SELECT * FROM users WHERE username = '{'user_input'}'"

    **after**
# Use parameterized queries to prevent injection
query = "SELECT * FROM users WHERE username = %s"
cursor.execute(query, (user_input,))
🟡 High-Priority Issues

(Issues that significantly impact performance, introduce major bugs, or degrade maintainability)

1. [Issue Title - e.g., Inefficient Loop causing N+1 Problem]

File: api/handlers.py:55

Category: Performance

Impact: The current implementation makes a separate database call for each item in the list, leading to poor performance as the dataset grows.

Fix Example:
(Provide relevant Before/After snippets)

(Continue for Medium and Low priority issues if present in the report)

📊 Overall Code Quality Assessment
Complexity Analysis

Summarize the code's complexity based on the report. If possible, create a "heat-map" table.
| Method / Function | File | Complexity Score | Rating |
|-------------------|------|------------------|--------|
| process_data | data.py | 15 | 🔴 High |
| calculate_total | utils.py| 4 | 🟢 Low |
Scores > 10 are considered high and may require refactoring.

Recurring Patterns & Themes

Identify and describe any recurring issues or anti-patterns found throughout the codebase (e.g., inconsistent error handling, widespread code duplication, lack of docstrings).

General Observations & Strengths

Conclude with a brief, high-level assessment of the codebase's quality. Mention positive aspects if any (e.g., good test coverage, consistent styling).
"""
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI-powered Code Quality Intelligence Agent. Your expertise lies in analyzing code repositories for security vulnerabilities, performance bottlenecks, complexity, and other quality issues. You generate actionable, developer-friendly reports with clear explanations and practical fix suggestions.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,  # Lowered temperature for more consistent, factual output
            max_tokens=3500,  # Increased max_tokens for more comprehensive reports
        )

        summary = response.choices[0].message.content
        return summary.strip() if summary else "No summary generated."

    except Exception as e:
        return f"Error generating LLM summary: {str(e)}"