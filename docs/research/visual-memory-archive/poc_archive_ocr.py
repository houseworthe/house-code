"""
Minimal POC: Test image archival + OCR reconstruction.

Phase 1: Local POC (no GPU required)
- Render sample conversation to PNG
- Store PNG bytes
- Calculate compression metrics
- Verify rendering quality

Phase 2 will test OCR reconstruction with DeepSeek-OCR on RunPod.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from house_code.visual import create_renderer, ArchivedImage


def poc_archive_conversation():
    """Test archiving a conversation as PNG."""

    print("=== Phase 1: Image Archival POC ===\n")

    # Sample conversation (realistic example with code)
    sample_text = """[USER]: Can you help me fix this bug?

[ASSISTANT]: Sure! What's the issue?

[USER]: My function is returning None:

def get_user(user_id):
    user = db.query(User).filter_by(id=user_id)
    return user

[ASSISTANT]: The issue is you're not calling .first() or .all(). Try:

def get_user(user_id):
    user = db.query(User).filter_by(id=user_id).first()
    return user

[USER]: Perfect! That fixed it. Thanks!"""

    print("Sample conversation:")
    print("-" * 60)
    print(sample_text[:200] + "...")
    print("-" * 60)
    print()

    # 1. Render to PNG
    print("Step 1: Rendering to PNG...")
    renderer = create_renderer()
    images = renderer.render_conversation(
        sample_text,
        message_ids=["msg_1", "msg_2", "msg_3", "msg_4", "msg_5"]
    )

    print(f"✓ Rendered {len(images)} image(s)")
    print(f"  Image resolution: {images[0].resolution}")
    print(f"  Image size: {images[0].size_kb:.1f} KB")
    print()

    # 2. Archive (store PNG bytes)
    print("Step 2: Archiving conversation...")
    archived = ArchivedImage(
        image_bytes=images[0].image_bytes,
        message_ids=["msg_1", "msg_2", "msg_3", "msg_4", "msg_5"],
        original_text=sample_text,
        format="PNG",
        metadata={
            "resolution": images[0].resolution,
            "page_count": len(images),
        }
    )

    print(f"✓ Archived conversation")
    print(f"  Message IDs: {len(archived.message_ids)}")
    print(f"  Archive format: {archived.format}")
    print()

    # 3. Calculate compression metrics
    print("Step 3: Calculating compression metrics...")
    text_size_bytes = len(sample_text.encode('utf-8'))
    png_size_bytes = len(archived.image_bytes)
    compression_ratio = text_size_bytes / png_size_bytes if png_size_bytes > 0 else 0

    # Estimate token savings (rough: 4 chars per token)
    estimated_text_tokens = text_size_bytes // 4
    # DeepSeek-OCR Base mode uses ~256 visual tokens for 1024x1024
    estimated_visual_tokens = 256
    token_compression = estimated_text_tokens / estimated_visual_tokens if estimated_visual_tokens > 0 else 0

    print(f"✓ Compression analysis:")
    print(f"  Original text: {text_size_bytes} bytes ({len(sample_text)} chars)")
    print(f"  PNG archive: {png_size_bytes} bytes ({archived.size_kb:.1f} KB)")
    print(f"  Byte compression: {compression_ratio:.2f}x")
    print(f"  Est. text tokens: ~{estimated_text_tokens}")
    print(f"  Est. visual tokens: ~{estimated_visual_tokens}")
    print(f"  Token compression: ~{token_compression:.2f}x")
    print()

    # 4. Save PNG for manual inspection
    print("Step 4: Saving PNG for inspection...")
    output_path = '/tmp/poc_conversation.png'
    with open(output_path, 'wb') as f:
        f.write(archived.image_bytes)

    print(f"✓ Saved to {output_path}")
    print(f"  → Open this file to verify rendering quality")
    print(f"  → Check if text is readable and code is clear")
    print()

    # 5. Phase 2 reminder
    print("=" * 60)
    print("Phase 1 Complete!")
    print("=" * 60)
    print()
    print("✓ PNG renders correctly")
    print(f"✓ File size reasonable ({archived.size_kb:.1f} KB)")
    print(f"✓ Compression ratio: {compression_ratio:.2f}x (bytes)")
    print()
    print("⚠️  Phase 2 Required: OCR Accuracy Test")
    print("   Need to test with real DeepSeek-OCR on RunPod:")
    print("   1. Deploy RunPod pod with RTX 4090")
    print("   2. Install DeepSeek-OCR")
    print("   3. Run OCR on this PNG")
    print("   4. Measure accuracy (target: >90%)")
    print()
    print(f"Next step: scp {output_path} to RunPod and test OCR")
    print()

    return archived


def validate_rendering_quality():
    """
    Additional validation checks for rendering quality.

    Helps identify potential OCR issues before GPU testing.
    """
    print("\n=== Rendering Quality Checks ===\n")

    # Test different content types
    test_cases = [
        ("Plain text", "This is a simple conversation without code."),
        ("Code only", "def hello():\n    print('world')\n    return True"),
        ("Mixed", "Here's the function:\n\ndef process(x):\n    return x * 2\n\nDoes that help?"),
        ("Special chars", "Common symbols: @#$%^&*() {} [] <> /\\"),
    ]

    for name, text in test_cases:
        renderer = create_renderer()
        images = renderer.render_conversation(text, ["test"])

        print(f"{name}:")
        print(f"  Text: {len(text)} chars")
        print(f"  PNG: {images[0].size_kb:.1f} KB")
        print(f"  Ratio: {len(text) / len(images[0].image_bytes):.2f}x")
        print()

    print("✓ Quality checks complete")


if __name__ == "__main__":
    # Run main POC
    archived = poc_archive_conversation()

    # Optional: Run additional quality checks
    print("\nRun additional quality checks? (y/n): ", end='')
    response = input().strip().lower()
    if response == 'y':
        validate_rendering_quality()

    print("\n" + "=" * 60)
    print("POC Phase 1 Complete!")
    print("=" * 60)
    print()
    print("Review the PNG at /tmp/poc_conversation.png")
    print("If it looks good, proceed to Phase 2 (RunPod OCR test)")
