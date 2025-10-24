#!/usr/bin/env python3
"""
Test script for DeepSeek-OCR MCP Server.

Tests:
1. GPU availability
2. Model loading
3. Compression/decompression cycle
4. Performance benchmarking (optional)

Usage:
  python test_server.py               # Basic tests
  python test_server.py --benchmark   # Include performance benchmarks
"""

import sys
import time
import argparse
import logging
from pathlib import Path

import torch
from PIL import Image, ImageDraw, ImageFont
import io

from inference import DeepSeekOCR, ModelNotLoadedError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_gpu():
    """Test 1: GPU availability."""
    logger.info("Test 1: Checking GPU availability...")

    if not torch.cuda.is_available():
        logger.error("✗ CUDA not available")
        return False

    gpu_count = torch.cuda.device_count()
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9

    logger.info(f"✓ CUDA available")
    logger.info(f"  GPU Count: {gpu_count}")
    logger.info(f"  GPU Name: {gpu_name}")
    logger.info(f"  GPU Memory: {gpu_memory:.2f} GB")

    return True


def test_model_loading():
    """Test 2: Model loading."""
    logger.info("Test 2: Loading DeepSeek-OCR model...")

    try:
        start_time = time.time()
        model = DeepSeekOCR()
        load_time = time.time() - start_time

        logger.info(f"✓ Model loaded successfully in {load_time:.2f}s")
        return model

    except ModelNotLoadedError as e:
        logger.error(f"✗ Model loading failed: {e}")
        return None


def create_test_image() -> bytes:
    """Create a test image with code content."""
    # Create image
    width, height = 1920, 1080
    image = Image.new('RGB', (width, height), color='#282828')
    draw = ImageDraw.Draw(image)

    # Try to use a monospace font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
    except:
        font = ImageFont.load_default()

    # Add sample code
    code_lines = [
        "def fibonacci(n: int) -> int:",
        "    \"\"\"Calculate nth Fibonacci number.\"\"\"",
        "    if n <= 1:",
        "        return n",
        "    return fibonacci(n-1) + fibonacci(n-2)",
        "",
        "# Test cases",
        "assert fibonacci(0) == 0",
        "assert fibonacci(1) == 1",
        "assert fibonacci(10) == 55",
    ]

    y_offset = 50
    for line in code_lines:
        draw.text((50, y_offset), line, fill='#ebdbb2', font=font)
        y_offset += 25

    # Convert to bytes
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def test_compression_decompression(model: DeepSeekOCR):
    """Test 3: Compression/decompression cycle."""
    logger.info("Test 3: Testing compression/decompression cycle...")

    try:
        # Create test image
        logger.info("  Creating test image...")
        image_bytes = create_test_image()
        original_size = len(image_bytes)
        logger.info(f"  Original image: {original_size} bytes")

        # Compress
        logger.info("  Compressing...")
        start_time = time.time()
        compression_result = model.compress(image_bytes, compression_level="medium")
        compress_time = time.time() - start_time

        token_count = len(compression_result.tokens)
        ratio = compression_result.compression_ratio

        logger.info(f"  ✓ Compressed in {compress_time:.2f}s")
        logger.info(f"    Tokens: {token_count}")
        logger.info(f"    Ratio: {ratio:.2f}x")

        # Decompress
        logger.info("  Decompressing...")
        start_time = time.time()
        decompression_result = model.decompress(compression_result.tokens)
        decompress_time = time.time() - start_time

        text_length = len(decompression_result.text)
        confidence = decompression_result.confidence

        logger.info(f"  ✓ Decompressed in {decompress_time:.2f}s")
        logger.info(f"    Text length: {text_length} chars")
        logger.info(f"    Confidence: {confidence:.2%}")

        logger.info("✓ Compression/decompression cycle successful")
        return True

    except Exception as e:
        logger.error(f"✗ Compression/decompression failed: {e}", exc_info=True)
        return False


def run_benchmark(model: DeepSeekOCR, iterations: int = 10):
    """Test 4: Performance benchmark."""
    logger.info(f"Test 4: Running performance benchmark ({iterations} iterations)...")

    compress_times = []
    decompress_times = []

    image_bytes = create_test_image()

    for i in range(iterations):
        # Compress
        start_time = time.time()
        result = model.compress(image_bytes, compression_level="medium")
        compress_times.append(time.time() - start_time)

        # Decompress
        start_time = time.time()
        model.decompress(result.tokens)
        decompress_times.append(time.time() - start_time)

        if (i + 1) % 5 == 0:
            logger.info(f"  Completed {i + 1}/{iterations} iterations")

    # Calculate statistics
    def stats(times):
        times_sorted = sorted(times)
        return {
            'min': min(times),
            'max': max(times),
            'mean': sum(times) / len(times),
            'p50': times_sorted[len(times) // 2],
            'p95': times_sorted[int(len(times) * 0.95)],
            'p99': times_sorted[int(len(times) * 0.99)]
        }

    compress_stats = stats(compress_times)
    decompress_stats = stats(decompress_times)

    logger.info("✓ Benchmark complete")
    logger.info("")
    logger.info("Compression latency:")
    logger.info(f"  Mean: {compress_stats['mean']:.3f}s")
    logger.info(f"  P50:  {compress_stats['p50']:.3f}s")
    logger.info(f"  P95:  {compress_stats['p95']:.3f}s")
    logger.info(f"  P99:  {compress_stats['p99']:.3f}s")
    logger.info("")
    logger.info("Decompression latency:")
    logger.info(f"  Mean: {decompress_stats['mean']:.3f}s")
    logger.info(f"  P50:  {decompress_stats['p50']:.3f}s")
    logger.info(f"  P95:  {decompress_stats['p95']:.3f}s")
    logger.info(f"  P99:  {decompress_stats['p99']:.3f}s")
    logger.info("")

    # Check if targets met
    compress_target = 5.0  # seconds
    decompress_target = 3.0  # seconds

    if compress_stats['p95'] < compress_target:
        logger.info(f"✓ Compression P95 ({compress_stats['p95']:.3f}s) meets target (<{compress_target}s)")
    else:
        logger.warning(f"⚠ Compression P95 ({compress_stats['p95']:.3f}s) exceeds target (<{compress_target}s)")

    if decompress_stats['p95'] < decompress_target:
        logger.info(f"✓ Decompression P95 ({decompress_stats['p95']:.3f}s) meets target (<{decompress_target}s)")
    else:
        logger.warning(f"⚠ Decompression P95 ({decompress_stats['p95']:.3f}s) exceeds target (<{decompress_target}s)")


def main():
    parser = argparse.ArgumentParser(description="Test DeepSeek-OCR MCP Server")
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run performance benchmarks"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of benchmark iterations (default: 10)"
    )
    args = parser.parse_args()

    logger.info("=================================")
    logger.info("DeepSeek-OCR MCP Server Tests")
    logger.info("=================================")
    logger.info("")

    # Test 1: GPU
    if not test_gpu():
        logger.error("GPU test failed. Aborting.")
        sys.exit(1)
    logger.info("")

    # Test 2: Model loading
    model = test_model_loading()
    if model is None:
        logger.error("Model loading failed. Aborting.")
        sys.exit(1)
    logger.info("")

    # Test 3: Compression/decompression
    if not test_compression_decompression(model):
        logger.error("Compression/decompression test failed. Aborting.")
        sys.exit(1)
    logger.info("")

    # Test 4: Benchmark (optional)
    if args.benchmark:
        run_benchmark(model, iterations=args.iterations)
        logger.info("")

    logger.info("=================================")
    logger.info("✓ All tests passed!")
    logger.info("=================================")
    logger.info("")
    logger.info("Next step: Run the MCP server")
    logger.info("  python mcp_server.py")


if __name__ == "__main__":
    main()
