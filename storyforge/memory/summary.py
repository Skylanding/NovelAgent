"""LLM-powered summarization utilities for context compression."""

from __future__ import annotations

from storyforge.llm.base import LLMBackend


class MemorySummarizer:
    """Compresses long context into summaries to fit context windows."""

    def __init__(self, llm: LLMBackend) -> None:
        self._llm = llm

    async def summarize_chapter(
        self, chapter_text: str, max_tokens: int = 500
    ) -> str:
        """Create a concise chapter summary for memory."""
        response = await self._llm.generate(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise summarizer. Create a concise summary "
                        "that captures: key plot events, character actions and "
                        "emotional changes, world details revealed, and any "
                        "unresolved threads. Use bullet points."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Summarize this chapter:\n\n{chapter_text}",
                },
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.content

    async def summarize_conversation(
        self, messages: list[dict[str, str]], max_tokens: int = 300
    ) -> str:
        """Summarize a conversation history to compress context."""
        conversation = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )
        response = await self._llm.generate(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize this conversation concisely, preserving "
                        "key decisions, facts, and context."
                    ),
                },
                {"role": "user", "content": conversation},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.content

    async def create_running_summary(
        self,
        previous_summary: str,
        new_content: str,
        max_tokens: int = 500,
    ) -> str:
        """Update a rolling summary with new events."""
        response = await self._llm.generate(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You maintain a running summary of a novel in progress. "
                        "Integrate the new content into the existing summary, "
                        "keeping it concise while preserving all important details. "
                        "Remove details that are no longer relevant."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Current summary:\n{previous_summary}\n\n"
                        f"New content to integrate:\n{new_content}"
                    ),
                },
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.content
