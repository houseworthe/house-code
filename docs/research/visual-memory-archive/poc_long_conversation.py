"""
Test image archival with a LONGER conversation.

Finding from POC 1: Short text (411 bytes) → 22KB PNG = negative compression
Hypothesis: Longer text (5KB+) should show positive compression

This tests a more realistic use case: archiving old message blocks.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from house_code.tools.visual import create_renderer, ArchivedImage


def create_long_conversation():
    """Create a realistic long conversation (~5-10KB)."""

    # Simulate a longer debugging session with code
    return """[USER]: I'm trying to implement a recursive function to find all files in a directory, but it's not working as expected. Here's my code:

import os

def find_files(path, pattern):
    results = []
    for item in os.listdir(path):
        if item.endswith(pattern):
            results.append(item)
    return results

files = find_files('/Users/me/Documents', '.txt')
print(files)

[ASSISTANT]: Your function is only checking the immediate directory, not recursing into subdirectories. Here's a fixed version:

import os

def find_files(path, pattern):
    results = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(pattern):
                full_path = os.path.join(root, file)
                results.append(full_path)
    return results

files = find_files('/Users/me/Documents', '.txt')
print(f'Found {len(files)} files:')
for f in files:
    print(f'  {f}')

The key changes:
1. Use os.walk() instead of os.listdir() - this recursively traverses directories
2. Store full paths using os.path.join()
3. Added better output formatting

[USER]: That works! But now I want to add a filter to exclude certain directories like __pycache__ and .git. How do I do that?

[ASSISTANT]: You can modify the dirs list in-place during os.walk() to skip directories:

import os

def find_files(path, pattern, exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', 'node_modules', '.venv']

    results = []
    for root, dirs, files in os.walk(path):
        # Remove excluded directories from dirs in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(pattern):
                full_path = os.path.join(root, file)
                results.append(full_path)

    return results

# Usage
files = find_files('/Users/me/Documents', '.txt')
print(f'Found {len(files)} .txt files')

# Or with custom exclusions
files = find_files(
    '/Users/me/Projects',
    '.py',
    exclude_dirs=['build', 'dist', 'venv']
)

The key trick is `dirs[:] = [...]` which modifies the list in-place. This tells os.walk() to skip those directories.

[USER]: Perfect! One more thing - can I make it case-insensitive? I want to match both .txt and .TXT files.

[ASSISTANT]: Sure! Use str.lower() for case-insensitive matching:

import os

def find_files(path, pattern, exclude_dirs=None, case_sensitive=True):
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', 'node_modules', '.venv']

    # Normalize pattern for case-insensitive matching
    if not case_sensitive:
        pattern = pattern.lower()

    results = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            # Compare lowercased filename if case-insensitive
            filename = file.lower() if not case_sensitive else file

            if filename.endswith(pattern):
                full_path = os.path.join(root, file)
                results.append(full_path)

    return results

# Case-insensitive search
files = find_files('/Users/me/Documents', '.txt', case_sensitive=False)
# Will match: document.txt, README.TXT, notes.Txt, etc.

[USER]: Excellent! This is exactly what I needed. Thanks!

[ASSISTANT]: You're welcome! A few best practices to consider:

1. **Error handling**: Add try-except for permission errors:
   ```python
   try:
       for root, dirs, files in os.walk(path):
           # ... your code ...
   except PermissionError as e:
       print(f"Permission denied: {e}")
   ```

2. **Performance**: For large directories, consider using pathlib:
   ```python
   from pathlib import Path

   def find_files_pathlib(path, pattern, case_sensitive=True):
       p = Path(path)
       if case_sensitive:
           return list(p.rglob(f'*{pattern}'))
       else:
           # pathlib doesn't support case-insensitive, use os.walk
           pass
   ```

3. **Testing**: Add unit tests:
   ```python
   def test_find_files():
       # Create temp directory structure
       import tempfile
       with tempfile.TemporaryDirectory() as tmpdir:
           # Create test files
           Path(tmpdir, 'test.txt').touch()
           Path(tmpdir, 'subdir').mkdir()
           Path(tmpdir, 'subdir', 'nested.txt').touch()

           # Test
           results = find_files(tmpdir, '.txt')
           assert len(results) == 2
   ```

Let me know if you need help with any of these!"""


def test_long_conversation():
    """Test archival with longer, more realistic conversation."""

    print("=== Testing Long Conversation Archival ===\n")

    long_text = create_long_conversation()

    print(f"Sample text length: {len(long_text)} characters ({len(long_text.encode('utf-8'))} bytes)")
    print(f"Preview: {long_text[:150]}...\n")

    # Render
    print("Rendering to PNG...")
    renderer = create_renderer()
    images = renderer.render_conversation(
        long_text,
        message_ids=[f"msg_{i}" for i in range(1, 11)]
    )

    print(f"✓ Rendered {len(images)} image(s)")
    for i, img in enumerate(images):
        print(f"  Page {i+1}: {img.size_kb:.1f} KB")
    print()

    # Stitch all pages into one tall image
    if len(images) > 1:
        print(f"Stitching {len(images)} pages into single tall image...")
        from PIL import Image as PILImage
        import io

        # Load all page images
        page_images = [PILImage.open(io.BytesIO(img.image_bytes)) for img in images]

        # Calculate dimensions for tall image
        width = page_images[0].width  # Should be 1024
        total_height = sum(img.height for img in page_images)

        # Create tall canvas
        tall_image = PILImage.new('RGB', (width, total_height), color='white')

        # Paste each page vertically
        y_offset = 0
        for page_img in page_images:
            tall_image.paste(page_img, (0, y_offset))
            y_offset += page_img.height

        # Convert back to bytes
        buffer = io.BytesIO()
        tall_image.save(buffer, format='PNG')
        stitched_bytes = buffer.getvalue()

        print(f"✓ Stitched into {width}x{total_height} image ({len(stitched_bytes) / 1024:.1f} KB)")

        archived = ArchivedImage(
            image_bytes=stitched_bytes,
            message_ids=[f"msg_{i}" for i in range(1, 11)],
            original_text=long_text,
            format="PNG"
        )
    else:
        # Single page, use as-is
        archived = ArchivedImage(
            image_bytes=images[0].image_bytes,
            message_ids=[f"msg_{i}" for i in range(1, 11)],
            original_text=long_text,
            format="PNG"
        )

    # Metrics
    text_bytes = len(long_text.encode('utf-8'))
    png_bytes = len(archived.image_bytes)
    byte_compression = text_bytes / png_bytes

    # Token estimates
    text_tokens = text_bytes // 4  # ~4 chars per token
    visual_tokens = 256 * len(images)  # Base mode: 256 tokens per 1024x1024
    token_compression = text_tokens / visual_tokens if visual_tokens > 0 else 0

    print("Compression Analysis:")
    print("=" * 60)
    print(f"Original text:      {text_bytes:,} bytes ({len(long_text)} chars)")
    print(f"PNG archive(s):     {png_bytes:,} bytes ({archived.size_kb:.1f} KB)")
    print(f"Byte compression:   {byte_compression:.2f}x")
    print()
    print(f"Est. text tokens:   ~{text_tokens:,}")
    print(f"Est. visual tokens: ~{visual_tokens}")
    print(f"Token compression:  ~{token_compression:.2f}x")
    print("=" * 60)
    print()

    # Save
    output_path = '/tmp/poc_long_conversation.png'
    with open(output_path, 'wb') as f:
        f.write(archived.image_bytes)

    print(f"✓ Saved to {output_path}")
    print()

    # Analysis
    if byte_compression > 0.5:
        print("✅ POSITIVE byte compression achieved!")
        print(f"   PNG is {1/byte_compression:.1f}x smaller than text")
    else:
        print("❌ NEGATIVE byte compression")
        print(f"   PNG is {byte_compression:.1f}x larger than text")
        print("   → PNG has ~22KB fixed overhead")
        print("   → Only efficient for text >50KB")

    print()

    if token_compression > 3.0:
        print(f"✅ GOOD token compression: {token_compression:.1f}x")
        print("   → Visual memory could save significant tokens")
    elif token_compression > 1.0:
        print(f"⚠️  MARGINAL token compression: {token_compression:.1f}x")
        print("   → Small savings, may not justify complexity")
    else:
        print(f"❌ POOR token compression: {token_compression:.1f}x")
        print("   → Not worth implementing")

    print()
    print("Next: Review PNG quality and proceed to Phase 2 (RunPod OCR)")

    return archived


if __name__ == "__main__":
    test_long_conversation()
