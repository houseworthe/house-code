"""
Edit tool implementation.

Based on introspection:
- I prefer Edit over Write for existing files
- I ALWAYS Read before Edit (need exact text for matching)
- Uses exact string replacement - safer than line numbers
- Fails if old_string is not unique (unless replace_all=True)
"""

from pathlib import Path


def create_edit_tool_definition() -> dict:
    """Tool definition for Claude API."""
    return {
        "name": "Edit",
        "description": """Performs exact string replacements in files.

Usage:
- You must use Read tool before editing to see exact content
- The edit will FAIL if `old_string` is not unique in the file
- Either provide larger string with more context to make it unique, or use `replace_all` to change every instance
- Use `replace_all` for replacing and renaming strings across the file""",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to modify",
                },
                "old_string": {
                    "type": "string",
                    "description": "The text to replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "The text to replace it with (must be different from old_string)",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences of old_string (default false)",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        },
    }


def execute_edit(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> str:
    """
    Execute the Edit tool.

    Based on introspection: I use Edit with exact text matching, always after Read.
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return f"Error: File not found: {file_path}"

        if not path.is_file():
            return f"Error: Path is not a file: {file_path}"

        # Read current content
        try:
            content = path.read_text()
        except UnicodeDecodeError:
            return f"Error: File is binary or not UTF-8 encoded: {file_path}"

        # Check if old_string exists
        if old_string not in content:
            return f"Error: old_string not found in file. Make sure you Read the file first to get exact text."

        # Check if old_string is unique (unless replace_all)
        if not replace_all and content.count(old_string) > 1:
            count = content.count(old_string)
            return f"Error: old_string appears {count} times in file. Provide more context to make it unique, or use replace_all=true."

        # Perform replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
            count = content.count(old_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
            count = 1

        # Write back
        path.write_text(new_content)

        if replace_all:
            return f"Successfully replaced {count} occurrence(s) in {file_path}"
        else:
            return f"Successfully edited {file_path}"

    except Exception as e:
        return f"Error editing file: {e}"
