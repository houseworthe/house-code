"""
Bash tool implementation.

Based on introspection:
- I use Bash for git operations, running tests, commands
- I prefer specialized tools (Read, Grep) over bash equivalents
- Safety: timeout for long-running commands
- Capture stdout and stderr
"""

import subprocess
import shlex
from typing import Optional


def create_bash_tool_definition() -> dict:
    """Tool definition for Claude API."""
    return {
        "name": "Bash",
        "description": """Executes a bash command with optional timeout.

IMPORTANT: This tool is for terminal operations like git, npm, docker, etc.
DO NOT use it for file operations (reading, writing, editing, searching) - use specialized tools instead.

Usage:
- Always quote file paths that contain spaces with double quotes
- Default timeout is 120 seconds (2 minutes)
- Avoid using bash for file operations - use Read, Write, Edit, Grep, Glob instead""",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Optional timeout in milliseconds (max 600000 / 10 minutes)",
                },
            },
            "required": ["command"],
        },
    }


def execute_bash(command: str, timeout: Optional[int] = None) -> str:
    """
    Execute the Bash tool.

    Based on introspection: I use bash for commands, not file operations.
    """
    try:
        # Convert timeout from milliseconds to seconds
        timeout_secs = (timeout / 1000) if timeout else 120

        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_secs,
            cwd=".",
        )

        # Format output
        output = []

        if result.stdout:
            output.append(result.stdout)

        if result.stderr:
            output.append(f"[stderr]\n{result.stderr}")

        if result.returncode != 0:
            output.append(f"[exit code: {result.returncode}]")

        return "\n".join(output) if output else "[No output]"

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout_secs} seconds"
    except Exception as e:
        return f"Error executing command: {e}"
