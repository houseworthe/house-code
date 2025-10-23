"""
Write tool implementation.

Based on introspection:
- I use Write to create NEW files
- I prefer Edit for existing files
- Safety: Check if file exists, warn user
"""

from pathlib import Path
from typing import Dict


def create_write_tool_definition() -> Dict:
    """Tool definition for Claude API."""
    return {
        "name": "Write",
        "description": """Writes a file to the local filesystem.

Usage:
- This tool will overwrite the existing file if there is one at the provided path.
- ALWAYS prefer editing existing files. NEVER write new files unless explicitly required.
- Only use for creating genuinely new files.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to write (must be absolute, not relative)",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        },
    }


def execute_write(file_path: str, content: str) -> str:
    """
    Execute the Write tool.

    Based on introspection: I write files but prefer Edit for existing files.
    """
    try:
        path = Path(file_path)

        # Safety check: warn if file exists
        existed = path.exists()

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        path.write_text(content)

        if existed:
            return f"File overwritten successfully at: {file_path}"
        else:
            return f"File created successfully at: {file_path}"

    except Exception as e:
        return f"Error writing file: {e}"
