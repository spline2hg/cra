import os
import pathlib
from cra.config import settings
import click

from cra.chat import CodebaseChat
from cra.lint_tool.main import run_linters, save_report
from cra.llm_diff import generate_and_display_llm_diff
from cra.llm_report import generate_llm_summary
from cra.utils import build_report_name, gc_reports, update_latest_report


@click.group()
def cli():
    """CRA"""
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("-o", "--output", default=None, help="Output markdown file path")
@click.option("--llm-summary", is_flag=True, default=True, help="Generate LLM summary")
@click.option(
    "--diff",
    is_flag=True,
    default=False,
    help="Generate LLM-powered diff recommendations for major refactoring",
)
def analyze(path, output, llm_summary, diff):
    """Generate comprehensive code quality report for specified file or directory."""
    abs_path = os.path.abspath(path)
    path_obj = pathlib.Path(abs_path)

    if output is None:
        settings.reports_dir_path.mkdir(exist_ok=True)
        file_name = build_report_name(abs_path)
        output = str(settings.reports_dir_path / file_name)

    click.echo(f"Running linters on: {abs_path}")

    report_content = run_linters(abs_path)

    if llm_summary:
        click.echo("Generating LLM summary...")
        summary = generate_llm_summary(report_content)
        header_end = report_content.find("\n\n## ")
        if header_end == -1:
            header_end = report_content.find("\n---")
        if header_end == -1:
            header_end = len(report_content)
        
        header_part = report_content[:header_end]
        content_part = report_content[header_end:]
        
        report_content = header_part + f"\n\n## LLM Summary\n\n{summary}\n\n---\n" + content_part

    save_report(report_content, output)

    update_latest_report(pathlib.Path(output))
    gc_reports()

    # Generate and display LLM diff recommendations if requested
    if diff:
        click.echo("\n" + "=" * 50)
        click.echo("Recommendations")
        click.echo("=" * 50)
        generate_and_display_llm_diff(report_content, abs_path)

    click.echo(f"\nReport saved to: {output}")


@cli.command()
@click.argument("codebase_path", type=click.Path(exists=True), default=".")
@click.option("-q", "--question", help="Question to ask about the codebase")
@click.option("--reindex", is_flag=True, help="Force re-indexing of the codebase")
@click.option("--clear-history", is_flag=True, help="Clear conversation history")
def chat(codebase_path, question, reindex, clear_history):
    """Chat with your codebase using AI."""
    chat_system = CodebaseChat(codebase_path=codebase_path)

    if reindex:
        click.echo("Re-indexing codebase...")
        try:
            chat_system.initialize()
        except RuntimeError as e:
            if "quota" in str(e).lower():
                click.echo(f"Error: {e}")
                return
            else:
                raise
    else:
        # click.echo(f"Checking for existing index at: {chat_system.persist_dir}")
        if not chat_system.load_existing_index():
            # click.echo("No existing index found. Creating new index...")
            try:
                chat_system.initialize()
            except RuntimeError as e:
                if "quota" in str(e).lower():
                    click.echo(f"Error: {e}")
                    return
                else:
                    raise

    # Clear history if requested
    if clear_history:
        chat_system.clear_conversation_history()
        click.echo("Conversation history cleared.")

    # Start interactive chat mode
    click.echo("Interactive chat mode. Type 'quit' to exit.")

    # If initial question provided, answer it first
    if question:
        answer = chat_system.ask(question)
        click.echo("Answer:")
        click.echo(answer)
        click.echo()  # For blank line

    # Continue with interactive loop
    while True:
        try:
            user_question = click.prompt("Ask a question about the codebase")
            if user_question.lower() in ["quit", "exit", "q"]:
                break
            answer = chat_system.ask(user_question)
            click.echo("Answer:")
            click.echo(answer)
            click.echo()  # Add blank line for readability
        except (KeyboardInterrupt, EOFError):
            click.echo("\nGoodbye!")
            break


def main():
    cli()


if __name__ == "__main__":
    main()
