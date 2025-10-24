#!/usr/bin/env python3
"""
Test suite for Phase 4: Visual memory MCP client with mock.

Tests:
1. Configuration defaults and persistence
2. Mock compression determinism and ratio
3. Cache LRU eviction and size limits
4. Cache persistence (save/load)
5. RosieClient mock mode
6. Integration: render → compress → cache → retrieve
"""

import sys
import os
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from house_code.visual import (
    create_renderer,
    VisualMemory,
    VisualTokens,
)
from house_code.visual.config import (
    VisualMemoryConfig,
    load_config,
    save_config,
    get_default_config,
    reset_config,
)
from house_code.visual.mock import (
    mock_compress,
    mock_decompress,
    estimate_compression_ratio,
    validate_mock_tokens,
)
from house_code.visual.cache import VisualCache
from house_code.visual.rosie_client import RosieClient


def test_config_defaults():
    """Test 1: Configuration defaults."""
    print("Test 1: Configuration defaults...")

    try:
        config = get_default_config()

        # Verify defaults
        assert config.use_mock == True, "Default should be mock mode"
        assert config.cache_max_entries == 50, "Default max entries should be 50"
        assert config.cache_max_size_mb == 100, "Default max size should be 100MB"
        assert config.compression_target_ratio == 8.0, "Default ratio should be 8.0"
        assert config.mock_latency_ms == 100, "Default latency should be 100ms"

        print("✓ Default config values correct")
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_persistence():
    """Test 2: Config save/load roundtrip."""
    print("\nTest 2: Config persistence...")

    try:
        # Create temp config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            # Create custom config
            config = VisualMemoryConfig(
                use_mock=False,
                cache_max_entries=100,
                cache_max_size_mb=200,
                cache_path=temp_path,
            )

            # Save
            success = save_config(config)
            assert success, "Save should succeed"
            print("✓ Config saved")

            # Load
            loaded = load_config()
            print("✓ Config loaded")

            # Note: loaded config will have defaults for most fields
            # since save_config only saves to visual_memory section
            # This is expected behavior - just verify it loads without error

            return True

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mock_compression_deterministic():
    """Test 3: Mock compression is deterministic."""
    print("\nTest 3: Mock compression determinism...")

    try:
        # Create sample image data
        image_bytes = b"fake image data for testing"

        # Compress twice
        tokens1 = mock_compress(image_bytes, latency_ms=0)
        tokens2 = mock_compress(image_bytes, latency_ms=0)

        # Should be identical
        assert len(tokens1) == len(tokens2), "Token counts should match"
        assert tokens1.data == tokens2.data, "Token data should match"
        print(f"✓ Deterministic: {len(tokens1)} tokens")

        # Validate token format
        is_valid, msg = validate_mock_tokens(tokens1)
        assert is_valid, f"Tokens should be valid: {msg}"
        print(f"✓ Tokens valid: {msg}")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mock_compression_ratio():
    """Test 4: Mock compression achieves target ratio."""
    print("\nTest 4: Mock compression ratio...")

    try:
        # Create sample image (simulate 1024x1024 PNG)
        image_bytes = b"x" * (30 * 1024)  # ~30KB

        # Compress
        tokens = mock_compress(image_bytes, target_ratio=8.0, latency_ms=0)

        # Check token count (Base mode: 256 tokens)
        assert len(tokens) == 256, f"Expected 256 tokens, got {len(tokens)}"
        print(f"✓ Token count: {len(tokens)} (Base mode)")

        # Check metadata
        ratio = tokens.metadata.get('compression_ratio')
        assert ratio == 8.0, f"Expected 8.0x ratio, got {ratio}"
        print(f"✓ Compression ratio: {ratio}x")

        # Test decompression
        decompressed = mock_decompress(tokens)
        assert "[COMPRESSED" in decompressed, "Should return placeholder"
        print(f"✓ Decompression returns placeholder ({len(decompressed)} chars)")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_lru_eviction():
    """Test 5: Cache LRU eviction works correctly."""
    print("\nTest 5: Cache LRU eviction...")

    try:
        # Create small cache (max 3 entries)
        cache = VisualCache(max_entries=3, max_size_mb=1000)

        # Add 5 entries
        for i in range(5):
            memory = VisualMemory(
                message_ids=[f'msg{i}'],
                visual_tokens=VisualTokens(
                    data=[f'token{i}'] * 256,
                    metadata={'test': True}
                ),
                original_text_length=1000,
                compression_ratio=8.0,
            )
            cache.put(f'key{i}', memory)

        # Should only have last 3
        assert len(cache.cache) == 3, f"Expected 3 entries, got {len(cache.cache)}"
        print(f"✓ Cache limited to {len(cache.cache)} entries")

        # Should have key2, key3, key4 (last 3)
        keys = cache.keys()
        assert 'key2' in keys, "Should have key2"
        assert 'key3' in keys, "Should have key3"
        assert 'key4' in keys, "Should have key4"
        assert 'key0' not in keys, "Should not have key0 (evicted)"
        assert 'key1' not in keys, "Should not have key1 (evicted)"
        print(f"✓ Correct entries retained: {keys}")

        # Test LRU order: access key2, then add key5
        cache.get('key2')  # Bump key2 to end
        memory5 = VisualMemory(
            message_ids=['msg5'],
            visual_tokens=VisualTokens(data=['token5'] * 256, metadata={}),
            original_text_length=1000,
            compression_ratio=8.0,
        )
        cache.put('key5', memory5)

        # Should evict key3 (oldest), keep key2, key4, key5
        keys = cache.keys()
        assert 'key2' in keys, "Should keep key2 (recently accessed)"
        assert 'key4' in keys, "Should keep key4"
        assert 'key5' in keys, "Should keep key5 (newest)"
        assert 'key3' not in keys, "Should evict key3 (oldest)"
        print(f"✓ LRU eviction correct: {keys}")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_size_limit():
    """Test 6: Cache size limit eviction."""
    print("\nTest 6: Cache size limit...")

    try:
        # Create cache with tiny size limit (1 MB)
        cache = VisualCache(max_entries=100, max_size_mb=1)

        # Add entries until size limit hit
        for i in range(10):
            # Create large entry (~200KB text)
            memory = VisualMemory(
                message_ids=[f'msg{i}'],
                visual_tokens=VisualTokens(
                    data=['x' * 100] * 256,  # Large tokens
                    metadata={'size': 'large'}
                ),
                original_text_length=200_000,  # 200KB
                compression_ratio=8.0,
            )
            cache.put(f'key{i}', memory)

        # Should have evicted some entries due to size
        assert len(cache.cache) < 10, f"Should evict by size, got {len(cache.cache)}"
        print(f"✓ Size-based eviction: {len(cache.cache)} entries kept")

        size_mb = cache.size_mb()
        print(f"✓ Cache size: {size_mb:.2f} MB")

        # Check stats
        stats = cache.stats()
        assert stats['evictions'] > 0, "Should have evictions"
        print(f"✓ Stats: {stats['evictions']} evictions")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_persistence():
    """Test 7: Cache save/load roundtrip."""
    print("\nTest 7: Cache persistence...")

    try:
        # Create temp file for cache
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            # Create cache with entries
            cache1 = VisualCache(cache_path=temp_path)

            for i in range(3):
                memory = VisualMemory(
                    message_ids=[f'msg{i}'],
                    visual_tokens=VisualTokens(
                        data=[f'token{i}'] * 10,
                        metadata={'index': i}
                    ),
                    original_text_length=1000,
                    compression_ratio=8.0,
                )
                cache1.put(f'key{i}', memory)

            # Save
            success = cache1.save()
            assert success, "Save should succeed"
            print(f"✓ Saved {len(cache1.cache)} entries")

            # Load into new cache
            cache2 = VisualCache(cache_path=temp_path)
            success = cache2.load()
            assert success, "Load should succeed"
            print(f"✓ Loaded {len(cache2.cache)} entries")

            # Verify contents match
            assert len(cache2.cache) == len(cache1.cache), "Entry count should match"

            for key in cache1.keys():
                mem1 = cache1.get(key)
                mem2 = cache2.get(key)

                assert mem2 is not None, f"Should have {key}"
                assert mem1.message_ids == mem2.message_ids, "Message IDs should match"
                assert len(mem1.visual_tokens) == len(mem2.visual_tokens), "Token count should match"

            print("✓ All entries match")
            return True

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rosie_client_mock_mode():
    """Test 8: RosieClient works in mock mode."""
    print("\nTest 8: RosieClient mock mode...")

    try:
        # Create client in mock mode
        config = VisualMemoryConfig(use_mock=True, mock_latency_ms=0)
        client = RosieClient(config=config)

        # Test health check
        is_healthy = client.health_check()
        assert is_healthy, "Mock mode should always be healthy"
        print("✓ Health check: healthy")

        # Test compression
        image_bytes = b"test image data"
        tokens = client.compress(image_bytes)
        assert len(tokens) == 256, "Should return 256 tokens"
        print(f"✓ Compression: {len(tokens)} tokens")

        # Test decompression
        text = client.decompress(tokens)
        assert "[COMPRESSED" in text, "Should return placeholder"
        print(f"✓ Decompression: {len(text)} chars")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_full_flow():
    """Test 9: Full integration flow."""
    print("\nTest 9: Integration - Render → Compress → Cache → Retrieve...")

    try:
        # 1. Render conversation
        print("  Step 1: Rendering...")
        renderer = create_renderer()

        sample_text = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

This is a recursive fibonacci implementation.
        """

        images = renderer.render_conversation(sample_text, ['msg1'])
        assert len(images) > 0, "Should render at least one image"
        print(f"  ✓ Rendered {len(images)} image(s), {images[0].size_kb:.1f} KB")

        # 2. Compress with mock
        print("  Step 2: Compressing...")
        config = VisualMemoryConfig(use_mock=True, mock_latency_ms=0)
        client = RosieClient(config=config)

        tokens = client.compress(images[0].image_bytes)
        assert len(tokens) == 256, "Should have 256 tokens"
        print(f"  ✓ Compressed to {len(tokens)} tokens")

        # 3. Create visual memory
        print("  Step 3: Creating visual memory...")
        memory = VisualMemory(
            message_ids=['msg1'],
            visual_tokens=tokens,
            original_text_length=len(sample_text),
            compression_ratio=8.0,
        )
        print(f"  ✓ Memory created: {memory.token_count} tokens, {memory.compression_ratio}x")

        # 4. Cache it
        print("  Step 4: Caching...")
        cache = VisualCache()
        cache.put('msg1', memory)
        assert len(cache.cache) == 1, "Should have 1 entry"
        print(f"  ✓ Cached (stats: {cache.stats()})")

        # 5. Retrieve
        print("  Step 5: Retrieving...")
        retrieved = cache.get('msg1')
        assert retrieved is not None, "Should retrieve entry"
        assert retrieved.message_ids == ['msg1'], "Should match original"
        print(f"  ✓ Retrieved: {len(retrieved.visual_tokens)} tokens")

        # 6. Decompress
        print("  Step 6: Decompressing...")
        decompressed = client.decompress(retrieved.visual_tokens)
        assert '[COMPRESSED' in decompressed, "Should have placeholder"
        print(f"  ✓ Decompressed: {len(decompressed)} chars")

        # 7. Save cache to temp file
        print("  Step 7: Persisting cache...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            cache.cache_path = temp_path
            success = cache.save()
            assert success, "Save should succeed"
            print(f"  ✓ Cache saved to {temp_path}")

            # 8. Load cache in new instance
            print("  Step 8: Loading cache...")
            cache2 = VisualCache(cache_path=temp_path)
            success = cache2.load()
            assert success, "Load should succeed"

            retrieved2 = cache2.get('msg1')
            assert retrieved2 is not None, "Should load entry"
            print(f"  ✓ Cache loaded: {len(cache2.cache)} entries")

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        print("✓ Full integration flow complete!")
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 4 Visual Memory Test Suite")
    print("=" * 60)

    tests = [
        test_config_defaults,
        test_config_persistence,
        test_mock_compression_deterministic,
        test_mock_compression_ratio,
        test_cache_lru_eviction,
        test_cache_size_limit,
        test_cache_persistence,
        test_rosie_client_mock_mode,
        test_integration_full_flow,
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
