"""Core data models used by the application."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ExportAspectRatio(StrEnum):
    """Supported export aspect ratio presets."""

    VERTICAL_9_16 = "vertical_9_16"
    VERTICAL_3_4 = "vertical_3_4"
    HORIZONTAL_16_9 = "horizontal_16_9"
    HORIZONTAL_4_3 = "horizontal_4_3"
    SQUARE_1_1 = "square_1_1"


@dataclass(frozen=True, slots=True)
class VideoItem:
    """A single source video selected by the user."""

    item_id: str
    path: Path


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Parameters required to generate ordered video-combination tasks."""

    items: tuple[VideoItem, ...]
    clips_per_output: int
    count: int


@dataclass(frozen=True, slots=True)
class GenerationSummary:
    """Summary counters for the current 3-layer generation logic."""

    item_count: int
    clips_per_output: int
    group_count: int
    usable_count: int
    leftover_count: int
    layer1_count: int
    layer2_count: int
    layer3_count: int
    total_count: int


@dataclass(frozen=True, slots=True)
class GenerationTask:
    """One generated export task with resolved clip metadata."""

    task_id: str
    layer: int
    pattern_type: str
    shift: int | None
    source_group_ids: tuple[int, ...]
    clip_ids: tuple[str, ...]
    clip_paths: tuple[Path, ...]
    timeline_name: str
    output_name: str


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Generated tasks plus summary information."""

    tasks: tuple[GenerationTask, ...]
    summary: GenerationSummary
    requested_count: int
    effective_count: int
    was_clamped: bool


@dataclass(frozen=True, slots=True)
class JobInput:
    """User-provided job configuration before Resolve execution."""

    videos: tuple[VideoItem, ...]
    clips_per_output: int
    count: int
    aspect_ratio: ExportAspectRatio
    output_dir: Path
