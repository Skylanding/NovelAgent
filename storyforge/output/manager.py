"""Output manager — saving, versioning, and exporting chapters."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from storyforge.agents.plot import ChapterOutline


class OutputManager:
    """Manages chapter output, versioning, and export."""

    def __init__(
        self,
        output_dir: Path,
        versioning: bool = True,
        save_intermediates: bool = True,
    ) -> None:
        self._output_dir = output_dir
        self._versioning = versioning
        self._save_intermediates = save_intermediates
        self._chapters_dir = output_dir / "chapters"
        self._versions_dir = output_dir / "versions"
        self._intermediates_dir = output_dir / "intermediates"
        self._exports_dir = output_dir / "exports"

    async def initialize(self) -> None:
        """Create output directory structure."""
        for d in [
            self._chapters_dir,
            self._versions_dir,
            self._intermediates_dir,
            self._exports_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    async def save_chapter(
        self,
        chapter_number: int,
        text: str,
        outline: Optional[ChapterOutline] = None,
        metadata: Optional[dict] = None,
    ) -> Path:
        """Save a chapter with metadata and optional versioning."""
        # Ensure directory exists
        self._chapters_dir.mkdir(parents=True, exist_ok=True)

        # Format chapter markdown
        chapter_content = self._format_chapter_markdown(
            chapter_number, text, outline
        )

        # Save current version
        chapter_path = self._chapters_dir / f"chapter_{chapter_number:03d}.md"
        chapter_path.write_text(chapter_content, encoding="utf-8")

        # Version snapshot
        if self._versioning:
            version_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            version_dir = (
                self._versions_dir / f"chapter_{chapter_number:03d}"
            )
            version_dir.mkdir(parents=True, exist_ok=True)
            version_path = version_dir / f"v_{version_id}.md"
            version_path.write_text(chapter_content, encoding="utf-8")

        # Save metadata
        meta = {
            "chapter_number": chapter_number,
            "title": outline.title if outline else f"Chapter {chapter_number}",
            "word_count": len(text.split()),
            "char_count": len(text),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if outline:
            meta["pov_character"] = outline.pov_character
            meta["scene_count"] = len(outline.scenes)
            meta["chapter_goal"] = outline.chapter_goal
        if metadata:
            meta.update(metadata)

        meta_path = (
            self._chapters_dir / f"chapter_{chapter_number:03d}_meta.json"
        )
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        return chapter_path

    async def save_intermediate(
        self, chapter_number: int, stage: str, content: Any
    ) -> None:
        """Save intermediate pipeline artifacts."""
        if not self._save_intermediates:
            return

        inter_dir = (
            self._intermediates_dir / f"chapter_{chapter_number:03d}"
        )
        inter_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(content, str):
            path = inter_dir / f"{stage}.md"
            path.write_text(content, encoding="utf-8")
        else:
            path = inter_dir / f"{stage}.json"
            path.write_text(
                json.dumps(content, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    async def export_markdown(self, title: str = "Novel") -> Path:
        """Export all chapters as a single Markdown file."""
        self._exports_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._exports_dir / f"{self._slugify(title)}.md"

        parts = [f"# {title}\n\n"]

        # Collect and sort chapter files
        chapter_files = sorted(self._chapters_dir.glob("chapter_*.md"))
        for chapter_file in chapter_files:
            if "_meta" not in chapter_file.name:
                parts.append(chapter_file.read_text(encoding="utf-8"))
                parts.append("\n\n---\n\n")

        output_path.write_text("".join(parts), encoding="utf-8")
        return output_path

    def get_chapter_count(self) -> int:
        """Count generated chapters."""
        if not self._chapters_dir.exists():
            return 0
        return len(
            [
                f
                for f in self._chapters_dir.glob("chapter_*.md")
                if "_meta" not in f.name
            ]
        )

    def get_total_word_count(self) -> int:
        """Get total word count across all chapters."""
        total = 0
        for meta_file in self._chapters_dir.glob("chapter_*_meta.json"):
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                total += meta.get("word_count", 0)
            except (json.JSONDecodeError, OSError):
                pass
        return total

    def _format_chapter_markdown(
        self,
        chapter_number: int,
        text: str,
        outline: Optional[ChapterOutline] = None,
    ) -> str:
        title = outline.title if outline else f"Chapter {chapter_number}"
        return f"## Chapter {chapter_number}: {title}\n\n{text}\n"

    @staticmethod
    def _slugify(text: str) -> str:
        return (
            text.lower()
            .replace(" ", "_")
            .replace(":", "")
            .replace("'", "")
            .replace('"', "")
        )
