"""Output manager for visual pipeline artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class VisualOutputManager:
    """Manages output storage for visual pipeline."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._visuals_dir = output_dir / "visuals"
        self._intermediates_dir = output_dir / "visual_intermediates"

    @property
    def visuals_dir(self) -> Path:
        return self._visuals_dir

    async def initialize(self) -> None:
        for d in [self._visuals_dir, self._intermediates_dir]:
            d.mkdir(parents=True, exist_ok=True)

    async def save_intermediate(self, stage: str, content: Any) -> None:
        self._intermediates_dir.mkdir(parents=True, exist_ok=True)
        path = self._intermediates_dir / f"{stage}.json"
        path.write_text(
            json.dumps(content, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    async def save_manifest(self, manifest: dict[str, Any]) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        manifest_path = self._output_dir / f"visual_manifest_{timestamp}.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return manifest_path
