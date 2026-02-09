"""PlotAgent — drives narrative structure, pacing, and scene planning."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from storyforge.agents.base import BaseAgent, strip_json_fences
from storyforge.agents.registry import AgentRegistry
from storyforge.events.types import Event, EventType

logger = logging.getLogger(__name__)


@dataclass
class ScenePlan:
    """Detailed plan for a single scene."""

    location: str
    characters_present: list[str]
    scene_goal: str
    conflict: str
    expected_outcome: str
    beats: list[str] = field(default_factory=list)
    pov_character: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "characters_present": self.characters_present,
            "scene_goal": self.scene_goal,
            "conflict": self.conflict,
            "expected_outcome": self.expected_outcome,
            "beats": self.beats,
            "pov_character": self.pov_character,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenePlan":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ChapterOutline:
    """Complete outline for a chapter."""

    number: int
    title: str
    summary: str
    pov_character: str
    scenes: list[ScenePlan]
    chapter_goal: str
    emotional_arc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "summary": self.summary,
            "pov_character": self.pov_character,
            "scenes": [s.to_dict() for s in self.scenes],
            "chapter_goal": self.chapter_goal,
            "emotional_arc": self.emotional_arc,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChapterOutline":
        scenes = [ScenePlan.from_dict(s) for s in data.get("scenes", [])]
        return cls(
            number=data.get("number", 0),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            pov_character=data.get("pov_character", ""),
            scenes=scenes,
            chapter_goal=data.get("chapter_goal", ""),
            emotional_arc=data.get("emotional_arc", ""),
        )


@dataclass
class PlotOutline:
    """High-level story structure."""

    premise: str
    themes: list[str] = field(default_factory=list)
    target_chapter_count: int = 12
    chapters: list[ChapterOutline] = field(default_factory=list)


@AgentRegistry.register("plot")
class PlotAgent(BaseAgent):
    """Drives narrative structure, pacing, conflict arcs, and scene planning."""

    async def handle_event(self, event: Event) -> Optional[Event]:
        handlers = {
            EventType.CHAPTER_PLAN_REQUEST: self._handle_chapter_plan,
            EventType.PACING_CHECK_REQUEST: self._handle_pacing_check,
            EventType.QUALITY_CHECK_REQUEST: self._handle_quality_check,
        }
        handler = handlers.get(event.event_type)
        if handler:
            return await handler(event)
        return None

    async def _handle_chapter_plan(self, event: Event) -> Event:
        chapter_number = event.payload.get("chapter_number", 1)
        available_characters = event.payload.get("available_characters", [])
        outline = await self.plan_chapter(chapter_number, available_characters)
        return event.create_response(
            EventType.CHAPTER_PLAN_READY,
            {"outline": outline.to_dict()},
            self.config.name,
        )

    async def _handle_pacing_check(self, event: Event) -> Event:
        chapter_text = event.payload.get("chapter_text", "")
        feedback = await self.evaluate_pacing(chapter_text)
        return event.create_response(
            EventType.PACING_FEEDBACK,
            {"feedback": feedback},
            self.config.name,
        )

    async def _handle_quality_check(self, event: Event) -> Event:
        chapter_text = event.payload.get("chapter_text", "")
        outline = event.payload.get("outline", {})
        issues = await self.check_quality(chapter_text, outline)
        return event.create_response(
            EventType.QUALITY_CHECK_RESULT,
            {"issues": issues},
            self.config.name,
        )

    async def plan_chapter(
        self, chapter_number: int, available_characters: list[str] | None = None
    ) -> ChapterOutline:
        """Plan a full chapter with scene breakdowns."""
        # Get plot outline and previous chapter summaries
        plot_data = await self.memory.retrieve("plot_outline") or {}
        summaries = await self.memory.retrieve("chapter_summaries") or []

        summary_text = ""
        if summaries:
            summary_text = "\n".join(
                f"Chapter {i+1}: {s}" for i, s in enumerate(summaries)
            )

        prev_section = f"Previous chapters:\n{summary_text}" if summary_text else "This is the first chapter."
        outline_text = json.dumps(plot_data, indent=2, ensure_ascii=False) if isinstance(plot_data, dict) else str(plot_data)

        # Tell the LLM about available character names so it uses exact names
        char_note = ""
        if available_characters:
            char_list = ", ".join(f'"{c}"' for c in available_characters)
            char_note = (
                f"\nIMPORTANT: The available characters are: {char_list}. "
                f"You MUST use these EXACT names (no translations, no parenthetical annotations) "
                f"in characters_present and pov_character fields.\n"
            )

        prompt = f"""You are a master story planner. Plan Chapter {chapter_number}.

Story outline:
{outline_text}

{prev_section}
{char_note}
Create a detailed chapter plan. Respond as JSON:
{{
    "number": {chapter_number},
    "title": "chapter title",
    "summary": "brief summary of what happens",
    "pov_character": "name of the POV character",
    "chapter_goal": "what this chapter accomplishes in the larger story",
    "emotional_arc": "emotional journey of this chapter",
    "scenes": [
        {{
            "location": "where the scene takes place",
            "characters_present": ["character names"],
            "scene_goal": "what this scene accomplishes",
            "conflict": "the tension or conflict in this scene",
            "expected_outcome": "how the scene resolves",
            "beats": ["ordered narrative beats"],
            "pov_character": "scene POV"
        }}
    ]
}}

Include 2-4 scenes per chapter. Each scene should advance the plot and develop characters."""
        response = await self.generate(prompt, temperature=0.7)
        try:
            data = json.loads(strip_json_fences(response))
            return ChapterOutline.from_dict(data)
        except json.JSONDecodeError:
            # Fallback: minimal outline
            logger.warning("Failed to parse chapter plan JSON, using fallback")
            return ChapterOutline(
                number=chapter_number,
                title=f"Chapter {chapter_number}",
                summary="",
                pov_character="",
                scenes=[
                    ScenePlan(
                        location="",
                        characters_present=[],
                        scene_goal="Advance the story",
                        conflict="",
                        expected_outcome="",
                        beats=["Opening", "Development", "Climax", "Resolution"],
                    )
                ],
                chapter_goal="",
            )

    async def evaluate_pacing(self, chapter_text: str) -> dict[str, Any]:
        """Evaluate if a chapter maintains proper pacing."""
        prompt = f"""Evaluate the pacing of this chapter draft.

Chapter:
{chapter_text[:3000]}

Analyze:
1. Is the opening engaging?
2. Does tension build appropriately?
3. Are there any sections that drag or rush?
4. Is the balance of dialogue, action, and description appropriate?
5. Does the chapter end with momentum?

Respond as JSON:
{{
    "score": 1-10,
    "issues": ["list of specific pacing problems"],
    "strengths": ["what works well"],
    "suggestions": ["actionable improvements"]
}}"""
        response = await self.generate(prompt, temperature=0.4)
        try:
            return json.loads(strip_json_fences(response))
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse pacing evaluation JSON: %s. Response: %.200s",
                e, response,
            )
            return {"score": 5, "issues": [], "strengths": [], "suggestions": []}

    async def check_quality(
        self, chapter_text: str, outline: dict[str, Any]
    ) -> list[str]:
        """Check chapter quality against the outline."""
        prompt = f"""Review this chapter draft against its outline.

Outline:
{json.dumps(outline, indent=2, ensure_ascii=False) if isinstance(outline, dict) else outline}

Chapter Draft:
{chapter_text[:3000]}

List any issues:
- Does the chapter achieve its stated goal?
- Are all planned scenes present?
- Is the pacing appropriate?
- Are character arcs progressing correctly?

Respond as a JSON array of issue strings. If no issues, respond with []."""
        response = await self.generate(prompt, temperature=0.3)
        try:
            result = json.loads(strip_json_fences(response))
            return result if isinstance(result, list) else []
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse quality check JSON: %s. Response: %.200s",
                e, response,
            )
            return []
