"""Pipeline stage definitions and status tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Result of a pipeline stage execution."""

    stage_name: str
    status: StageStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Any = None
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class PipelineTracker:
    """Tracks the progress of a chapter generation pipeline."""

    def __init__(self) -> None:
        self._stages: list[StageResult] = []

    def start_stage(self, name: str) -> StageResult:
        result = StageResult(
            stage_name=name,
            status=StageStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self._stages.append(result)
        return result

    def complete_stage(
        self, result: StageResult, output: Any = None
    ) -> None:
        result.status = StageStatus.COMPLETED
        result.completed_at = datetime.now(timezone.utc)
        result.output = output

    def fail_stage(self, result: StageResult, error: str) -> None:
        result.status = StageStatus.FAILED
        result.completed_at = datetime.now(timezone.utc)
        result.error = error

    @property
    def stages(self) -> list[StageResult]:
        return list(self._stages)

    def summary(self) -> dict[str, Any]:
        return {
            "total_stages": len(self._stages),
            "completed": sum(
                1 for s in self._stages if s.status == StageStatus.COMPLETED
            ),
            "failed": sum(
                1 for s in self._stages if s.status == StageStatus.FAILED
            ),
            "stages": [
                {
                    "name": s.stage_name,
                    "status": s.status.value,
                    "duration": s.duration_seconds,
                }
                for s in self._stages
            ],
        }
