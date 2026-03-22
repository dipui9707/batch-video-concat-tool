"""Service orchestration entry point."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from batch_concat.core.config_store import AppConfig, ConfigStore
from batch_concat.core.models import GenerationRequest, GenerationSummary, JobInput, VideoItem
from batch_concat.core.permutation_engine import PermutationEngine
from batch_concat.core.validation import validate_job_inputs
from batch_concat.resolve.script_exporter import ExportedScript, ResolveScriptExporter

LogHandler = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class BatchExportResult:
    """Aggregated result of one exported Resolve script batch."""

    validation: GenerationSummary
    task_count: int
    exported_script: ExportedScript
    was_clamped: bool


class AppService:
    """Coordinate validation, generation, and script export."""

    def __init__(
        self,
        permutation_engine: PermutationEngine | None = None,
        script_exporter: ResolveScriptExporter | None = None,
        config_store: ConfigStore | None = None,
    ) -> None:
        self._config_store = config_store or ConfigStore()
        self._config = self._config_store.load()
        self._permutation_engine = permutation_engine or PermutationEngine()
        self._script_exporter = script_exporter or ResolveScriptExporter()

    def preview_generation(self, video_count: int, clips_per_output: int) -> GenerationSummary:
        """Return generation counters for the current UI selection."""

        return self._permutation_engine.summarize(video_count, clips_per_output)

    def export_batch_script(
        self,
        job_input: JobInput,
        log: LogHandler | None = None,
    ) -> BatchExportResult:
        """Validate input and export a Resolve Lua script for manual execution."""

        logger = log or (lambda message: None)
        logger("开始校验任务参数")
        validation = validate_job_inputs(job_input)
        logger(
            "参数校验通过，"
            f"N={validation.item_count}，"
            f"K={validation.clips_per_output}，"
            f"G={validation.group_count}，"
            f"L1={validation.layer1_count}，"
            f"L2={validation.layer2_count}，"
            f"L3={validation.layer3_count}，"
            f"T={validation.total_count}"
        )
        if validation.leftover_count > 0:
            logger(f"有 {validation.leftover_count} 个素材因不能组成完整分组而被忽略。")

        generation_result = self._permutation_engine.generate(
            GenerationRequest(
                items=job_input.videos,
                clips_per_output=job_input.clips_per_output,
                count=job_input.count,
            )
        )
        if generation_result.was_clamped:
            logger(
                f"请求生成数量 {generation_result.requested_count} 超过上限，"
                f"已自动调整为 {generation_result.effective_count}。"
            )
        logger(f"实际导出任务数量：{generation_result.effective_count}")
        logger(f"已生成 {len(generation_result.tasks)} 个组合任务")
        for task in generation_result.tasks:
            logger(
                f"任务 {task.task_id} | "
                f"layer={task.layer} | "
                f"pattern={task.pattern_type} | "
                f"shift={task.shift if task.shift is not None else '-'} | "
                f"groups={task.source_group_ids} | "
                f"clips={','.join(str(path) for path in task.clip_paths)}"
            )

        script_path = self._default_script_path()
        exported_script = self._script_exporter.export(
            script_path=script_path,
            source_paths=tuple(video.path for video in job_input.videos),
            tasks=generation_result.tasks,
            output_dir=job_input.output_dir,
            aspect_ratio=job_input.aspect_ratio,
        )
        logger(f"已导出 Resolve 脚本：{exported_script.script_path}")
        logger(f"导出比例：{job_input.aspect_ratio}")
        logger("导出格式：mp4")
        logger(f"Lua 运行代码：{exported_script.run_command}")
        logger("请在 DaVinci Resolve 中手动运行该 Lua 脚本。")

        return BatchExportResult(
            validation=validation,
            task_count=len(generation_result.tasks),
            exported_script=exported_script,
            was_clamped=generation_result.was_clamped,
        )

    def build_video_items(self, paths: list[Path]) -> tuple[VideoItem, ...]:
        """Convert selected file paths into stable video items for the GUI."""

        return tuple(
            VideoItem(item_id=str(index), path=path)
            for index, path in enumerate(paths, start=1)
        )

    def get_config(self) -> AppConfig:
        """Return the currently loaded app config."""

        return self._config

    def set_last_output_dir(self, path: Path) -> None:
        """Persist the most recently used output directory."""

        self._config = AppConfig(
            last_output_dir=str(path),
            recent_video_dir=self._config.recent_video_dir,
        )
        self._config_store.save(self._config)

    def set_recent_video_dir(self, path: Path) -> None:
        """Persist the most recently used video directory."""

        self._config = AppConfig(
            last_output_dir=self._config.last_output_dir,
            recent_video_dir=str(path),
        )
        self._config_store.save(self._config)

    def _default_script_path(self) -> Path:
        """Return the default export path for the generated Resolve script."""

        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            preferred_dir = exe_dir / "generated_scripts"
            if self._is_directory_writable(exe_dir):
                return preferred_dir / "batch_concat_resolve_job.lua"

            appdata_dir = ConfigStore.default_config_path().parent / "generated_scripts"
            return appdata_dir / "batch_concat_resolve_job.lua"

        return Path(__file__).resolve().parents[3] / "generated_scripts" / "batch_concat_resolve_job.lua"

    def _is_directory_writable(self, directory: Path) -> bool:
        """Return whether a directory can be created/written by the current user."""

        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".write_test.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except OSError:
            return False
