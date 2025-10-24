"""
Test Phase 3: Tool system functionality

Tests each tool to ensure it works correctly.
"""

import os
import tempfile
from pathlib import Path

from house_code.tools.read import execute_read
from house_code.tools.write import execute_write
from house_code.tools.edit import execute_edit
from house_code.tools.bash import execute_bash
from house_code.tools.grep import execute_grep
from house_code.tools.glob import execute_glob
from house_code.tools.todowrite import execute_todowrite


def test_write_tool():
    """Test Write tool creates files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        result = execute_write(file_path, "Hello, World!")
        assert "created successfully" in result
        assert Path(file_path).exists()
        assert Path(file_path).read_text() == "Hello, World!"
    print("✅ Write tool works!")


def test_read_tool():
    """Test Read tool reads files with line numbers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        Path(file_path).write_text("Line 1\nLine 2\nLine 3")

        result = execute_read(file_path)
        assert "1→Line 1" in result
        assert "2→Line 2" in result
        assert "3→Line 3" in result
    print("✅ Read tool works!")


def test_edit_tool():
    """Test Edit tool modifies files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        Path(file_path).write_text("Hello, World!")

        result = execute_edit(file_path, "World", "House Code")
        assert "Successfully edited" in result
        assert Path(file_path).read_text() == "Hello, House Code!"
    print("✅ Edit tool works!")


def test_bash_tool():
    """Test Bash tool executes commands."""
    result = execute_bash("echo 'test'")
    assert "test" in result
    print("✅ Bash tool works!")


def test_grep_tool():
    """Test Grep tool finds patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        file1 = os.path.join(tmpdir, "test1.txt")
        file2 = os.path.join(tmpdir, "test2.txt")
        Path(file1).write_text("This has the word ERROR in it")
        Path(file2).write_text("This is fine")

        result = execute_grep("ERROR", path=tmpdir)
        assert "test1.txt" in result
        assert "test2.txt" not in result
    print("✅ Grep tool works!")


def test_glob_tool():
    """Test Glob tool finds files by pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        Path(os.path.join(tmpdir, "test.py")).write_text("# Python")
        Path(os.path.join(tmpdir, "test.txt")).write_text("Text")
        Path(os.path.join(tmpdir, "test.js")).write_text("// JS")

        result = execute_glob("*.py", path=tmpdir)
        assert "test.py" in result
        assert "test.txt" not in result
        assert "test.js" not in result
    print("✅ Glob tool works!")


def test_todowrite_tool():
    """Test TodoWrite tool tracks tasks."""
    todos = [
        {"content": "Task 1", "status": "completed", "activeForm": "Doing task 1"},
        {"content": "Task 2", "status": "in_progress", "activeForm": "Doing task 2"},
        {"content": "Task 3", "status": "pending", "activeForm": "Doing task 3"},
    ]
    result = execute_todowrite(todos)
    assert "1 completed" in result
    assert "1 in progress" in result
    assert "1 pending" in result
    assert "Current task: Doing task 2" in result
    print("✅ TodoWrite tool works!")


if __name__ == "__main__":
    print("Testing Phase 3: Tool System\n")

    test_write_tool()
    test_read_tool()
    test_edit_tool()
    test_bash_tool()
    test_grep_tool()
    test_glob_tool()
    test_todowrite_tool()

    print("\n✅ Phase 3 tool system verified!")
    print("\nAll core tools working:")
    print("  - Read: View file contents with line numbers")
    print("  - Write: Create new files")
    print("  - Edit: Modify existing files with exact text matching")
    print("  - Bash: Execute commands")
    print("  - Grep: Search for patterns across files")
    print("  - Glob: Find files by name pattern")
    print("  - TodoWrite: Plan and track complex tasks")
