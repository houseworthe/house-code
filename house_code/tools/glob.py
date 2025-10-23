"""
Glob tool implementation.

Based on introspection:
- I use Glob to find files by name pattern
- Fast file pattern matching
- Returns sorted file paths
"""

from pathlib import Path
from typing import Optional


def create_glob_tool_definition() -> dict:
    """Tool definition for Claude API."""
    return {
        "name": "Glob",
        "description": """Fast file pattern matching tool.

Usage:
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- Use this when you need to find files by name patterns""",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files against",
                },
                "path": {
                    "type": "string",
                    "description": "The directory to search in (defaults to current directory)",
                },
            },
            "required": ["pattern"],
        },
    }


def execute_glob(pattern: str, path: Optional[str] = None) -> str:
    """
    Execute the Glob tool.

    Based on introspection: I use glob to find files by pattern.
    """
    try:
        # Determine search path
        search_path = Path(path) if path else Path(".")
        if not search_path.exists():
            return f"Error: Path not found: {path}"

        if not search_path.is_dir():
            return f"Error: Path is not a directory: {path}"

        # Find matching files
        matches = list(search_path.glob(pattern))

        # Filter to only files
        files = [m for m in matches if m.is_file()]

        if not files:
            return f"No files found matching pattern: {pattern}"

        # Sort by modification time (most recent first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Format output
        result = "\n".join(str(f) for f in files)

        # Limit output
        if len(files) > 100:
            result = "\n".join(str(f) for f in files[:100])
            result += f"\n\n[... {len(files) - 100} more files not shown ...]"

        return result

    except Exception as e:
        return f"Error executing glob: {e}"
