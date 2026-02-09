"""Chapter pipeline — orchestrates the generation of a single chapter."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from storyforge.agents.character import CharacterAgent
from storyforge.agents.character.skills import SkillMatcher
from storyforge.agents.plot import ChapterOutline, PlotAgent, ScenePlan
from storyforge.agents.world import WorldAgent
from storyforge.agents.writing import WritingAgent
from storyforge.events.bus import EventBus
from storyforge.events.types import Event, EventType
from storyforge.memory.summary import MemorySummarizer
from storyforge.output.manager import OutputManager

logger = logging.getLogger(__name__)


class ChapterPipeline:
    """Orchestrates the generation of a single chapter through all stages."""

    def __init__(
        self,
        event_bus: EventBus,
        world_agent: WorldAgent,
        character_agents: dict[str, CharacterAgent],
        plot_agent: PlotAgent,
        writing_agent: WritingAgent,
        output_manager: OutputManager,
        summarizer: Optional[MemorySummarizer] = None,
        max_revision_rounds: int = 3,
        parallel_characters: bool = True,
    ) -> None:
        self._bus = event_bus
        self._world = world_agent
        self._characters = character_agents
        self._plot = plot_agent
        self._writer = writing_agent
        self._output = output_manager
        self._summarizer = summarizer
        self._max_revisions = max_revision_rounds
        self._parallel = parallel_characters

    def _resolve_character_name(self, name_from_plot: str) -> Optional[str]:
        """Fuzzy-match a character name from the plot agent to a registered name.

        Handles cases like '林焱 (Lin Yan)' matching registered name '林焱'.
        """
        # Exact match first
        if name_from_plot in self._characters:
            return name_from_plot
        # Check if any registered name is contained in the plot name
        for registered_name in self._characters:
            if registered_name in name_from_plot:
                return registered_name
        # Check if plot name is contained in any registered name
        for registered_name in self._characters:
            if name_from_plot in registered_name:
                return registered_name
        # Strip parenthetical annotations and try again
        stripped = name_from_plot.split("(")[0].strip()
        if stripped and stripped in self._characters:
            return stripped
        return None

    def _resolve_scene_characters(self, scene_plan: ScenePlan) -> None:
        """Resolve all character names in a scene plan to registered names."""
        resolved = []
        for name in scene_plan.characters_present:
            resolved_name = self._resolve_character_name(name)
            if resolved_name:
                resolved.append(resolved_name)
            else:
                logger.warning(
                    "Character '%s' could not be resolved to any registered agent",
                    name,
                )
        scene_plan.characters_present = resolved
        if scene_plan.pov_character:
            resolved_pov = self._resolve_character_name(scene_plan.pov_character)
            if resolved_pov:
                scene_plan.pov_character = resolved_pov

    async def generate_chapter(self, chapter_number: int) -> str:
        """Full chapter generation pipeline. Returns the final chapter text."""
        logger.info("=== Generating Chapter %d ===", chapter_number)

        # Stage 1: Plan
        logger.info("[Stage 1] Planning chapter %d...", chapter_number)
        chapter_outline = await self._stage_plan(chapter_number)
        # Resolve character names from plot agent to registered agent names
        for scene in chapter_outline.scenes:
            self._resolve_scene_characters(scene)
        await self._save_intermediate(
            chapter_number, "outline", chapter_outline.to_dict()
        )

        # Stage 2-5: Generate all scenes in parallel
        logger.info(
            "[Stage 2] Generating %d scenes in parallel...",
            len(chapter_outline.scenes),
        )
        scene_tasks = [
            self._generate_scene(
                chapter_number, scene_idx, scene_plan, chapter_outline
            )
            for scene_idx, scene_plan in enumerate(chapter_outline.scenes)
        ]
        scenes = await asyncio.gather(*scene_tasks)
        scenes = list(scenes)
        for scene_idx, scene_text in enumerate(scenes):
            await self._save_intermediate(
                chapter_number, f"scene_{scene_idx}_draft", scene_text
            )

        # Stage 6: Assemble chapter (direct concatenation — skip LLM rewrite)
        logger.info("[Stage 6] Assembling chapter...")
        chapter_header = f"## Chapter {chapter_number}: {chapter_outline.title}\n\n"
        chapter_draft = chapter_header + "\n\n".join(scenes)

        # Stage 7: Review and revise
        logger.info("[Stage 7] Review and revision loop...")
        final_chapter = await self._stage_review_and_revise(
            chapter_number, chapter_draft, chapter_outline
        )

        # Stage 8: Finalize
        logger.info("[Stage 8] Finalizing chapter %d...", chapter_number)
        await self._stage_finalize(
            chapter_number, final_chapter, chapter_outline
        )

        logger.info("=== Chapter %d complete ===", chapter_number)
        return final_chapter

    async def _stage_plan(self, chapter_number: int) -> ChapterOutline:
        """Stage 1: PlotAgent plans the chapter."""
        event = Event(
            event_type=EventType.CHAPTER_PLAN_REQUEST,
            payload={
                "chapter_number": chapter_number,
                "available_characters": list(self._characters.keys()),
            },
            source_agent="pipeline",
            target_agent=self._plot.config.name,
            chapter_number=chapter_number,
        )
        response = await self._bus.request(event, timeout=120.0)
        return ChapterOutline.from_dict(response.payload["outline"])

    async def _generate_scene(
        self,
        chapter_number: int,
        scene_idx: int,
        scene_plan: ScenePlan,
        chapter_outline: ChapterOutline,
    ) -> str:
        """Generate a single scene through all substages."""
        # Stage 2: WorldAgent validates setting + CharacterAgents react (parallel)
        world_task = self._stage_validate_world(
            chapter_number, scene_idx, scene_plan
        )
        char_task = self._stage_character_reactions(
            chapter_number, scene_idx, scene_plan, {}
        )
        enriched_setting, character_reactions = await asyncio.gather(
            world_task, char_task
        )

        # Stage 3: WritingAgent composes the scene (dialogue is generated inline)
        scene_text = await self._stage_compose_scene(
            chapter_number,
            scene_idx,
            scene_plan,
            enriched_setting,
            character_reactions,
            [],  # No separate dialogue — WritingAgent generates it inline
        )
        return scene_text

    async def _stage_validate_world(
        self,
        chapter_number: int,
        scene_idx: int,
        scene_plan: ScenePlan,
    ) -> dict[str, Any]:
        """WorldAgent validates/enriches the setting."""
        event = Event(
            event_type=EventType.SETTING_VALIDATION_REQUEST,
            payload={"scene_plan": scene_plan.to_dict()},
            source_agent="pipeline",
            target_agent=self._world.config.name,
            chapter_number=chapter_number,
            scene_index=scene_idx,
        )
        response = await self._bus.request(event, timeout=90.0)
        return response.payload.get("enriched_setting", {})

    async def _stage_character_reactions(
        self,
        chapter_number: int,
        scene_idx: int,
        scene_plan: ScenePlan,
        setting: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """All characters in the scene react (optionally in parallel)."""
        # Detect scene types for skill activation
        scene_types = SkillMatcher.detect_scene_type(scene_plan.to_dict())
        scene_type_values = [st.value for st in scene_types]

        tasks = []
        for char_name in scene_plan.characters_present:
            if char_name not in self._characters:
                continue
            event = Event(
                event_type=EventType.CHARACTER_REACTION_REQUEST,
                payload={
                    "scene_plan": scene_plan.to_dict(),
                    "setting": setting,
                    "scene_types": scene_type_values,
                },
                source_agent="pipeline",
                target_agent=char_name,
                chapter_number=chapter_number,
                scene_index=scene_idx,
            )
            tasks.append(self._bus.request(event, timeout=60.0))

        if not tasks:
            return []

        if self._parallel:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
            for task in tasks:
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    results.append(e)

        reactions = []
        for result in results:
            if isinstance(result, Event):
                reactions.append(result.payload.get("reaction", {}))
            elif isinstance(result, Exception):
                logger.warning("Character reaction failed: %s", result)
        return reactions

    async def _stage_dialogue(
        self,
        chapter_number: int,
        scene_idx: int,
        scene_plan: ScenePlan,
        reactions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate dialogue exchanges between characters."""
        dialogue_lines: list[dict[str, Any]] = []

        for beat in scene_plan.beats:
            # Only generate dialogue for dialogue-related beats
            beat_lower = beat.lower()
            if not any(
                word in beat_lower
                for word in ["dialogue", "speak", "talk", "convers", "discuss", "argue", "say"]
            ):
                continue

            for char_name in scene_plan.characters_present:
                if char_name not in self._characters:
                    continue
                event = Event(
                    event_type=EventType.DIALOGUE_REQUEST,
                    payload={
                        "beat": beat,
                        "previous_dialogue": dialogue_lines[-6:],
                        "scene_context": scene_plan.to_dict(),
                    },
                    source_agent="pipeline",
                    target_agent=char_name,
                    chapter_number=chapter_number,
                    scene_index=scene_idx,
                )
                try:
                    response = await self._bus.request(event, timeout=30.0)
                    dialogue_lines.append(
                        response.payload.get("dialogue", {})
                    )
                except TimeoutError:
                    logger.warning(
                        "Dialogue timeout for %s on beat: %s",
                        char_name,
                        beat,
                    )
        return dialogue_lines

    async def _stage_compose_scene(
        self,
        chapter_number: int,
        scene_idx: int,
        scene_plan: ScenePlan,
        setting: dict[str, Any],
        reactions: list[dict[str, Any]],
        dialogue: list[dict[str, Any]],
    ) -> str:
        """WritingAgent composes the scene."""
        event = Event(
            event_type=EventType.SCENE_DRAFT_REQUEST,
            payload={
                "scene_plan": scene_plan.to_dict(),
                "setting": setting,
                "character_reactions": reactions,
                "dialogue_lines": dialogue,
            },
            source_agent="pipeline",
            target_agent=self._writer.config.name,
            chapter_number=chapter_number,
            scene_index=scene_idx,
        )
        response = await self._bus.request(event, timeout=180.0)
        return response.payload.get("scene_text", "")

    async def _stage_review_and_revise(
        self,
        chapter_number: int,
        draft: str,
        outline: ChapterOutline,
    ) -> str:
        """Review loop with consistency and quality checks."""
        if self._max_revisions <= 0:
            logger.info("  Review rounds disabled — skipping")
            return draft

        current_draft = draft

        for round_num in range(self._max_revisions):
            logger.info("  Review round %d/%d", round_num + 1, self._max_revisions)

            # Consistency check via WorldAgent
            consistency_event = Event(
                event_type=EventType.CONSISTENCY_CHECK_REQUEST,
                payload={
                    "chapter_text": current_draft,
                    "chapter_number": chapter_number,
                },
                source_agent="pipeline",
                target_agent=self._world.config.name,
            )

            # Quality check via PlotAgent
            quality_event = Event(
                event_type=EventType.QUALITY_CHECK_REQUEST,
                payload={
                    "chapter_text": current_draft,
                    "outline": outline.to_dict(),
                },
                source_agent="pipeline",
                target_agent=self._plot.config.name,
            )

            # Run both checks in parallel
            consistency_resp, quality_resp = await asyncio.gather(
                self._bus.request(consistency_event, timeout=90.0),
                self._bus.request(quality_event, timeout=90.0),
            )

            consistency_issues = consistency_resp.payload.get("issues", [])
            quality_issues = quality_resp.payload.get("issues", [])
            all_issues = consistency_issues + quality_issues

            if not all_issues:
                logger.info("  No issues found — draft approved")
                break

            # Only revise if there are significant issues (>2)
            if len(all_issues) <= 2:
                logger.info(
                    "  Found %d minor issues — accepting draft without revision",
                    len(all_issues),
                )
                break

            logger.info("  Found %d issues, revising...", len(all_issues))
            await self._save_intermediate(
                chapter_number,
                f"review_round_{round_num + 1}",
                {"issues": all_issues},
            )

            # Revise
            revision_event = Event(
                event_type=EventType.REVISION_REQUEST,
                payload={
                    "chapter_text": current_draft,
                    "feedback": all_issues,
                },
                source_agent="pipeline",
                target_agent=self._writer.config.name,
            )
            revision_resp = await self._bus.request(
                revision_event, timeout=180.0
            )
            current_draft = revision_resp.payload.get(
                "revised_text", current_draft
            )

        return current_draft

    async def _stage_finalize(
        self,
        chapter_number: int,
        final_text: str,
        outline: ChapterOutline,
    ) -> None:
        """Save chapter and update all agent memories."""
        # Save the chapter
        await self._output.save_chapter(chapter_number, final_text, outline)

        # Create chapter summary for memory (fast: truncate instead of LLM call)
        summary = final_text[:500] + "..." if len(final_text) > 500 else final_text

        # Update plot agent memory with chapter summary
        summaries = await self._plot.memory.retrieve("chapter_summaries") or []
        if isinstance(summaries, list):
            summaries.append(summary)
            await self._plot.memory.store("chapter_summaries", summaries)

        # Store memories for each character that appeared
        for scene in outline.scenes:
            for char_name in scene.characters_present:
                if char_name in self._characters:
                    char_agent = self._characters[char_name]
                    memory_key = f"ch{chapter_number}_scene_{scene.scene_goal[:30]}"
                    await char_agent.memory.store(
                        memory_key,
                        f"Chapter {chapter_number}: {scene.scene_goal}. "
                        f"Outcome: {scene.expected_outcome}",
                        metadata={"chapter": chapter_number},
                    )

    async def _save_intermediate(
        self, chapter_number: int, stage: str, content: Any
    ) -> None:
        """Save intermediate pipeline artifacts."""
        try:
            await self._output.save_intermediate(
                chapter_number, stage, content
            )
        except Exception as e:
            logger.warning("Failed to save intermediate for %s: %s", stage, e)
