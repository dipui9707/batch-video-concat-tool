"""Tests for user input validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from batch_concat.core.models import ExportAspectRatio, JobInput, VideoItem
from batch_concat.core.validation import ValidationError, validate_job_inputs


def test_validate_job_inputs_returns_generation_summary(tmp_path: Path) -> None:
    videos = []
    for name in ("a.mp4", "b.mp4", "c.mp4", "d.mp4"):
        path = tmp_path / name
        path.write_bytes(b"x")
        videos.append(path)

    summary = validate_job_inputs(
        JobInput(
            videos=tuple(VideoItem(item_id=str(index), path=path) for index, path in enumerate(videos, start=1)),
            clips_per_output=4,
            count=1,
            aspect_ratio=ExportAspectRatio.VERTICAL_9_16,
            output_dir=tmp_path,
        )
    )

    assert summary.group_count == 1
    assert summary.total_count == 1
    assert summary.layer3_count == 0


def test_validate_job_inputs_rejects_k_below_2(tmp_path: Path) -> None:
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x")

    with pytest.raises(ValidationError, match="K must be at least 2."):
        validate_job_inputs(
            JobInput(
                videos=(VideoItem(item_id="1", path=video),),
                clips_per_output=1,
                count=1,
                aspect_ratio=ExportAspectRatio.VERTICAL_9_16,
                output_dir=tmp_path,
            )
        )


def test_validate_job_inputs_rejects_n_below_k(tmp_path: Path) -> None:
    first = tmp_path / "a.mp4"
    second = tmp_path / "b.mp4"
    first.write_bytes(b"x")
    second.write_bytes(b"y")

    with pytest.raises(ValidationError, match="N must be greater than or equal to K."):
        validate_job_inputs(
            JobInput(
                videos=(
                    VideoItem(item_id="1", path=first),
                    VideoItem(item_id="2", path=second),
                ),
                clips_per_output=4,
                count=1,
                aspect_ratio=ExportAspectRatio.VERTICAL_9_16,
                output_dir=tmp_path,
            )
        )


def test_validate_job_inputs_rejects_count_below_1(tmp_path: Path) -> None:
    first = tmp_path / "a.mp4"
    second = tmp_path / "b.mp4"
    first.write_bytes(b"x")
    second.write_bytes(b"y")

    with pytest.raises(ValidationError, match="Generation count must be at least 1."):
        validate_job_inputs(
            JobInput(
                videos=(
                    VideoItem(item_id="1", path=first),
                    VideoItem(item_id="2", path=second),
                ),
                clips_per_output=2,
                count=0,
                aspect_ratio=ExportAspectRatio.VERTICAL_9_16,
                output_dir=tmp_path,
            )
        )
