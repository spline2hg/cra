from openai import OpenAI

from cra.config import settings


def generate_llm_summary(report_content: str) -> str:
    """Generate LLM summary of report."""
    if not settings.llm_base_url:
        raise ValueError("LLM_BASE_URL not configured")

    if not settings.llm_api_key:
        raise ValueError("LLM_API_KEY not configured")

    client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

    prompt = f"""Analyze this Python linting report and provide a clear, concise summary.

Focus on:
1. Critical issues requiring immediate attention
2. Recurring patterns of issues
3. Overall code quality assessment
4. Actionable recommendations for improvement

Linting Report:
{report_content}

Provide only the summary content as output."""

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert software engineer and code quality reviewer with deep knowledge of Python, JavaScript, security best practices, and software engineering principles.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        summary = response.choices[0].message.content
        return summary.strip() if summary else "No summary generated."

    except Exception as e:
        return f"Error generating LLM summary: {str(e)}"
