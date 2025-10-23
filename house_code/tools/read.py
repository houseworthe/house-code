"""
Read tool implementation.

Based on introspection:
- I use Read constantly to view file contents
- I ALWAYS read before editing
- I prefer Read over bash cat because it has line numbers
- It handles images/PDFs (though simplified here)
"""

from pathlib import Path
from typing import Optional


def create_read_tool_definition() -> dict:
    """Tool definition for Claude API."""
    return {
        "name": "Read",
        "description": """Reads a file from the local filesystem.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to 2000 lines starting from the beginning
- You can optionally specify a line offset and limit for long files
- Results are returned using cat -n format, with line numbers starting at 1
- Any lines longer than 2000 characters will be truncated""",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "The line number to start reading from. Only provide if the file is too large to read at once",
                },
                "limit": {
                    "type": "integer",
                    "description": "The number of lines to read. Only provide if the file is too large to read at once",
                },
            },
            "required": ["file_path"],
        },
    }


def execute_read(
    file_path: str,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> str:
    """
    Execute the Read tool.

    Based on introspection: I read files constantly, always before editing.
    Format output like `cat -n` with line numbers.
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return f"Error: File not found: {file_path}"

        if not path.is_file():
            return f"Error: Path is not a file: {file_path}"

        # Read file
        try:
            content = path.read_text()
        except UnicodeDecodeError:
            return f"Error: File is binary or not UTF-8 encoded: {file_path}"

        # Split into lines
        lines = content.splitlines()

        # Apply offset and limit
        start = offset - 1 if offset else 0
        end = start + limit if limit else len(lines)

        # Default limit if not specified
        if offset is None and limit is None:
            end = min(len(lines), 2000)

        # Format with line numbers (like cat -n)
        result_lines = []
        for i in range(start, min(end, len(lines))):
            line = lines[i]
            # Truncate long lines
            if len(line) > 2000:
                line = line[:2000] + "..."
            result_lines.append(f"{i+1}\u2192{line}")

        result = "\n".join(result_lines)

        # Add info about truncation if needed
        if end < len(lines):
            result += f"\n\n[... {len(lines) - end} more lines not shown ...]"

        return result

    except Exception as e:
        return f"Error reading file: {e}"
