"""
Grep tool implementation.

Based on introspection:
- I use Grep to search for code patterns across files
- Supports regex patterns
- Multiple output modes (files_with_matches, content, count)
- Glob filtering for file types
"""

import re
from pathlib import Path
from typing import Optional, List


def create_grep_tool_definition() -> dict:
    """Tool definition for Claude API."""
    return {
        "name": "Grep",
        "description": """A powerful search tool for finding patterns in files.

Usage:
- ALWAYS use Grep for search tasks. NEVER invoke grep or rg as Bash command.
- Supports full regex syntax (e.g., "log.*Error", "function\\s+\\w+")
- Filter files with glob parameter (e.g., "*.js", "**/*.tsx")
- Output modes: "content" shows matching lines, "files_with_matches" shows only file paths (default), "count" shows match counts""",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regular expression pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search in (defaults to current directory)",
                },
                "glob": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g. \"*.js\", \"*.{ts,tsx}\")",
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["content", "files_with_matches", "count"],
                    "description": "Output mode (defaults to files_with_matches)",
                },
                "i": {
                    "type": "boolean",
                    "description": "Case insensitive search",
                },
            },
            "required": ["pattern"],
        },
    }


def execute_grep(
    pattern: str,
    path: Optional[str] = None,
    glob: Optional[str] = None,
    output_mode: str = "files_with_matches",
    i: bool = False,
) -> str:
    """
    Execute the Grep tool.

    Based on introspection: I use grep to find patterns across files.
    """
    try:
        # Compile regex
        flags = re.IGNORECASE if i else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"

        # Determine search path
        search_path = Path(path) if path else Path(".")
        if not search_path.exists():
            return f"Error: Path not found: {path}"

        # Find files to search
        if search_path.is_file():
            files = [search_path]
        else:
            # Use glob to filter if provided
            if glob:
                files = list(search_path.glob(glob))
            else:
                files = list(search_path.rglob("*"))

            # Only keep files
            files = [f for f in files if f.is_file()]

        results = []
        total_matches = 0

        # Search each file
        for file in files:
            try:
                content = file.read_text()
            except (UnicodeDecodeError, PermissionError):
                continue  # Skip binary/unreadable files

            matches = list(regex.finditer(content))
            if not matches:
                continue

            total_matches += len(matches)

            if output_mode == "files_with_matches":
                results.append(str(file))
            elif output_mode == "count":
                results.append(f"{file}: {len(matches)}")
            elif output_mode == "content":
                lines = content.splitlines()
                for match in matches:
                    # Find line number
                    line_no = content[:match.start()].count('\n') + 1
                    if line_no <= len(lines):
                        results.append(f"{file}:{line_no}:{lines[line_no-1]}")

        if not results:
            return f"No matches found for pattern: {pattern}"

        # Limit output
        if len(results) > 100:
            results = results[:100]
            results.append(f"\n[... {len(results) - 100} more results not shown ...]")

        return "\n".join(results)

    except Exception as e:
        return f"Error executing grep: {e}"
