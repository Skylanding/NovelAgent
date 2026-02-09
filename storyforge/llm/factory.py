"""LLM backend factory — creates backends from configuration."""

from __future__ import annotations

from typing import Type

from storyforge.llm.base import LLMBackend, LLMConfig, ModelTier


class LLMFactory:
    """Creates LLM backend instances from configuration."""

    _providers: dict[str, Type[LLMBackend]] = {}

    @classmethod
    def _ensure_defaults(cls) -> None:
        if cls._providers:
            return
        from storyforge.llm.anthropic import AnthropicBackend
        from storyforge.llm.ollama import OllamaBackend
        from storyforge.llm.openai import OpenAIBackend

        cls._providers = {
            "ollama": OllamaBackend,
            "anthropic": AnthropicBackend,
            "openai": OpenAIBackend,
        }

    @classmethod
    def register_provider(
        cls, name: str, backend_class: Type[LLMBackend]
    ) -> None:
        """Register a custom LLM provider."""
        cls._providers[name] = backend_class

    @classmethod
    def create(cls, config: LLMConfig) -> LLMBackend:
        """Instantiate the appropriate backend from config."""
        cls._ensure_defaults()
        provider_cls = cls._providers.get(config.provider)
        if provider_cls is None:
            raise ValueError(
                f"Unknown LLM provider: {config.provider}. "
                f"Available: {list(cls._providers.keys())}"
            )
        return provider_cls(config)

    @classmethod
    def create_from_dict(cls, config_dict: dict) -> LLMBackend:
        """Create backend from a raw config dictionary."""
        tier = config_dict.get("tier", "small")
        if isinstance(tier, str):
            tier = ModelTier(tier)
        llm_config = LLMConfig(
            provider=config_dict["provider"],
            model=config_dict["model"],
            tier=tier,
            base_url=config_dict.get("base_url"),
            api_key=config_dict.get("api_key"),
            max_tokens=config_dict.get("max_tokens", 4096),
            default_temperature=config_dict.get("default_temperature", 0.7),
            requests_per_minute=config_dict.get("requests_per_minute", 60),
            context_window=config_dict.get("context_window", 8192),
        )
        return cls.create(llm_config)
