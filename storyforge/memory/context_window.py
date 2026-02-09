"""Context window budget manager for fitting content into small models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ContextBudget:
    """Tracks token allocation within a context window."""

    total_tokens: int
    system_prompt_tokens: int = 0
    fixed_context_tokens: int = 0
    generation_reserve_tokens: int = 512

    @property
    def available_for_dynamic(self) -> int:
        """Tokens remaining for dynamic content (memories, scene context)."""
        return max(
            0,
            self.total_tokens
            - self.system_prompt_tokens
            - self.fixed_context_tokens
            - self.generation_reserve_tokens,
        )


class ContextWindowManager:
    """Manages context window budgets, especially for small models."""

    def __init__(
        self,
        max_context_tokens: int,
        token_counter: Callable[[str], int],
    ) -> None:
        self._max_tokens = max_context_tokens
        self._count = token_counter

    def allocate_budget(
        self,
        system_prompt: str,
        fixed_context: str,
        generation_reserve: int = 512,
    ) -> ContextBudget:
        """Calculate how many tokens remain for dynamic content."""
        return ContextBudget(
            total_tokens=self._max_tokens,
            system_prompt_tokens=self._count(system_prompt),
            fixed_context_tokens=self._count(fixed_context),
            generation_reserve_tokens=generation_reserve,
        )

    def fit_to_budget(
        self,
        items: list[str],
        budget_tokens: int,
    ) -> list[str]:
        """Select items that fit within the budget, preserving order."""
        selected: list[str] = []
        used = 0
        for item in items:
            cost = self._count(item)
            if used + cost <= budget_tokens:
                selected.append(item)
                used += cost
            else:
                break
        return selected

    def truncate_text(self, text: str, budget_tokens: int) -> str:
        """Hard-truncate text to fit within a token budget."""
        # Approximate: cut at 4 chars per token
        max_chars = budget_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."
