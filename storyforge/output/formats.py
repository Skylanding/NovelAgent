"""Export formatters for different output formats."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ExportFormatter(ABC):
    """Abstract base for export format handlers."""

    @abstractmethod
    async def export(
        self,
        chapters_dir: Path,
        metadata: dict,
        output_path: Path,
    ) -> Path:
        ...


class MarkdownFormatter(ExportFormatter):
    """Combines chapters into a single Markdown document."""

    async def export(
        self, chapters_dir: Path, metadata: dict, output_path: Path
    ) -> Path:
        title = metadata.get("title", "Novel")
        author = metadata.get("author", "")
        parts = [f"# {title}\n"]
        if author:
            parts.append(f"*by {author}*\n")
        parts.append("\n---\n\n")

        chapter_files = sorted(chapters_dir.glob("chapter_*.md"))
        for chapter_file in chapter_files:
            if "_meta" not in chapter_file.name:
                parts.append(chapter_file.read_text(encoding="utf-8"))
                parts.append("\n\n")

        output_path.write_text("".join(parts), encoding="utf-8")
        return output_path


class HtmlFormatter(ExportFormatter):
    """Exports as a styled HTML document."""

    async def export(
        self, chapters_dir: Path, metadata: dict, output_path: Path
    ) -> Path:
        title = metadata.get("title", "Novel")
        author = metadata.get("author", "")

        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            f"<title>{title}</title>",
            "<meta charset='utf-8'>",
            "<style>",
            "body { max-width: 700px; margin: 2em auto; font-family: Georgia, serif; line-height: 1.8; color: #333; padding: 0 1em; }",
            "h1 { text-align: center; margin-bottom: 0.2em; }",
            "h2 { margin-top: 3em; border-bottom: 1px solid #ccc; padding-bottom: 0.3em; }",
            ".author { text-align: center; color: #666; margin-bottom: 2em; }",
            "p { text-indent: 1.5em; margin: 0.5em 0; }",
            "hr { margin: 3em 0; border: none; border-top: 1px solid #ccc; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{title}</h1>",
        ]
        if author:
            html_parts.append(f'<p class="author">by {author}</p>')
        html_parts.append("<hr>")

        chapter_files = sorted(chapters_dir.glob("chapter_*.md"))
        for chapter_file in chapter_files:
            if "_meta" not in chapter_file.name:
                content = chapter_file.read_text(encoding="utf-8")
                html_parts.append(self._md_to_html(content))
                html_parts.append("<hr>")

        html_parts.extend(["</body>", "</html>"])
        output_path.write_text("\n".join(html_parts), encoding="utf-8")
        return output_path

    @staticmethod
    def _md_to_html(md_text: str) -> str:
        """Simple markdown-to-HTML conversion."""
        lines = md_text.split("\n")
        html_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                html_lines.append(f"<h2>{stripped[3:]}</h2>")
            elif stripped.startswith("# "):
                html_lines.append(f"<h1>{stripped[2:]}</h1>")
            elif stripped:
                html_lines.append(f"<p>{stripped}</p>")
        return "\n".join(html_lines)
