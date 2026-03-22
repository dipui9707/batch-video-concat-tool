"""3-layer generation logic for batch video combination tasks."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from math import comb

from batch_concat.core.models import (
    GenerationRequest,
    GenerationResult,
    GenerationSummary,
    GenerationTask,
    VideoItem,
)


@dataclass(slots=True)
class PermutationEngine:
    """Generate ordered video-combination tasks using the current 3-layer rules."""

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate tasks according to the authoritative generation logic."""

        self._validate_request(request)
        summary = self.calculate_counts(len(request.items), request.clips_per_output)
        tasks = self.generate_all_candidates(request.items, request.clips_per_output)
        clamped_count = min(request.count, summary.total_count)
        return GenerationResult(
            tasks=tasks[:clamped_count],
            summary=summary,
            requested_count=request.count,
            effective_count=clamped_count,
            was_clamped=request.count > summary.total_count,
        )

    def summarize(self, item_count: int, clips_per_output: int) -> GenerationSummary:
        """Backwards-compatible wrapper for generation counts."""

        return self.calculate_counts(item_count, clips_per_output)

    def calculate_counts(self, item_count: int, clips_per_output: int) -> GenerationSummary:
        """Return generation counters for the given input size."""

        if clips_per_output < 2:
            raise ValueError("clips_per_output must be at least 2.")
        if item_count < 0:
            raise ValueError("item_count cannot be negative.")

        group_count = item_count // clips_per_output
        usable_count = group_count * clips_per_output
        leftover_count = item_count - usable_count
        layer1_count = group_count
        layer2_count = 0
        layer3_count = 0

        if group_count >= clips_per_output:
            layer2_count = comb(group_count, clips_per_output) * (clips_per_output**2)

        if clips_per_output >= 3 and group_count >= clips_per_output - 1:
            layer3_count = (
                group_count
                * comb(group_count - 1, clips_per_output - 2)
                * comb(clips_per_output, 2)
                * (clips_per_output ** (clips_per_output - 2))
            )

        return GenerationSummary(
            item_count=item_count,
            clips_per_output=clips_per_output,
            group_count=group_count,
            usable_count=usable_count,
            leftover_count=leftover_count,
            layer1_count=layer1_count,
            layer2_count=layer2_count,
            layer3_count=layer3_count,
            total_count=layer1_count + layer2_count + layer3_count,
        )

    def build_groups(self, items: tuple[VideoItem, ...], k: int) -> tuple[tuple[VideoItem, ...], ...]:
        """Split the first usable clips into stable groups of size ``k``."""

        summary = self.calculate_counts(len(items), k)
        participating = items[: summary.usable_count]
        return tuple(
            participating[index : index + k]
            for index in range(0, len(participating), k)
        )

    def generate_all_candidates(
        self,
        items: tuple[VideoItem, ...],
        k: int,
    ) -> tuple[GenerationTask, ...]:
        """Generate all candidate tasks in required layer order."""

        groups = self.build_groups(items, k)
        tasks: list[GenerationTask] = []
        tasks.extend(self.generate_layer1(groups, k, start_index=len(tasks) + 1))
        tasks.extend(self.generate_layer2(groups, k, start_index=len(tasks) + 1))
        tasks.extend(self.generate_layer3(groups, k, start_index=len(tasks) + 1))
        return tuple(tasks)

    def generate_layer1(
        self,
        groups: tuple[tuple[VideoItem, ...], ...],
        k: int,
        start_index: int = 1,
    ) -> tuple[GenerationTask, ...]:
        """Generate layer 1 direct group tasks."""

        del k
        tasks: list[GenerationTask] = []
        for offset, group in enumerate(groups):
            group_id = offset + 1
            tasks.append(
                self._make_task(
                    index=start_index + offset,
                    layer=1,
                    pattern_type="group_direct",
                    shift=None,
                    source_group_ids=(group_id,),
                    clips=group,
                )
            )
        return tuple(tasks)

    def generate_layer2(
        self,
        groups: tuple[tuple[VideoItem, ...], ...],
        k: int,
        start_index: int = 1,
    ) -> tuple[GenerationTask, ...]:
        """Generate layer 2 cross-group shift tasks."""

        if len(groups) < k:
            return tuple()

        tasks: list[GenerationTask] = []
        task_index = start_index
        for group_indexes in combinations(range(len(groups)), k):
            matrix = tuple(groups[index] for index in group_indexes)
            source_group_ids = tuple(index + 1 for index in group_indexes)
            for shift in range(k):
                for column in range(k):
                    clips = tuple(
                        row[(column + row_index * shift) % k]
                        for row_index, row in enumerate(matrix)
                    )
                    tasks.append(
                        self._make_task(
                            index=task_index,
                            layer=2,
                            pattern_type="cross_group_shift",
                            shift=shift,
                            source_group_ids=source_group_ids,
                            clips=clips,
                        )
                    )
                    task_index += 1
        return tuple(tasks)

    def generate_layer3(
        self,
        groups: tuple[tuple[VideoItem, ...], ...],
        k: int,
        start_index: int = 1,
    ) -> tuple[GenerationTask, ...]:
        """Generate layer 3 one-group-two-clips tasks."""

        if k < 3 or len(groups) < k - 1:
            return tuple()

        tasks: list[GenerationTask] = []
        task_index = start_index
        for double_index, double_group in enumerate(groups):
            remaining_indexes = tuple(index for index in range(len(groups)) if index != double_index)
            for single_indexes in combinations(remaining_indexes, k - 2):
                single_groups = tuple(groups[index] for index in single_indexes)
                source_group_ids = (double_index + 1,) + tuple(index + 1 for index in single_indexes)
                for double_pair in combinations(range(k), 2):
                    for single_positions in product(range(k), repeat=k - 2):
                        clips = (
                            double_group[double_pair[0]],
                            double_group[double_pair[1]],
                            *(
                                single_group[position]
                                for single_group, position in zip(single_groups, single_positions)
                            ),
                        )
                        tasks.append(
                            self._make_task(
                                index=task_index,
                                layer=3,
                                pattern_type="one_group_two_clips",
                                shift=None,
                                source_group_ids=source_group_ids,
                                clips=clips,
                            )
                        )
                        task_index += 1
        return tuple(tasks)

    def _make_task(
        self,
        index: int,
        layer: int,
        pattern_type: str,
        shift: int | None,
        source_group_ids: tuple[int, ...],
        clips: tuple[VideoItem, ...],
    ) -> GenerationTask:
        """Build one normalized task object."""

        clip_ids = tuple(item.item_id for item in clips)
        suffix = "_".join(clip_ids)
        return GenerationTask(
            task_id=f"L{layer}_{index:05d}",
            layer=layer,
            pattern_type=pattern_type,
            shift=shift,
            source_group_ids=source_group_ids,
            clip_ids=clip_ids,
            clip_paths=tuple(item.path for item in clips),
            timeline_name=f"TL_{suffix}",
            output_name=f"OUT_{suffix}",
        )

    def _validate_request(self, request: GenerationRequest) -> None:
        """Validate engine-level invariants."""

        item_count = len(request.items)
        if request.clips_per_output < 2:
            raise ValueError("clips_per_output must be at least 2.")
        if item_count < request.clips_per_output:
            raise ValueError("At least K clips are required to generate tasks.")
        item_ids = tuple(item.item_id for item in request.items)
        if len(set(item_ids)) != item_count:
            raise ValueError("Items must be unique for generation.")
        if request.count < 1:
            raise ValueError("count must be at least 1.")
