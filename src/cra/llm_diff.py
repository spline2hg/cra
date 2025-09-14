import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from rich.console import Console

from cra.config import settings
from cra.dtos import DiffRecommendations


def get_file_content(file_path: str) -> str:
    """Get the content of a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def generate_llm_diff_recommendations(
    report: str, file_path: str
) -> DiffRecommendations:
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError(
            "GOOGLE_API_KEY environment variable not set. Cannot generate LLM recommendations."
        )

    # Get the actual file content
    file_content = get_file_content(file_path)

    # Create the prompt template focused on major refactoring
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an expert Python refactoring specialist focused on major structural improvements.

        IMPORTANT: Only provide recommendations for significant issues that require structural changes or pose security/maintainability risks.

        IGNORE minor style issues like:
        - Trailing whitespace, indentation, spacing
        - Line length issues (unless they severely impact readability)
        - Missing newlines, quote style preferences
        - Minor naming convention violations

        FOCUS ON major issues like:
        - Security vulnerabilities (bandit warnings)
        - High complexity functions that need decomposition
        - Design pattern violations requiring structural changes
        - Dead code that impacts maintainability
        - Exception handling that needs improvement
        - Import organization that affects code structure

        Guidelines:
        1. Prioritize: Security > Complexity > Design > Dead Code
        2. Provide exact before/after code with line numbers
        3. Explain WHY the change improves code structure/security
        4. Suggest refactoring patterns when appropriate
        5. Only recommend changes that significantly improve code quality
        """,
            ),
            (
                "user",
                """Analyze this report for MAJOR refactoring opportunities only. Ignore minor style issues.

        Report:
        {report}

        Source Code File: {file_path}
        ```python
        {file_content}
        ```

        Provide structured recommendations ONLY for significant structural improvements, security fixes, or complexity reduction.""",
            ),
        ]
    )

    try:
        # Initialize Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model, temperature=0.1, max_tokens=4000
        )

        # Create the chain with structured output
        chain = prompt | llm.with_structured_output(DiffRecommendations)

        # Generate recommendations
        result = chain.invoke(
            {
                "report": report,
                "file_path": file_path,
                "file_content": file_content,
            }
        )

        # Ensure we return a valid DiffRecommendations object
        if isinstance(result, DiffRecommendations):
            return result
        else:
            # Fallback if LLM returns unexpected format
            return DiffRecommendations(
                summary="LLM returned unexpected format, using fallback",
                changes=[],
                priority_order=[],
            )
    except Exception as e:
        return DiffRecommendations(
            summary=f"Error generating recommendations: {str(e)}",
            changes=[],
            priority_order=[],
        )


def display_simple_diff_recommendations(recommendations: DiffRecommendations):
    """Display LLM recommendations in a simple, clean format."""
    console = Console()

    if not recommendations.changes:
        console.print("[dim]No specific recommendations generated[/dim]")
        return

    console.print(f"[bold green]Summary:[/bold green] {recommendations.summary}")
    console.print()

    console.print("[bold cyan]Recommended Changes:[/bold cyan]")
    console.print("-" * 50)

    for i, change in enumerate(recommendations.changes, 1):
        console.print(
            f"\n[bold]{i}. {change.issue_type.upper()} - Line {change.line_number}[/bold]"
        )
        console.print(f"[yellow]Reason:[/yellow] {change.reason}")
        console.print(f"[red]- {change.original_code}[/red]")
        console.print(f"[green]+ {change.recommended_code}[/green]")


def generate_and_display_llm_diff(report: str, file_path: str):
    """Generate and display LLM diff recommendations only for major refactoring scenarios."""
    console = Console()

    try:
        # Generate recommendations using Gemini
        recommendations = generate_llm_diff_recommendations(report, file_path)

        # Ensure we have a valid recommendations object
        if recommendations is None:
            recommendations = DiffRecommendations(
                summary="Failed to generate recommendations",
                changes=[],
                priority_order=[],
            )

        # Display recommendations
        display_simple_diff_recommendations(recommendations)

        return recommendations

    except Exception as e:
        console.print(f"[red]Error generating LLM diff recommendations: {str(e)}[/red]")
        fallback_recommendations = DiffRecommendations(
            summary=f"Error: {str(e)}", changes=[], priority_order=[]
        )
        return fallback_recommendations
