"""
DeepSeek-OCR inference wrapper for visual memory compression.

Handles model loading, compression, and decompression using DeepSeek-VL2.
"""

import io
import base64
import logging
from dataclasses import dataclass
from typing import List
from PIL import Image

import torch
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger(__name__)


class ModelNotLoadedError(Exception):
    """Raised when model operations attempted before loading."""
    pass


@dataclass
class CompressionResult:
    """Result of compression operation."""
    tokens: List[int]
    compression_ratio: float


@dataclass
class DecompressionResult:
    """Result of decompression operation."""
    text: str
    confidence: float


class DeepSeekOCR:
    """
    DeepSeek-OCR model wrapper for visual memory compression.

    Loads DeepSeek-VL2 model and provides compress/decompress operations.
    """

    MODEL_PATH = "/workspace/models/deepseek-vl2"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    def __init__(self):
        """Initialize model (lazy-loads on first use)."""
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load DeepSeek-VL2 model and tokenizer."""
        logger.info(f"Loading model from {self.MODEL_PATH}")
        logger.info(f"Using device: {self.DEVICE}")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.MODEL_PATH,
                trust_remote_code=True
            )

            self.model = AutoModel.from_pretrained(
                self.MODEL_PATH,
                torch_dtype=torch.float16 if self.DEVICE == "cuda" else torch.float32,
                device_map="auto",
                trust_remote_code=True
            )

            self.model.eval()

            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise ModelNotLoadedError(f"Could not load DeepSeek-VL2: {e}")

    def compress(
        self,
        image_bytes: bytes,
        compression_level: str = "medium"
    ) -> CompressionResult:
        """
        Compress image to visual tokens.

        Args:
            image_bytes: PNG image bytes
            compression_level: Quality setting ("low", "medium", "high")

        Returns:
            CompressionResult with tokens and ratio
        """
        if self.model is None:
            raise ModelNotLoadedError("Model not loaded")

        logger.debug(f"Compressing image ({len(image_bytes)} bytes)")

        # Load image
        image = Image.open(io.BytesIO(image_bytes))

        # Process with model
        with torch.no_grad():
            # Use DeepSeek-VL2's OCR capability
            inputs = self.tokenizer(
                images=image,
                return_tensors="pt"
            ).to(self.DEVICE)

            # Get visual tokens
            outputs = self.model(**inputs)
            tokens = outputs.last_hidden_state

            # Compress to token indices
            token_ids = tokens.argmax(dim=-1).squeeze().cpu().tolist()

        # Calculate compression ratio
        original_size = len(image_bytes)
        compressed_size = len(token_ids) * 2  # Rough estimate: 2 bytes per token
        compression_ratio = original_size / compressed_size if compressed_size > 0 else 0

        logger.debug(
            f"Compressed to {len(token_ids)} tokens "
            f"({compression_ratio:.2f}x ratio)"
        )

        return CompressionResult(
            tokens=token_ids,
            compression_ratio=compression_ratio
        )

    def decompress(self, tokens: List[int]) -> DecompressionResult:
        """
        Decompress visual tokens to text.

        Args:
            tokens: Token IDs from compress()

        Returns:
            DecompressionResult with text and confidence
        """
        if self.model is None:
            raise ModelNotLoadedError("Model not loaded")

        logger.debug(f"Decompressing {len(tokens)} tokens")

        # Decode tokens
        with torch.no_grad():
            text = self.tokenizer.decode(tokens, skip_special_tokens=True)

        # Calculate confidence (placeholder - DeepSeek-VL2 doesn't provide this directly)
        confidence = 0.95  # Assume high confidence for successful decode

        logger.debug(f"Decompressed to {len(text)} characters")

        return DecompressionResult(
            text=text,
            confidence=confidence
        )
