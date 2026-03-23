"""Tests for Resolve Lua script export."""

from __future__ import annotations

from pathlib import Path

from batch_concat.core.models import ExportAspectRatio, GenerationTask
from batch_concat.resolve.script_exporter import ResolveScriptExporter


def test_export_writes_lua_script_with_paths_and_sequences(tmp_path: Path) -> None:
    exporter = ResolveScriptExporter()
    script_path = tmp_path / "job.lua"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    source_paths = (
        Path(r"C:\video\1.mp4"),
        Path(r"C:\video\2.mp4"),
    )
    tasks = (
        GenerationTask(
            task_id="L1_00001",
            layer=1,
            pattern_type="group_direct",
            shift=None,
            source_group_ids=(1,),
            clip_ids=("2", "1"),
            clip_paths=(source_paths[1], source_paths[0]),
            timeline_name="TL_2_1",
            output_name="OUT_2_1",
        ),
        GenerationTask(
            task_id="L1_00002",
            layer=1,
            pattern_type="group_direct",
            shift=None,
            source_group_ids=(1,),
            clip_ids=("1", "2"),
            clip_paths=(source_paths[0], source_paths[1]),
            timeline_name="TL_1_2",
            output_name="OUT_1_2",
        ),
    )

    result = exporter.export(
        script_path=script_path,
        source_paths=source_paths,
        tasks=tasks,
        output_dir=output_dir,
        aspect_ratio=ExportAspectRatio.HORIZONTAL_16_9,
    )

    content = script_path.read_text(encoding="utf-8")

    assert result.script_path == script_path
    assert result.timeline_names == ("TL_2_1", "TL_1_2")
    assert result.output_names == ("OUT_2_1", "OUT_1_2")
    assert result.run_command == "dofile([[C:/tmp/job.lua]])".replace("C:/tmp/job.lua", str(script_path).replace("\\", "/"))
    assert "[[C:/video/1.mp4]]" in content
    assert "[[C:/video/2.mp4]]" in content
    assert (output_dir / "CacheClip").exists()
    assert (output_dir / ".gallery").exists()
    assert f"local cacheDir = [[{str((output_dir / 'CacheClip')).replace(chr(92), '/')}]]" in content
    assert f"local galleryDir = [[{str((output_dir / '.gallery')).replace(chr(92), '/')}]]" in content
    assert "string.find(lowerKey, 'cache')" in content
    assert "string.find(lowerKey, 'gallery')" in content
    assert "local tasks = {" in content
    assert "local function resolveClips(clipIds)" in content
    assert "local function queueTask(task)" in content
    assert "clipIds = { [[2]], [[1]] }" in content
    assert "project:SetCurrentRenderFormatAndCodec('mp4', 'H.264')" in content
    assert "project:SetSetting('timelineResolutionWidth', '1920')" in content
    assert "project:SetSetting('timelineResolutionHeight', '1080')" in content
    assert "timelineName = [[TL_2_1]]" in content
    assert "outputName = [[OUT_1_2]]" in content


def test_export_uses_shared_task_queue_code_for_many_tasks(tmp_path: Path) -> None:
    exporter = ResolveScriptExporter()
    script_path = tmp_path / "job.lua"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    source_paths = tuple(Path(fr"C:\video\{index}.mp4") for index in range(1, 5))
    tasks = tuple(
        GenerationTask(
            task_id=f"T_{index:05d}",
            layer=3,
            pattern_type="one_group_two_clips",
            shift=None,
            source_group_ids=(1, 2, 3),
            clip_ids=("1", "2", "3", "4"),
            clip_paths=source_paths,
            timeline_name=f"TL_{index:05d}",
            output_name=f"OUT_{index:05d}",
        )
        for index in range(1, 260)
    )

    exporter.export(
        script_path=script_path,
        source_paths=source_paths,
        tasks=tasks,
        output_dir=output_dir,
        aspect_ratio=ExportAspectRatio.HORIZONTAL_16_9,
    )

    content = script_path.read_text(encoding="utf-8")

    assert content.count("local function queueTask(task)") == 1
    assert content.count("local timeline = mediaPool:CreateEmptyTimeline(timelineName)") == 1
    assert content.count("taskId = [[T_") == len(tasks)
