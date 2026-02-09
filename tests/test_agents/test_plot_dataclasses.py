"""Tests for Plot agent data classes (ScenePlan, ChapterOutline)."""

import pytest

from storyforge.agents.plot import ScenePlan, ChapterOutline


class TestScenePlan:
    def test_to_dict(self):
        plan = ScenePlan(
            location="forest",
            characters_present=["Alice", "Bob"],
            scene_goal="escape",
            conflict="pursuit",
            expected_outcome="they escape",
            beats=["chase", "hide", "escape"],
            pov_character="Alice",
        )
        d = plan.to_dict()
        assert d["location"] == "forest"
        assert d["characters_present"] == ["Alice", "Bob"]
        assert d["pov_character"] == "Alice"
        assert len(d["beats"]) == 3

    def test_from_dict(self):
        data = {
            "location": "castle",
            "characters_present": ["Hero"],
            "scene_goal": "confront villain",
            "conflict": "battle",
            "expected_outcome": "victory",
            "beats": ["entrance", "fight"],
            "pov_character": "Hero",
        }
        plan = ScenePlan.from_dict(data)
        assert plan.location == "castle"
        assert plan.pov_character == "Hero"

    def test_from_dict_extra_keys_ignored(self):
        data = {
            "location": "cave",
            "characters_present": [],
            "scene_goal": "explore",
            "conflict": "none",
            "expected_outcome": "discovery",
            "extra_field": "ignored",
        }
        plan = ScenePlan.from_dict(data)
        assert plan.location == "cave"

    def test_from_dict_missing_optional_fields(self):
        data = {
            "location": "town",
            "characters_present": ["A"],
            "scene_goal": "gather info",
            "conflict": "suspicion",
            "expected_outcome": "info gathered",
        }
        plan = ScenePlan.from_dict(data)
        assert plan.beats == []
        assert plan.pov_character == ""

    def test_roundtrip(self):
        original = ScenePlan(
            location="ship",
            characters_present=["Captain"],
            scene_goal="sail",
            conflict="storm",
            expected_outcome="survive",
            beats=["set sail", "storm hits"],
            pov_character="Captain",
        )
        restored = ScenePlan.from_dict(original.to_dict())
        assert restored.location == original.location
        assert restored.characters_present == original.characters_present


class TestChapterOutline:
    def test_to_dict(self):
        scene = ScenePlan(
            location="library",
            characters_present=["Scholar"],
            scene_goal="research",
            conflict="missing book",
            expected_outcome="find clue",
        )
        outline = ChapterOutline(
            number=1,
            title="The Discovery",
            summary="Scholar finds a clue",
            pov_character="Scholar",
            scenes=[scene],
            chapter_goal="Introduce mystery",
            emotional_arc="curious -> excited",
        )
        d = outline.to_dict()
        assert d["number"] == 1
        assert d["title"] == "The Discovery"
        assert len(d["scenes"]) == 1

    def test_from_dict(self):
        data = {
            "number": 3,
            "title": "The Battle",
            "summary": "Heroes fight",
            "pov_character": "Hero",
            "chapter_goal": "Climax",
            "emotional_arc": "determined -> triumphant",
            "scenes": [
                {
                    "location": "battlefield",
                    "characters_present": ["Hero", "Villain"],
                    "scene_goal": "final battle",
                    "conflict": "combat",
                    "expected_outcome": "hero wins",
                }
            ],
        }
        outline = ChapterOutline.from_dict(data)
        assert outline.number == 3
        assert outline.title == "The Battle"
        assert len(outline.scenes) == 1
        assert outline.scenes[0].location == "battlefield"

    def test_from_dict_defaults(self):
        data = {}
        outline = ChapterOutline.from_dict(data)
        assert outline.number == 0
        assert outline.title == ""
        assert outline.scenes == []
        assert outline.emotional_arc == ""

    def test_from_dict_empty_scenes(self):
        data = {
            "number": 1,
            "title": "Chapter 1",
            "summary": "intro",
            "pov_character": "MC",
            "chapter_goal": "setup",
            "scenes": [],
        }
        outline = ChapterOutline.from_dict(data)
        assert outline.scenes == []
