"""Tests for the current 3-layer generation engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from batch_concat.core.models import GenerationRequest, VideoItem
from batch_concat.core.permutation_engine import PermutationEngine


def _items(count: int) -> tuple[VideoItem, ...]:
    return tuple(
        VideoItem(item_id=str(index), path=Path(f"C:/video/{index}.mp4"))
        for index in range(1, count + 1)
    )


def test_formula_n20_k4_total_is_2965() -> None:
    engine = PermutationEngine()

    summary = engine.summarize(item_count=20, clips_per_output=4)

    assert summary.group_count == 5
    assert summary.layer1_count == 5
    assert summary.layer2_count == 80
    assert summary.layer3_count == 2880
    assert summary.total_count == 2965


def test_formula_n8_k4_has_only_layer1() -> None:
    engine = PermutationEngine()

    summary = engine.summarize(item_count=8, clips_per_output=4)

    assert summary.group_count == 2
    assert summary.layer1_count == 2
    assert summary.layer2_count == 0
    assert summary.layer3_count == 0
    assert summary.total_count == 2


def test_formula_n10_k4_has_leftover_2() -> None:
    engine = PermutationEngine()

    summary = engine.summarize(item_count=10, clips_per_output=4)

    assert summary.group_count == 2
    assert summary.usable_count == 8
    assert summary.leftover_count == 2


def test_generation_order_is_layer1_then_layer2_then_layer3() -> None:
    engine = PermutationEngine()

    result = engine.generate(
        GenerationRequest(
            items=_items(12),
            clips_per_output=4,
            count=12,
        )
    )

    assert tuple(task.clip_ids for task in result.tasks[:3]) == (
        ("1", "2", "3", "4"),
        ("5", "6", "7", "8"),
        ("9", "10", "11", "12"),
    )
    assert result.tasks[3].layer == 3
    assert result.tasks[3].clip_ids == ("1", "2", "5", "9")
    assert result.tasks[4].clip_ids == ("1", "2", "5", "10")
    assert result.tasks[5].clip_ids == ("1", "2", "5", "11")
    assert result.tasks[6].clip_ids == ("1", "2", "5", "12")
    assert result.tasks[7].clip_ids == ("1", "2", "6", "9")


def test_layer3_ordering_is_deterministic() -> None:
    engine = PermutationEngine()

    first = engine.generate(
        GenerationRequest(
            items=_items(12),
            clips_per_output=4,
            count=20,
        )
    )
    second = engine.generate(
        GenerationRequest(
            items=_items(12),
            clips_per_output=4,
            count=20,
        )
    )

    assert tuple(task.clip_ids for task in first.tasks) == tuple(task.clip_ids for task in second.tasks)


def test_requested_count_above_total_is_clamped() -> None:
    engine = PermutationEngine()

    result = engine.generate(
        GenerationRequest(
            items=_items(8),
            clips_per_output=4,
            count=99,
        )
    )

    assert result.effective_count == 2
    assert result.was_clamped is True
    assert len(result.tasks) == 2


def test_generation_rejects_k_below_2() -> None:
    engine = PermutationEngine()

    with pytest.raises(ValueError, match="clips_per_output must be at least 2."):
        engine.generate(
            GenerationRequest(
                items=_items(2),
                clips_per_output=1,
                count=1,
            )
        )


def test_generation_rejects_when_n_below_k() -> None:
    engine = PermutationEngine()

    with pytest.raises(ValueError, match="At least K clips are required to generate tasks."):
        engine.generate(
            GenerationRequest(
                items=_items(3),
                clips_per_output=4,
                count=1,
            )
        )
