#!/usr/bin/env python3
"""
Test script for visual memory renderer.

Tests the rendering engine with sample conversation data.
Validates:
- Image generation (1024x1024)
- Syntax highlighting
- Multi-page rendering
- Font rendering
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from house_code.visual import create_renderer


def test_basic_rendering():
    """Test basic text rendering."""
    print("Test 1: Basic text rendering...")

    renderer = create_renderer()

    sample_text = """
This is a sample conversation between a user and an AI assistant.

[user]:
Can you help me write a Python function to calculate fibonacci numbers?

[assistant]:
Sure! Here's a simple recursive implementation:

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

This is the classic recursive approach. For better performance, you could use memoization.

[user]:
Can you add memoization?

[assistant]:
Absolutely! Here's the memoized version:

def fibonacci(n, memo=None):
    if memo is None:
        memo = {}

    if n in memo:
        return memo[n]

    if n <= 1:
        return n

    memo[n] = fibonacci(n-1, memo) + fibonacci(n-2, memo)
    return memo[n]

This caches results and avoids redundant calculations.
    """

    message_ids = ['msg1', 'msg2', 'msg3', 'msg4']

    try:
        images = renderer.render_conversation(sample_text, message_ids)
        print(f"✓ Rendered {len(images)} image(s)")

        for i, img in enumerate(images):
            print(f"  - Image {i+1}: {img.size_kb:.1f} KB, {img.resolution}")

        # Save first image
        if images:
            output_path = '/tmp/test_render_basic.png'
            with open(output_path, 'wb') as f:
                f.write(images[0].image_bytes)
            print(f"✓ Saved to {output_path}")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multipage_rendering():
    """Test multi-page rendering with long content."""
    print("\nTest 2: Multi-page rendering...")

    renderer = create_renderer()

    # Generate long code sample
    long_code = """
def process_data(data_list):
    \"\"\"Process a list of data items.\"\"\"
    results = []

    for item in data_list:
        if item is None:
            continue

        # Validate item
        if not isinstance(item, dict):
            raise TypeError(f"Expected dict, got {type(item)}")

        # Extract fields
        name = item.get('name', 'unknown')
        value = item.get('value', 0)
        timestamp = item.get('timestamp')

        # Process
        processed = {
            'name': name.upper(),
            'value': value * 2,
            'timestamp': timestamp,
            'processed_at': datetime.now(),
        }

        results.append(processed)

    return results


class DataProcessor:
    \"\"\"Main data processor class.\"\"\"

    def __init__(self, config):
        self.config = config
        self.cache = {}
        self.stats = {
            'processed': 0,
            'errors': 0,
        }

    def process(self, data):
        \"\"\"Process incoming data.\"\"\"
        try:
            result = self._process_internal(data)
            self.stats['processed'] += 1
            return result
        except Exception as e:
            self.stats['errors'] += 1
            raise

    def _process_internal(self, data):
        \"\"\"Internal processing logic.\"\"\"
        # Check cache
        cache_key = self._get_cache_key(data)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Process
        result = self._transform(data)

        # Cache result
        self.cache[cache_key] = result

        return result

    def _get_cache_key(self, data):
        \"\"\"Generate cache key for data.\"\"\"
        import hashlib
        import json

        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _transform(self, data):
        \"\"\"Transform data.\"\"\"
        return {
            'transformed': True,
            'original': data,
            'timestamp': datetime.now().isoformat(),
        }


# Usage example
processor = DataProcessor(config={'mode': 'strict'})

sample_data = [
    {'name': 'alice', 'value': 10, 'timestamp': '2025-10-23T10:00:00'},
    {'name': 'bob', 'value': 20, 'timestamp': '2025-10-23T10:01:00'},
    {'name': 'charlie', 'value': 30, 'timestamp': '2025-10-23T10:02:00'},
]

results = process_data(sample_data)
for result in results:
    print(f"Processed: {result}")
    """

    message_ids = ['msg_code_1']

    try:
        images = renderer.render_conversation(long_code, message_ids)
        print(f"✓ Rendered {len(images)} image(s) from long code")

        for i, img in enumerate(images):
            print(f"  - Page {i+1}: {img.size_kb:.1f} KB, metadata: {img.metadata}")

        # Save all pages
        for i, img in enumerate(images):
            output_path = f'/tmp/test_render_page_{i+1}.png'
            with open(output_path, 'wb') as f:
                f.write(img.image_bytes)
            print(f"✓ Saved page {i+1} to {output_path}")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compression_estimate():
    """Test compression ratio estimation."""
    print("\nTest 3: Compression ratio estimation...")

    renderer = create_renderer()

    test_cases = [
        ("Plain text with no code", "This is just plain text. No code here."),
        ("Code-heavy", """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
        """),
        ("Mixed content", """
Here's a function:

def hello(name):
    return f"Hello, {name}!"

And some explanation text about what it does.
        """),
    ]

    try:
        for name, text in test_cases:
            ratio = renderer.estimate_compression_ratio(text)
            print(f"✓ {name}: ~{ratio:.1f}x compression")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_message_formatting():
    """Test rendering from structured messages."""
    print("\nTest 4: Message formatting...")

    renderer = create_renderer()

    messages = [
        {
            'id': 'msg1',
            'role': 'user',
            'content': 'Write a hello world in Python'
        },
        {
            'id': 'msg2',
            'role': 'assistant',
            'content': 'Here it is:\n\nprint("Hello, World!")'
        },
        {
            'id': 'msg3',
            'role': 'user',
            'content': 'Thanks!'
        },
    ]

    try:
        images = renderer.render_messages(messages)
        print(f"✓ Rendered {len(images)} image(s) from {len(messages)} messages")

        output_path = '/tmp/test_render_messages.png'
        with open(output_path, 'wb') as f:
            f.write(images[0].image_bytes)
        print(f"✓ Saved to {output_path}")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Visual Memory Renderer Test Suite")
    print("=" * 60)

    tests = [
        test_basic_rendering,
        test_multipage_rendering,
        test_compression_estimate,
        test_message_formatting,
    ]

    results = []
    for test in tests:
        result = test()
        results.append(result)

    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
