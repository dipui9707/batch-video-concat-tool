"""Tests for application service orchestration."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from batch_concat.core.config_store import ConfigStore
from batch_concat.core.models import ExportAspectRatio, GenerationTask, JobInput, VideoItem
from batch_concat.resolve.script_exporter import ExportedScript
from batch_concat.services.app_service import AppService


class FakeScriptExporter:
    """Script exporter stub for service tests."""

    def __init__(self) -> None:
        self.received_tasks: tuple[GenerationTask, ...] = tuple()
        self.received_script_path: Path | None = None

    def export(
        self,
        script_path: Path,
        source_paths: tuple[Path, ...],
        tasks: tuple[GenerationTask, ...],
        output_dir: Path,
        aspect_ratio: ExportAspectRatio,
        timeline_prefix: str = "TL",
        output_prefix: str = "OUT",
    ) -> ExportedScript:
        self.received_tasks = tasks
        self.received_script_path = script_path
        return ExportedScript(
            script_path=script_path,
            timeline_names=tuple(task.timeline_name for task in tasks),
            output_names=tuple(task.output_name for task in tasks),
            run_command=f"dofile([[{str(script_path).replace(chr(92), '/')}]] )",
        )


def test_export_batch_script_clamps_count_and_logs_summary(tmp_path: Path) -> None:
    videos = []
    for name in ("a.mp4", "b.mp4", "c.mp4", "d.mp4", "e.mp4", "f.mp4", "g.mp4", "h.mp4"):
        path = tmp_path / name
        path.write_bytes(b"x")
        videos.append(path)

    exporter = FakeScriptExporter()
    service = AppService(script_exporter=exporter)
    logs: list[str] = []

    result = service.export_batch_script(
        JobInput(
            videos=tuple(VideoItem(item_id=str(index), path=path) for index, path in enumerate(videos, start=1)),
            clips_per_output=4,
            count=99,
            aspect_ratio=ExportAspectRatio.VERTICAL_9_16,
            output_dir=tmp_path,
        ),
        log=logs.append,
    )

    assert result.task_count == 2
    assert result.was_clamped is True
    assert exporter.received_script_path == Path(__file__).resolve().parents[1] / "generated_scripts" / "batch_concat_resolve_job.lua"
    assert any("G=2" in message for message in logs)
    assert any("L3=0" in message for message in logs)
    assert any("已自动调整为 2" in message for message in logs)


def test_export_batch_script_logs_ignored_leftover_clips(tmp_path: Path) -> None:
    videos = []
    for name in ("a.mp4", "b.mp4", "c.mp4", "d.mp4", "e.mp4"):
        path = tmp_path / name
        path.write_bytes(b"x")
        videos.append(path)

    exporter = FakeScriptExporter()
    service = AppService(script_exporter=exporter)
    logs: list[str] = []

    result = service.export_batch_script(
        JobInput(
            videos=tuple(VideoItem(item_id=str(index), path=path) for index, path in enumerate(videos, start=1)),
            clips_per_output=2,
            count=2,
            aspect_ratio=ExportAspectRatio.VERTICAL_9_16,
            output_dir=tmp_path,
        ),
        log=logs.append,
    )

    assert result.validation.leftover_count == 1
    assert any("被忽略" in message for message in logs)


def test_export_batch_script_logs_per_task_details(tmp_path: Path) -> None:
    videos = []
    for name in ("a.mp4", "b.mp4", "c.mp4", "d.mp4"):
        path = tmp_path / name
        path.write_bytes(b"x")
        videos.append(path)

    exporter = FakeScriptExporter()
    service = AppService(script_exporter=exporter)
    logs: list[str] = []

    result = service.export_batch_script(
        JobInput(
            videos=tuple(VideoItem(item_id=str(index), path=path) for index, path in enumerate(videos, start=1)),
            clips_per_output=4,
            count=1,
            aspect_ratio=ExportAspectRatio.VERTICAL_9_16,
            output_dir=tmp_path,
        ),
        log=logs.append,
    )

    assert result.task_count == 1
    assert exporter.received_tasks[0].layer == 1
    assert any("任务 L1_" in message for message in logs)


def test_default_script_path_uses_exe_dir_when_frozen_and_writable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AppService()
    exe_path = tmp_path / "BatchVideoConcatTool.exe"
    exe_path.write_bytes(b"x")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path))

    assert service._default_script_path() == tmp_path / "generated_scripts" / "batch_concat_resolve_job.lua"


def test_default_script_path_falls_back_to_appdata_when_frozen_dir_not_writable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AppService()
    exe_path = tmp_path / "BatchVideoConcatTool.exe"
    exe_path.write_bytes(b"x")
    fallback_config_path = tmp_path / "roaming" / "BatchConcatTool" / "config.json"

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path))
    monkeypatch.setattr(service, "_is_directory_writable", lambda directory: False)
    monkeypatch.setattr(ConfigStore, "default_config_path", staticmethod(lambda: fallback_config_path))

    assert service._default_script_path() == tmp_path / "roaming" / "BatchConcatTool" / "generated_scripts" / "batch_concat_resolve_job.lua"
