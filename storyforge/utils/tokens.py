"""Token counting utilities."""

from __future__ import annotations


def count_tokens_approximate(text: str) -> int:
    """Approximate token count using chars/4 heuristic."""
    return len(text) // 4


def count_tokens_tiktoken(text: str, model: str = "gpt-4") -> int:
    """Count tokens using tiktoken."""
    try:
        import tiktoken

        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except (ImportError, KeyError):
        return count_tokens_approximate(text)
