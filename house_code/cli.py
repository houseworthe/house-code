"""
CLI interface for House Code.

Provides the command-line interface for interacting with House Code.
"""

import os
import sys
import click
from pathlib import Path

from .core import HouseCode


@click.command()
@click.option(
    "--api-key",
    envvar="ANTHROPIC_API_KEY",
    required=True,
    help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
)
@click.option(
    "--model",
    default="claude-sonnet-4-20250514",
    help="Claude model to use",
)
@click.option(
    "--working-dir",
    default=".",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Working directory for file operations",
)
@click.option(
    "--max-iterations",
    default=50,
    type=int,
    help="Maximum iterations per request",
)
@click.argument("prompt", required=False)
def main(api_key: str, model: str, working_dir: str, max_iterations: int, prompt: str):
    """
    House Code - Introspective AI Coding Assistant

    Run in interactive mode:
        house

    Run with a single prompt:
        house "create a hello world Python script"
    """
    # Initialize House Code
    agent = HouseCode(
        api_key=api_key,
        model=model,
        working_directory=working_dir,
        max_iterations=max_iterations,
    )

    # Change to working directory
    os.chdir(working_dir)

    # Import and register tools (Phase 3 will implement these)
    try:
        from .tools.registry import register_all_tools
        register_all_tools(agent)
    except ImportError:
        # Tools not yet implemented
        pass

    # Single prompt mode
    if prompt:
        response = agent.run(prompt)
        print(response)
        return

    # Interactive mode
    agent.interactive_loop()


if __name__ == "__main__":
    main()
