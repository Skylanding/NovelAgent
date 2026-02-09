"""Base agent abstraction for all StoryForge agents."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from storyforge.events.bus import EventBus
from storyforge.events.types import Event, EventType
from storyforge.llm.base import LLMBackend
from storyforge.memory.base import MemoryStore
from storyforge.memory.context_window import ContextWindowManager

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""

    name: str
    role: str
    llm_backend_id: str
    system_prompt_template: str = ""
    prompt_variables: dict[str, Any] = field(default_factory=dict)
    max_context_tokens: int = 4096
    temperature: float = 0.7
    subscriptions: list[EventType] = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base class for all StoryForge agents."""

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMBackend,
        memory: MemoryStore,
        event_bus: EventBus,
        prompt_dir: Optional[Path] = None,
    ) -> None:
        self.config = config
        self.llm = llm
        self.memory = memory
        self.event_bus = event_bus
        self.prompt_dir = prompt_dir
        self._system_prompt: str = ""
        self._conversation_history: list[dict[str, str]] = []
        self._jinja_env: Optional[Environment] = None
        if prompt_dir and prompt_dir.exists():
            self._jinja_env = Environment(
                loader=FileSystemLoader(str(prompt_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        self._context_mgr = ContextWindowManager(
            max_context_tokens=config.max_context_tokens,
            token_counter=lambda text: len(text) // 4,
        )

    async def initialize(self) -> None:
        """Set up subscriptions and load initial state."""
        # Register directed handler
        await self.event_bus.subscribe_directed(
            self.config.name, self.handle_event
        )
        # Register broadcast subscriptions
        for event_type in self.config.subscriptions:
            await self.event_bus.subscribe(event_type, self.handle_event)
        # Load system prompt
        await self._load_system_prompt()

    @abstractmethod
    async def handle_event(self, event: Event) -> Optional[Event]:
        """Process an incoming event. Return a response event or None."""
        ...

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Send prompt to LLM with system prompt and return response."""
        system_content = self._system_prompt
        # Prepend language instruction if configured
        language = self.config.prompt_variables.get("language", "")
        if language and language.lower() != "english":
            system_content = (
                f"IMPORTANT: You MUST write ALL prose, dialogue, descriptions, "
                f"titles, and narrative content in {language}. "
                f"Only keep JSON keys and structural labels in English.\n\n"
                + system_content
            )
        messages = [{"role": "system", "content": system_content}]
        # Add conversation history (limited)
        messages.extend(self._conversation_history[-10:])
        messages.append({"role": "user", "content": prompt})

        response = await self.llm.generate(
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens"),
        )

        # Track history (keep last 20 exchanges to bound memory usage)
        self._conversation_history.append(
            {"role": "user", "content": prompt}
        )
        self._conversation_history.append(
            {"role": "assistant", "content": response.content}
        )
        if len(self._conversation_history) > 20:
            self._conversation_history = self._conversation_history[-20:]

        return response.content

    async def _load_system_prompt(self) -> None:
        """Render the system prompt from Jinja2 template."""
        if self._jinja_env and self.config.system_prompt_template:
            template = self._jinja_env.get_template(
                self.config.system_prompt_template
            )
            self._system_prompt = template.render(
                **self.config.prompt_variables
            )
        elif self.config.prompt_variables.get("system_prompt"):
            self._system_prompt = self.config.prompt_variables["system_prompt"]

    def _render_template(self, template_name: str, **variables: Any) -> str:
        """Load and render a Jinja2 prompt template."""
        if self._jinja_env is None:
            raise RuntimeError(
                f"No prompt directory configured for agent {self.config.name}"
            )
        template = self._jinja_env.get_template(template_name)
        return template.render(**variables)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()


def strip_json_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ```) from LLM responses."""
    text = text.strip()
    # Remove ```json or ``` prefix and ``` suffix
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()
