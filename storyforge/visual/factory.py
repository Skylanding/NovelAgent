"""Visual backend factory — creates backends from configuration."""

from __future__ import annotations

from typing import Type

from storyforge.visual.base import VisualBackend, VisualConfig


class VisualFactory:
    """Creates visual backend instances from configuration."""

    _providers: dict[str, Type[VisualBackend]] = {}

    @classmethod
    def _ensure_defaults(cls) -> None:
        if cls._providers:
            return
        from storyforge.visual.openai_image import DallE3Backend
        from storyforge.visual.openai_video import Sora2Backend

        cls._providers = {
            "openai_image": DallE3Backend,
            "openai_video": Sora2Backend,
        }

    @classmethod
    def register_provider(
        cls, name: str, backend_class: Type[VisualBackend]
    ) -> None:
        cls._providers[name] = backend_class

    @classmethod
    def create(cls, config: VisualConfig) -> VisualBackend:
        cls._ensure_defaults()
        provider_cls = cls._providers.get(config.provider)
        if provider_cls is None:
            raise ValueError(
                f"Unknown visual provider: {config.provider}. "
                f"Available: {list(cls._providers.keys())}"
            )
        return provider_cls(config)

    @classmethod
    def create_from_dict(cls, config_dict: dict) -> VisualBackend:
        visual_config = VisualConfig(
            provider=config_dict["provider"],
            model=config_dict["model"],
            api_key=config_dict.get("api_key"),
            base_url=config_dict.get("base_url"),
            requests_per_minute=config_dict.get("requests_per_minute", 10),
            default_size=config_dict.get("default_size", "1024x1024"),
            default_quality=config_dict.get("default_quality", "standard"),
            default_style=config_dict.get("default_style", "natural"),
        )
        return cls.create(visual_config)
