"""Tests for ContextWindowManager and ContextBudget."""

import pytest

from storyforge.memory.context_window import ContextBudget, ContextWindowManager


class TestContextBudget:
    def test_available_for_dynamic(self):
        budget = ContextBudget(
            total_tokens=4096,
            system_prompt_tokens=500,
            fixed_context_tokens=300,
            generation_reserve_tokens=512,
        )
        assert budget.available_for_dynamic == 4096 - 500 - 300 - 512

    def test_available_never_negative(self):
        budget = ContextBudget(
            total_tokens=100,
            system_prompt_tokens=500,
            fixed_context_tokens=300,
            generation_reserve_tokens=512,
        )
        assert budget.available_for_dynamic == 0


class TestContextWindowManager:
    def setup_method(self):
        # Simple token counter: 1 token per 4 chars
        self.mgr = ContextWindowManager(
            max_context_tokens=1000,
            token_counter=lambda text: len(text) // 4,
        )

    def test_allocate_budget(self):
        budget = self.mgr.allocate_budget(
            system_prompt="a" * 400,   # 100 tokens
            fixed_context="b" * 200,   # 50 tokens
            generation_reserve=100,
        )
        assert budget.total_tokens == 1000
        assert budget.system_prompt_tokens == 100
        assert budget.fixed_context_tokens == 50
        assert budget.generation_reserve_tokens == 100
        assert budget.available_for_dynamic == 750

    def test_fit_to_budget_all_fit(self):
        items = ["short", "also short", "tiny"]
        result = self.mgr.fit_to_budget(items, budget_tokens=100)
        assert result == items

    def test_fit_to_budget_partial(self):
        items = ["a" * 40, "b" * 40, "c" * 40]  # Each ~10 tokens
        result = self.mgr.fit_to_budget(items, budget_tokens=20)
        assert len(result) == 2
        assert result == ["a" * 40, "b" * 40]

    def test_fit_to_budget_empty(self):
        result = self.mgr.fit_to_budget([], budget_tokens=100)
        assert result == []

    def test_fit_to_budget_first_too_large(self):
        items = ["a" * 1000]  # 250 tokens
        result = self.mgr.fit_to_budget(items, budget_tokens=10)
        assert result == []

    def test_truncate_text_within_budget(self):
        text = "Hello world"
        result = self.mgr.truncate_text(text, budget_tokens=100)
        assert result == text

    def test_truncate_text_exceeds_budget(self):
        text = "a" * 1000
        result = self.mgr.truncate_text(text, budget_tokens=10)
        assert len(result) == 43  # 10*4 + len("...")
        assert result.endswith("...")
