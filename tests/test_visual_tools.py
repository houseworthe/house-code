"""
Test suite for visual memory tools (Phase 5).

Tests tool definitions, executors, and integration with HouseCode agent.
"""

import os
import unittest
import tempfile
from pathlib import Path

from house_code.core import HouseCode, ConversationContext
from house_code.tools.registry import register_all_tools
from house_code.tools.visual_memory import (
    create_compress_tool_definition,
    execute_compress,
    create_decompress_tool_definition,
    execute_decompress,
    create_stats_tool_definition,
    execute_stats,
)
from house_code.visual import VisualCache, RosieClient, load_config


class TestVisualMemoryToolDefinitions(unittest.TestCase):
    """Test that tool definitions are valid."""

    def test_compress_definition_valid(self):
        """Test compress tool has valid definition."""
        definition = create_compress_tool_definition()

        # Check required fields
        self.assertIn("name", definition)
        self.assertIn("description", definition)
        self.assertIn("input_schema", definition)

        # Check name
        self.assertEqual(definition["name"], "CompressVisualMemory")

        # Check schema structure
        schema = definition["input_schema"]
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)
        self.assertIn("required", schema)

        # Check required parameters
        self.assertIn("text", schema["properties"])
        self.assertIn("message_ids", schema["properties"])
        self.assertEqual(set(schema["required"]), {"text", "message_ids"})

        # Check parameter types
        self.assertEqual(schema["properties"]["text"]["type"], "string")
        self.assertEqual(schema["properties"]["message_ids"]["type"], "array")

    def test_decompress_definition_valid(self):
        """Test decompress tool has valid definition."""
        definition = create_decompress_tool_definition()

        # Check required fields
        self.assertIn("name", definition)
        self.assertIn("description", definition)
        self.assertIn("input_schema", definition)

        # Check name
        self.assertEqual(definition["name"], "DecompressVisualMemory")

        # Check schema structure
        schema = definition["input_schema"]
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)
        self.assertIn("required", schema)

        # Check required parameters
        self.assertIn("message_ids", schema["properties"])
        self.assertEqual(schema["required"], ["message_ids"])

    def test_stats_definition_valid(self):
        """Test stats tool has valid definition."""
        definition = create_stats_tool_definition()

        # Check required fields
        self.assertIn("name", definition)
        self.assertIn("description", definition)
        self.assertIn("input_schema", definition)

        # Check name
        self.assertEqual(definition["name"], "GetVisualMemoryStats")

        # Check schema structure (no parameters)
        schema = definition["input_schema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["required"], [])


class TestVisualMemoryExecutors(unittest.TestCase):
    """Test that executors work correctly."""

    def setUp(self):
        """Create test agent with visual memory."""
        # Create temporary cache file
        self.temp_dir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.temp_dir, "test_cache.json")

        # Create agent (will initialize visual cache)
        self.agent = HouseCode(
            api_key="test-key-not-used",
            working_directory=".",
        )

        # Override cache path for testing
        self.agent.context.visual_cache.cache_path = self.cache_path

    def tearDown(self):
        """Clean up test cache."""
        if os.path.exists(self.cache_path):
            os.remove(self.cache_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_compress_executor_basic(self):
        """Test compress executor with valid input."""
        text = """
def hello_world():
    print("Hello, World!")
    return 42
"""
        message_ids = ["msg1", "msg2"]

        result = execute_compress(text, message_ids, self.agent)

        # Check result is string
        self.assertIsInstance(result, str)

        # Check result contains expected info
        self.assertIn("Compressed", result)
        self.assertIn("visual tokens", result)
        self.assertIn("Compression:", result)
        self.assertIn("Cache:", result)
        self.assertIn("Mode: MOCK", result)

        # Check cache was populated
        cache_key = "msg1,msg2"
        memory = self.agent.context.visual_cache.get(cache_key)
        self.assertIsNotNone(memory)
        self.assertEqual(memory.message_ids, message_ids)
        self.assertEqual(memory.original_text_length, len(text))

    def test_compress_executor_empty_text(self):
        """Test compress executor rejects empty text."""
        result = execute_compress("", ["msg1"], self.agent)

        self.assertIsInstance(result, str)
        self.assertIn("Error", result)
        self.assertIn("empty", result.lower())

    def test_compress_executor_no_message_ids(self):
        """Test compress executor rejects empty message_ids."""
        result = execute_compress("some text", [], self.agent)

        self.assertIsInstance(result, str)
        self.assertIn("Error", result)
        self.assertIn("message ID", result)

    def test_decompress_executor_success(self):
        """Test decompress executor retrieves from cache."""
        # First compress something
        text = "def test(): pass"
        message_ids = ["msg3"]
        execute_compress(text, message_ids, self.agent)

        # Now decompress
        result = execute_decompress(message_ids, self.agent)

        # Check result is string
        self.assertIsInstance(result, str)

        # Check result contains expected info
        self.assertIn("Decompressed", result)
        self.assertIn("Token count:", result)
        self.assertIn("Original length:", result)
        self.assertIn("Compression ratio:", result)
        self.assertIn("Mode: MOCK", result)
        self.assertIn("Decompressed content:", result)

    def test_decompress_executor_cache_miss(self):
        """Test decompress executor handles cache miss."""
        result = execute_decompress(["nonexistent"], self.agent)

        self.assertIsInstance(result, str)
        self.assertIn("Error", result)
        self.assertIn("No visual memory found", result)

    def test_decompress_executor_no_message_ids(self):
        """Test decompress executor rejects empty message_ids."""
        result = execute_decompress([], self.agent)

        self.assertIsInstance(result, str)
        self.assertIn("Error", result)
        self.assertIn("message ID", result)

    def test_stats_executor(self):
        """Test stats executor returns cache statistics."""
        result = execute_stats(self.agent)

        # Check result is string
        self.assertIsInstance(result, str)

        # Check result contains expected info
        self.assertIn("Visual Memory Cache Statistics", result)
        self.assertIn("Entries:", result)
        self.assertIn("Size:", result)
        self.assertIn("Hit rate:", result)
        self.assertIn("Mode:", result)


class TestVisualMemoryIntegration(unittest.TestCase):
    """Test integration with HouseCode agent."""

    def setUp(self):
        """Create test agent with all tools registered."""
        # Create temporary cache file
        self.temp_dir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.temp_dir, "test_cache.json")

        # Create agent
        self.agent = HouseCode(
            api_key="test-key-not-used",
            working_directory=".",
        )

        # Register all tools
        register_all_tools(self.agent)

        # Override cache path for testing
        self.agent.context.visual_cache.cache_path = self.cache_path

    def tearDown(self):
        """Clean up test cache."""
        if os.path.exists(self.cache_path):
            os.remove(self.cache_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_tools_registered(self):
        """Test visual memory tools are registered."""
        tool_names = [tool["name"] for tool in self.agent.tools]

        self.assertIn("CompressVisualMemory", tool_names)
        self.assertIn("DecompressVisualMemory", tool_names)
        self.assertIn("GetVisualMemoryStats", tool_names)

    def test_compress_tool_executor_exists(self):
        """Test compress tool executor is registered."""
        self.assertIn("CompressVisualMemory", self.agent.tool_executors)

        executor = self.agent.tool_executors["CompressVisualMemory"]
        self.assertIsNotNone(executor)
        self.assertTrue(callable(executor))

    def test_decompress_tool_executor_exists(self):
        """Test decompress tool executor is registered."""
        self.assertIn("DecompressVisualMemory", self.agent.tool_executors)

        executor = self.agent.tool_executors["DecompressVisualMemory"]
        self.assertIsNotNone(executor)
        self.assertTrue(callable(executor))

    def test_stats_tool_executor_exists(self):
        """Test stats tool executor is registered."""
        self.assertIn("GetVisualMemoryStats", self.agent.tool_executors)

        executor = self.agent.tool_executors["GetVisualMemoryStats"]
        self.assertIsNotNone(executor)
        self.assertTrue(callable(executor))

    def test_full_compress_decompress_cycle(self):
        """Test full compress → cache → decompress cycle."""
        # Step 1: Compress text
        text = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
        message_ids = ["msg100", "msg101"]

        compress_executor = self.agent.tool_executors["CompressVisualMemory"]
        result1 = compress_executor(text=text, message_ids=message_ids)

        # Check compression succeeded
        self.assertIsInstance(result1, str)
        self.assertIn("Compressed", result1)
        self.assertNotIn("Error", result1)

        # Step 2: Check cache is populated
        cache_key = "msg100,msg101"
        memory = self.agent.context.visual_cache.get(cache_key)
        self.assertIsNotNone(memory, "Cache should contain compressed memory")

        # Step 3: Decompress
        decompress_executor = self.agent.tool_executors["DecompressVisualMemory"]
        result2 = decompress_executor(message_ids=message_ids)

        # Check decompression succeeded
        self.assertIsInstance(result2, str)
        self.assertIn("Decompressed", result2)
        self.assertNotIn("Error", result2)

        # Step 4: Check stats
        stats_executor = self.agent.tool_executors["GetVisualMemoryStats"]
        result3 = stats_executor()

        # Check stats show 1 entry
        self.assertIn("Entries: 1", result3)

    def test_cache_persistence(self):
        """Test cache can be saved and loaded."""
        # Compress something
        text = "def test(): return 42"
        message_ids = ["persist_test"]

        compress_executor = self.agent.tool_executors["CompressVisualMemory"]
        compress_executor(text=text, message_ids=message_ids)

        # Save cache
        self.agent.context.visual_cache.save()

        # Create new cache and load
        new_cache = VisualCache(cache_path=self.cache_path)
        loaded = new_cache.load()

        self.assertTrue(loaded, "Cache should load successfully")

        # Check entry exists
        memory = new_cache.get("persist_test")
        self.assertIsNotNone(memory)
        self.assertEqual(memory.message_ids, message_ids)


class TestVisualMemoryErrorHandling(unittest.TestCase):
    """Test error handling in visual memory tools."""

    def setUp(self):
        """Create test agent."""
        self.agent = HouseCode(
            api_key="test-key-not-used",
            working_directory=".",
        )

    def test_compress_handles_exceptions_gracefully(self):
        """Test compress tool doesn't crash on errors."""
        # Try compressing with invalid input types (should be caught by tool validation)
        # But test executor error handling
        result = execute_compress("", [], self.agent)

        # Should return error string, not raise exception
        self.assertIsInstance(result, str)
        self.assertIn("Error", result)

    def test_decompress_handles_missing_cache(self):
        """Test decompress handles cache miss gracefully."""
        result = execute_decompress(["missing_key"], self.agent)

        # Should return helpful error message
        self.assertIsInstance(result, str)
        self.assertIn("Error", result)
        self.assertIn("No visual memory found", result)

    def test_multiple_compressions_with_cache_eviction(self):
        """Test cache eviction works correctly."""
        # Set small cache limit
        self.agent.context.visual_cache.max_entries = 3

        # Compress 5 items (should evict 2)
        for i in range(5):
            text = f"def func{i}(): pass"
            message_ids = [f"msg{i}"]
            execute_compress(text, message_ids, self.agent)

        # Check cache has exactly 3 entries (oldest 2 evicted)
        stats = self.agent.context.visual_cache.stats()
        self.assertEqual(stats["entries"], 3)
        self.assertEqual(stats["evictions"], 2)

        # Check oldest entries were evicted
        self.assertIsNone(self.agent.context.visual_cache.get("msg0"))
        self.assertIsNone(self.agent.context.visual_cache.get("msg1"))

        # Check newest entries still exist
        self.assertIsNotNone(self.agent.context.visual_cache.get("msg2"))
        self.assertIsNotNone(self.agent.context.visual_cache.get("msg3"))
        self.assertIsNotNone(self.agent.context.visual_cache.get("msg4"))


def run_tests():
    """Run all tests and print results."""
    print("=" * 60)
    print("Phase 5 Visual Memory Tools Test Suite")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestVisualMemoryToolDefinitions))
    suite.addTests(loader.loadTestsFromTestCase(TestVisualMemoryExecutors))
    suite.addTests(loader.loadTestsFromTestCase(TestVisualMemoryIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestVisualMemoryErrorHandling))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 60)
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")
    if result.wasSuccessful():
        print("✓ All tests passed!")
    else:
        print(f"✗ {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
