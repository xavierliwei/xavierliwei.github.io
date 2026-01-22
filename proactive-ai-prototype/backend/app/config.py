"""
Configuration Management.

Handles loading configuration from environment variables and .env files.
Provides type-safe access to application settings.

Environment Variables:
    CHAT_PROVIDER: "mock" or "claude" (default: "mock")
    CLAUDE_API_KEY: Anthropic API key (required if CHAT_PROVIDER=claude)
    CLAUDE_MODEL: Claude model ID (default: claude-haiku-3-5-20241022)
    MAX_TOKENS: Maximum tokens in response (default: 1024)
    TEMPERATURE: Sampling temperature 0-1 (default: 0.7)
"""

import os
from typing import Optional, Literal
from pathlib import Path


class Config:
    """Application configuration."""

    def __init__(self):
        """Initialize configuration from environment."""
        # Load .env file if it exists
        self._load_env_file()

        # Chat provider settings
        self.chat_provider: Literal["mock", "claude"] = os.getenv(
            "CHAT_PROVIDER", "mock"
        ).lower()

        if self.chat_provider not in ["mock", "claude"]:
            raise ValueError(
                f"Invalid CHAT_PROVIDER: {self.chat_provider}. "
                f"Must be 'mock' or 'claude'"
            )

        # Claude API settings
        self.claude_api_key: Optional[str] = os.getenv("CLAUDE_API_KEY")
        self.claude_model: str = os.getenv(
            "CLAUDE_MODEL",
            "claude-haiku-3-5-20241022"
        )

        # Validate Claude settings if using Claude provider
        if self.chat_provider == "claude" and not self.claude_api_key:
            raise ValueError(
                "CLAUDE_API_KEY must be set when CHAT_PROVIDER=claude. "
                "Get your API key from: https://console.anthropic.com/"
            )

        # Generation parameters
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "1024"))
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.7"))

        # Validate parameters
        if self.max_tokens < 1 or self.max_tokens > 4096:
            raise ValueError("MAX_TOKENS must be between 1 and 4096")

        if self.temperature < 0 or self.temperature > 1:
            raise ValueError("TEMPERATURE must be between 0 and 1")

    def _load_env_file(self):
        """Load environment variables from .env file if it exists."""
        try:
            from dotenv import load_dotenv
            # Look for .env file in backend directory
            env_path = Path(__file__).parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                print(f"Loaded environment from: {env_path}")
        except ImportError:
            # python-dotenv not installed, skip
            pass

    def is_using_claude(self) -> bool:
        """Check if Claude API is being used."""
        return self.chat_provider == "claude"

    def is_using_mock(self) -> bool:
        """Check if mock provider is being used."""
        return self.chat_provider == "mock"

    def get_provider_info(self) -> dict:
        """Get information about the current provider."""
        if self.is_using_mock():
            return {
                "provider": "mock",
                "model": "mock-v1",
                "description": "Mock responses for development"
            }
        else:
            from .chat_provider import ClaudeChatProvider
            models = ClaudeChatProvider.get_available_models()
            model_info = models.get(self.claude_model, {})
            return {
                "provider": "claude",
                "model": self.claude_model,
                "description": model_info.get("description", ""),
                "input_cost_per_mtok": model_info.get("input_cost"),
                "output_cost_per_mtok": model_info.get("output_cost")
            }

    def __repr__(self) -> str:
        """String representation of config."""
        api_key_display = (
            f"{self.claude_api_key[:8]}..." if self.claude_api_key else "not set"
        )
        return (
            f"Config(provider={self.chat_provider}, "
            f"model={self.claude_model}, "
            f"api_key={api_key_display})"
        )


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.

    The config is loaded once and cached. To reload, call reload_config().
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """
    Reload configuration from environment.

    Useful for testing or when environment changes.
    """
    global _config
    _config = Config()
    return _config
