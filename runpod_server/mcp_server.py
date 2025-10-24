#!/usr/bin/env python3
"""
MCP Server for DeepSeek-OCR Visual Memory Compression.

Provides three tools:
1. compress_visual_tokens - Compress images to visual tokens
2. decompress_visual_tokens - Decompress tokens to text
3. health_check - Verify GPU and model availability

Usage:
  python mcp_server.py

Connects via SSH stdio transport from House Code client.
"""

import sys
import json
import base64
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from inference import DeepSeekOCR, ModelNotLoadedError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/workspace/deepseek_mcp/server.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Initialize server
server = Server("deepseek-ocr-runpod")

# Global model instance (lazy-loaded)
_model = None


def get_model() -> DeepSeekOCR:
    """Get or initialize model instance."""
    global _model
    if _model is None:
        logger.info("Loading DeepSeek-OCR model...")
        _model = DeepSeekOCR()
        logger.info("Model loaded successfully")
    return _model


@server.tool()
async def compress_visual_tokens(
    image_base64: str,
    compression_level: str = "medium"
) -> dict:
    """
    Compress an image to visual tokens using DeepSeek-OCR.

    Args:
        image_base64: Base64-encoded PNG image
        compression_level: "low", "medium", or "high" (affects quality vs size)

    Returns:
        dict with keys:
            - tokens: list of compressed visual tokens
            - compression_ratio: float indicating compression ratio
            - metadata: dict with model info and settings
    """
    logger.info(f"Compressing image (level: {compression_level})")

    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_base64)
        logger.debug(f"Decoded image: {len(image_bytes)} bytes")

        # Get model
        model = get_model()

        # Compress
        result = model.compress(
            image_bytes,
            compression_level=compression_level
        )

        logger.info(
            f"Compression complete: {len(result.tokens)} tokens, "
            f"{result.compression_ratio:.2f}x ratio"
        )

        return {
            "tokens": result.tokens,
            "compression_ratio": result.compression_ratio,
            "metadata": {
                "model": "deepseek-vl2",
                "compression_level": compression_level,
                "original_size_bytes": len(image_bytes),
                "token_count": len(result.tokens)
            }
        }

    except Exception as e:
        logger.error(f"Compression failed: {e}", exc_info=True)
        raise


@server.tool()
async def decompress_visual_tokens(tokens: list) -> dict:
    """
    Decompress visual tokens back to text using DeepSeek-OCR.

    Args:
        tokens: List of visual tokens (from compress_visual_tokens)

    Returns:
        dict with keys:
            - text: str of decompressed text
            - confidence: float indicating reconstruction confidence
    """
    logger.info(f"Decompressing {len(tokens)} tokens")

    try:
        # Get model
        model = get_model()

        # Decompress
        result = model.decompress(tokens)

        logger.info(
            f"Decompression complete: {len(result.text)} chars, "
            f"{result.confidence:.2%} confidence"
        )

        return {
            "text": result.text,
            "confidence": result.confidence
        }

    except Exception as e:
        logger.error(f"Decompression failed: {e}", exc_info=True)
        raise


@server.tool()
async def health_check() -> dict:
    """
    Check server health and GPU availability.

    Returns:
        dict with keys:
            - status: "healthy" or "unhealthy"
            - gpu_available: bool
            - gpu_count: int
            - gpu_name: str or None
            - model_loaded: bool
    """
    logger.info("Running health check")

    try:
        import torch

        gpu_available = torch.cuda.is_available()
        gpu_count = torch.cuda.device_count() if gpu_available else 0
        gpu_name = torch.cuda.get_device_name(0) if gpu_available else None

        # Try to load model
        try:
            model = get_model()
            model_loaded = True
        except Exception as e:
            logger.warning(f"Model not loaded: {e}")
            model_loaded = False

        is_healthy = gpu_available and model_loaded

        result = {
            "status": "healthy" if is_healthy else "unhealthy",
            "gpu_available": gpu_available,
            "gpu_count": gpu_count,
            "gpu_name": gpu_name,
            "model_loaded": model_loaded
        }

        logger.info(f"Health check result: {result}")
        return result

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def main():
    """Run MCP server with stdio transport."""
    logger.info("Starting DeepSeek-OCR MCP Server...")
    logger.info("Waiting for connections via stdio...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
