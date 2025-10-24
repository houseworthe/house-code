"""
Configuration management for visual memory system.

Handles loading/saving configuration from ~/.house_code/config.json
with sensible defaults.
"""

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional


@dataclass
class VisualMemoryConfig:
    """
    Configuration for visual memory compression system.

    Attributes:
        use_mock: Toggle between mock and real MCP server
        cache_max_entries: Maximum number of entries in LRU cache
        cache_max_size_mb: Maximum cache size in megabytes
        cache_path: Path to cache persistence file
        compression_target_ratio: Target compression ratio (for estimation)
        mock_latency_ms: Simulated latency for mock compression (ms)
        mcp_server_name: Name of MCP server in config (for real mode)
        enable_auto_compression: Enable automatic compression during GC
        compression_age_threshold: Minimum turns old before compression
        mcp_timeout_seconds: Timeout for MCP calls in seconds
        mcp_max_retries: Maximum number of retry attempts for failed MCP calls
        runpod_ssh_host: SSH host for RunPod (optional, from MCP config)
        runpod_ssh_port: SSH port for RunPod (optional, from MCP config)
        runpod_ssh_key_path: Path to SSH private key (optional, from MCP config)
    """
    use_mock: bool = True
    cache_max_entries: int = 50
    cache_max_size_mb: int = 100
    cache_path: str = "~/.house_code/visual_cache.json"
    compression_target_ratio: float = 8.0
    mock_latency_ms: int = 100
    mcp_server_name: str = "deepseek-ocr-runpod"
    enable_auto_compression: bool = True
    compression_age_threshold: int = 10
    mcp_timeout_seconds: int = 10
    mcp_max_retries: int = 3
    runpod_ssh_host: Optional[str] = None
    runpod_ssh_port: Optional[int] = None
    runpod_ssh_key_path: Optional[str] = None

    def __post_init__(self):
        """Expand paths after initialization."""
        self.cache_path = os.path.expanduser(self.cache_path)


def get_config_dir() -> Path:
    """
    Get the House Code configuration directory.

    Returns:
        Path to ~/.house_code/
    """
    config_dir = Path.home() / ".house_code"
    return config_dir


def ensure_config_dir() -> Path:
    """
    Ensure the configuration directory exists.

    Returns:
        Path to config directory
    """
    config_dir = get_config_dir()
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """
    Get path to main config file.

    Returns:
        Path to ~/.house_code/config.json
    """
    return get_config_dir() / "config.json"


def load_config() -> VisualMemoryConfig:
    """
    Load configuration from ~/.house_code/config.json.

    Creates default config if file doesn't exist.

    Returns:
        VisualMemoryConfig instance
    """
    config_path = get_config_path()

    # Return defaults if config doesn't exist
    if not config_path.exists():
        return get_default_config()

    try:
        with open(config_path, 'r') as f:
            data = json.load(f)

        # Extract visual_memory section if it exists
        visual_config = data.get('visual_memory', {})

        # Merge with defaults
        default = asdict(get_default_config())
        default.update(visual_config)

        return VisualMemoryConfig(**default)

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Warning: Failed to load config: {e}")
        print("Using default configuration")
        return get_default_config()


def save_config(config: VisualMemoryConfig) -> bool:
    """
    Save configuration to ~/.house_code/config.json.

    Merges with existing config file to preserve other settings.

    Args:
        config: Configuration to save

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        ensure_config_dir()
        config_path = get_config_path()

        # Load existing config or start with empty dict
        existing_data = {}
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # Update visual_memory section
        existing_data['visual_memory'] = asdict(config)

        # Save merged config
        with open(config_path, 'w') as f:
            json.dump(existing_data, f, indent=2)

        return True

    except (IOError, OSError) as e:
        print(f"Error: Failed to save config: {e}")
        return False


def get_default_config() -> VisualMemoryConfig:
    """
    Get default configuration.

    Returns:
        VisualMemoryConfig with default values
    """
    return VisualMemoryConfig()


def update_config(
    use_mock: Optional[bool] = None,
    cache_max_entries: Optional[int] = None,
    cache_max_size_mb: Optional[int] = None,
    **kwargs
) -> VisualMemoryConfig:
    """
    Update configuration with new values.

    Loads existing config, updates specified fields, and saves.

    Args:
        use_mock: Toggle mock mode
        cache_max_entries: Update cache entry limit
        cache_max_size_mb: Update cache size limit
        **kwargs: Additional fields to update

    Returns:
        Updated configuration
    """
    config = load_config()

    if use_mock is not None:
        config.use_mock = use_mock
    if cache_max_entries is not None:
        config.cache_max_entries = cache_max_entries
    if cache_max_size_mb is not None:
        config.cache_max_size_mb = cache_max_size_mb

    # Update any additional kwargs
    for key, value in kwargs.items():
        if hasattr(config, key) and value is not None:
            setattr(config, key, value)

    save_config(config)
    return config


def reset_config() -> VisualMemoryConfig:
    """
    Reset configuration to defaults and save.

    Returns:
        Default configuration
    """
    config = get_default_config()
    save_config(config)
    return config
