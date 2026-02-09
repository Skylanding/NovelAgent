"""Agent registry for dynamic agent type discovery and instantiation."""

from __future__ import annotations

from typing import Callable, Type

from storyforge.agents.base import BaseAgent


class AgentRegistry:
    """Registry for dynamically discovering and instantiating agent types."""

    _agent_types: dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register(cls, role: str) -> Callable[[Type[BaseAgent]], Type[BaseAgent]]:
        """Decorator to register an agent class for a given role."""

        def decorator(agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
            cls._agent_types[role] = agent_class
            return agent_class

        return decorator

    @classmethod
    def get(cls, role: str) -> Type[BaseAgent]:
        """Get an agent class by role name."""
        if role not in cls._agent_types:
            raise ValueError(
                f"Unknown agent role: {role}. "
                f"Available: {list(cls._agent_types.keys())}"
            )
        return cls._agent_types[role]

    @classmethod
    def list_roles(cls) -> list[str]:
        """Return all registered agent role names."""
        return list(cls._agent_types.keys())
