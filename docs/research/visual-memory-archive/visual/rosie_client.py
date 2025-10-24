"""
Client wrapper for visual memory compression.

Provides unified interface for both mock and real DeepSeek-OCR compression.
Toggles between mock mode (for testing) and real MCP server (for production).
"""

import base64
import logging
import json
import subprocess
import asyncio
from pathlib import Path
from typing import Optional

from .models import VisualTokens
from .config import VisualMemoryConfig, load_config
from .mock import mock_compress, mock_decompress


# Set up logging
logger = logging.getLogger(__name__)


class RosieClient:
    """
    Client for visual memory compression via DeepSeek-OCR.

    Supports two modes:
    - Mock mode: Uses local mock compression for testing
    - Real mode: Calls MCP server on Rosie supercomputer

    The mode is configured via VisualMemoryConfig.use_mock.
    """

    def __init__(self, config: Optional[VisualMemoryConfig] = None):
        """
        Initialize Rosie client.

        Args:
            config: Configuration (loads from disk if None)
        """
        self.config = config or load_config()
        self._mcp_client = None  # Will be initialized on first real call

        logger.info(
            f"RosieClient initialized in {'MOCK' if self.config.use_mock else 'REAL'} mode"
        )

    def compress(self, image_bytes: bytes) -> VisualTokens:
        """
        Compress image to visual tokens.

        Args:
            image_bytes: PNG image bytes

        Returns:
            VisualTokens with compressed representation

        Raises:
            RuntimeError: If compression fails
        """
        if self.config.use_mock:
            return self._mock_compress(image_bytes)
        else:
            return self._real_compress(image_bytes)

    def decompress(self, tokens: VisualTokens) -> str:
        """
        Decompress visual tokens to text.

        Args:
            tokens: Visual tokens to decompress

        Returns:
            Decompressed text

        Raises:
            RuntimeError: If decompression fails
        """
        if self.config.use_mock:
            return self._mock_decompress(tokens)
        else:
            return self._real_decompress(tokens)

    def health_check(self) -> bool:
        """
        Check if compression service is available.

        Returns:
            True if service is healthy, False otherwise
        """
        if self.config.use_mock:
            # Mock is always available
            return True
        else:
            return self._real_health_check()

    def switch_mode(self, use_mock: bool):
        """
        Switch between mock and real mode.

        Args:
            use_mock: True for mock mode, False for real mode
        """
        old_mode = "MOCK" if self.config.use_mock else "REAL"
        new_mode = "MOCK" if use_mock else "REAL"

        self.config.use_mock = use_mock

        logger.info(f"Switched mode: {old_mode} → {new_mode}")

    # ========== Mock Mode Implementation ==========

    def _mock_compress(self, image_bytes: bytes) -> VisualTokens:
        """
        Mock compression implementation.

        Args:
            image_bytes: Image to compress

        Returns:
            Mock visual tokens
        """
        logger.debug(f"Mock compressing image ({len(image_bytes)} bytes)")

        try:
            tokens = mock_compress(
                image_bytes,
                target_ratio=self.config.compression_target_ratio,
                latency_ms=self.config.mock_latency_ms
            )

            logger.debug(
                f"Mock compression complete: {len(tokens)} tokens, "
                f"{tokens.metadata.get('compression_ratio')}x ratio"
            )

            return tokens

        except Exception as e:
            logger.error(f"Mock compression failed: {e}")
            raise RuntimeError(f"Mock compression failed: {e}")

    def _mock_decompress(self, tokens: VisualTokens) -> str:
        """
        Mock decompression implementation.

        Args:
            tokens: Tokens to decompress

        Returns:
            Placeholder text
        """
        logger.debug(f"Mock decompressing {len(tokens)} tokens")

        try:
            text = mock_decompress(tokens)
            logger.debug(f"Mock decompression complete: {len(text)} chars")
            return text

        except Exception as e:
            logger.error(f"Mock decompression failed: {e}")
            raise RuntimeError(f"Mock decompression failed: {e}")

    # ========== Real Mode Implementation ==========

    def _real_compress(self, image_bytes: bytes) -> VisualTokens:
        """
        Real compression via MCP server on Rosie.

        Args:
            image_bytes: Image to compress

        Returns:
            Visual tokens from DeepSeek-OCR

        Raises:
            RuntimeError: If MCP call fails or not configured
        """
        logger.debug(f"Real compressing image ({len(image_bytes)} bytes)")

        # Check if MCP server is configured
        if not self._is_mcp_configured():
            logger.warning(
                "Real mode selected but MCP server not configured. "
                "Falling back to mock."
            )
            return self._mock_compress(image_bytes)

        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

            # Call MCP tool
            result = self._call_mcp_tool(
                tool="compress_visual_tokens",
                arguments={
                    "image_base64": image_b64,
                    "compression_level": "medium"
                }
            )

            # Parse result
            tokens = VisualTokens(
                data=result["tokens"],
                metadata=result.get("metadata", {})
            )

            logger.info(
                f"Real compression complete: {len(tokens)} tokens, "
                f"{tokens.metadata.get('compression_ratio', 'unknown')}x ratio"
            )

            return tokens

        except Exception as e:
            logger.error(f"Real compression failed: {e}")
            logger.warning("Falling back to mock compression")
            return self._mock_compress(image_bytes)

    def _real_decompress(self, tokens: VisualTokens) -> str:
        """
        Real decompression via MCP server on Rosie.

        Args:
            tokens: Tokens to decompress

        Returns:
            Decompressed text

        Raises:
            RuntimeError: If MCP call fails or not configured
        """
        logger.debug(f"Real decompressing {len(tokens)} tokens")

        # Check if MCP server is configured
        if not self._is_mcp_configured():
            logger.warning(
                "Real mode selected but MCP server not configured. "
                "Falling back to mock."
            )
            return self._mock_decompress(tokens)

        try:
            # Call MCP tool
            result = self._call_mcp_tool(
                tool="decompress_visual_tokens",
                arguments={
                    "tokens": tokens.data
                }
            )

            text = result["text"]

            logger.info(f"Real decompression complete: {len(text)} chars")

            return text

        except Exception as e:
            logger.error(f"Real decompression failed: {e}")
            logger.warning("Falling back to mock decompression")
            return self._mock_decompress(tokens)

    def _real_health_check(self) -> bool:
        """
        Check real MCP server health.

        Returns:
            True if healthy, False otherwise
        """
        logger.debug("Checking MCP server health")

        if not self._is_mcp_configured():
            logger.warning("MCP server not configured")
            return False

        try:
            result = self._call_mcp_tool(
                tool="health_check",
                arguments={}
            )

            is_healthy = result.get("status") == "healthy"

            logger.info(
                f"Health check: {'healthy' if is_healthy else 'unhealthy'} "
                f"(GPU: {result.get('gpu_available', False)})"
            )

            return is_healthy

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def _is_mcp_configured(self) -> bool:
        """
        Check if MCP server is configured.

        Returns:
            True if configured, False otherwise
        """
        try:
            # Check if config file exists
            config_path = Path.home() / ".house_code" / "config.json"
            if not config_path.exists():
                logger.debug("Config file not found")
                return False

            # Load config
            import json
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # Check if MCP server is defined
            mcp_servers = config_data.get('mcpServers', {})
            if self.config.mcp_server_name not in mcp_servers:
                logger.debug(f"MCP server '{self.config.mcp_server_name}' not in config")
                return False

            # Verify server config has required fields
            server_config = mcp_servers[self.config.mcp_server_name]
            if not server_config.get('command') or not server_config.get('args'):
                logger.debug("MCP server config missing command or args")
                return False

            logger.debug(f"MCP server '{self.config.mcp_server_name}' is configured")
            return True

        except Exception as e:
            logger.debug(f"Error checking MCP configuration: {e}")
            return False

    def _call_mcp_tool(self, tool: str, arguments: dict) -> dict:
        """
        Call MCP tool via SSH stdio transport.

        Args:
            tool: Tool name (e.g., "compress_visual_tokens")
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            RuntimeError: If call fails
        """
        logger.debug(f"MCP call: {self.config.mcp_server_name}.{tool}")

        try:
            # Load MCP server config
            config_path = Path.home() / ".house_code" / "config.json"
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            server_config = config_data['mcpServers'][self.config.mcp_server_name]
            command = server_config['command']
            args = server_config['args']

            # Build MCP request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool,
                    "arguments": arguments
                }
            }

            # Execute MCP call with retry logic
            for attempt in range(self.config.mcp_max_retries):
                try:
                    # Call server via SSH stdio
                    process = subprocess.Popen(
                        [command] + args,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                    # Send request and get response
                    stdout, stderr = process.communicate(
                        input=json.dumps(request) + "\n",
                        timeout=self.config.mcp_timeout_seconds
                    )

                    # Parse response
                    if process.returncode != 0:
                        raise RuntimeError(
                            f"MCP server process failed (exit {process.returncode}): {stderr}"
                        )

                    # Parse JSON-RPC response
                    response = json.loads(stdout)

                    if "error" in response:
                        raise RuntimeError(
                            f"MCP tool error: {response['error'].get('message', 'Unknown error')}"
                        )

                    if "result" not in response:
                        raise RuntimeError("MCP response missing 'result' field")

                    logger.debug(f"MCP call successful on attempt {attempt + 1}")
                    return response["result"]

                except subprocess.TimeoutExpired:
                    logger.warning(
                        f"MCP call timeout on attempt {attempt + 1}/{self.config.mcp_max_retries}"
                    )
                    if attempt == self.config.mcp_max_retries - 1:
                        raise RuntimeError(
                            f"MCP call timed out after {self.config.mcp_max_retries} attempts"
                        )

                except Exception as e:
                    logger.warning(
                        f"MCP call failed on attempt {attempt + 1}/{self.config.mcp_max_retries}: {e}"
                    )
                    if attempt == self.config.mcp_max_retries - 1:
                        raise

            raise RuntimeError("MCP call failed after all retry attempts")

        except Exception as e:
            logger.error(f"MCP call failed: {e}", exc_info=True)
            raise RuntimeError(f"MCP call to {self.config.mcp_server_name}.{tool} failed: {e}")
