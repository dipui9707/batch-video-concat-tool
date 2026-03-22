"""Validation helpers for user-provided job input."""

from __future__ import annotations

import os
from pathlib import Path

from batch_concat.core.models import GenerationRequest, GenerationSummary, JobInput
from batch_concat.core.permutation_engine import PermutationEngine


class ValidationError(Exception):
    """Raised when user-provided job input fails validation."""


def validate_job_inputs(job_input: JobInput) -> GenerationSummary:
    """Validate user inputs before Resolve script export starts."""

    if job_input.clips_per_output < 2:
        raise ValidationError("K must be at least 2.")
    if job_input.count < 1:
        raise ValidationError("Generation count must be at least 1.")
    if len({video.item_id for video in job_input.videos}) != len(job_input.videos):
        raise ValidationError("Video item IDs must be unique.")

    _validate_video_paths(job_input)
    _validate_output_dir(job_input.output_dir)

    engine = PermutationEngine()
    summary = engine.summarize(len(job_input.videos), job_input.clips_per_output)
    if len(job_input.videos) < job_input.clips_per_output:
        raise ValidationError("N must be greater than or equal to K.")

    try:
        engine.generate(
            GenerationRequest(
                items=job_input.videos,
                clips_per_output=job_input.clips_per_output,
                count=job_input.count,
            )
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    return summary


def _validate_video_paths(job_input: JobInput) -> None:
    """Ensure each selected source file exists and is a file."""

    seen_paths: set[Path] = set()
    for video in job_input.videos:
        if video.path in seen_paths:
            raise ValidationError(f"Duplicate video path selected: {video.path}")
        seen_paths.add(video.path)
        if not video.path.exists():
            raise ValidationError(f"Video file does not exist: {video.path}")
        if not video.path.is_file():
            raise ValidationError(f"Video path is not a file: {video.path}")


def _validate_output_dir(output_dir: Path) -> None:
    """Ensure the output directory exists, is a directory, and is writable."""

    if not output_dir.exists():
        raise ValidationError(f"Output directory does not exist: {output_dir}")
    if not output_dir.is_dir():
        raise ValidationError(f"Output path is not a directory: {output_dir}")
    if not os.access(output_dir, os.W_OK):
        raise ValidationError(f"Output directory is not writable: {output_dir}")
