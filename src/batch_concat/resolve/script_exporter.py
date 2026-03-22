"""Export DaVinci Resolve Lua scripts for manual execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from batch_concat.core.models import ExportAspectRatio, GenerationTask


ASPECT_RATIO_SETTINGS: dict[ExportAspectRatio, tuple[int, int]] = {
    ExportAspectRatio.VERTICAL_9_16: (1080, 1920),
    ExportAspectRatio.VERTICAL_3_4: (1080, 1440),
    ExportAspectRatio.HORIZONTAL_16_9: (1920, 1080),
    ExportAspectRatio.HORIZONTAL_4_3: (1440, 1080),
    ExportAspectRatio.SQUARE_1_1: (1080, 1080),
}

@dataclass(frozen=True, slots=True)
class ExportedScript:
    """Metadata about a generated Resolve script."""

    script_path: Path
    timeline_names: tuple[str, ...]
    output_names: tuple[str, ...]
    run_command: str


class ResolveScriptExporter:
    """Generate a Lua script that Resolve can run manually."""

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
        """Write a Lua script that imports clips, builds timelines, and queues renders."""

        cache_dir = output_dir / "CacheClip"
        gallery_dir = output_dir / ".gallery"
        cache_dir.mkdir(parents=True, exist_ok=True)
        gallery_dir.mkdir(parents=True, exist_ok=True)

        source_map = {str(index): path for index, path in enumerate(source_paths, start=1)}
        timeline_names = tuple(
            task.timeline_name or self.make_timeline_name(task.clip_ids, timeline_prefix)
            for task in tasks
        )
        output_names = tuple(
            task.output_name or self.make_output_name(task.clip_ids, output_prefix)
            for task in tasks
        )

        lua = self._build_lua(
            source_map=source_map,
            tasks=tasks,
            output_dir=output_dir,
            cache_dir=cache_dir,
            gallery_dir=gallery_dir,
            aspect_ratio=aspect_ratio,
            timeline_names=timeline_names,
            output_names=output_names,
        )
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(lua, encoding="utf-8")
        return ExportedScript(
            script_path=script_path,
            timeline_names=timeline_names,
            output_names=output_names,
            run_command=self.make_run_command(script_path),
        )

    def make_timeline_name(self, sequence_ids: tuple[str, ...], prefix: str = "TL") -> str:
        """Build a deterministic timeline name from sequence ids."""

        return f"{prefix}_{'_'.join(sequence_ids)}"

    def make_output_name(self, sequence_ids: tuple[str, ...], prefix: str = "OUT") -> str:
        """Build a deterministic output base name from sequence ids."""

        return f"{prefix}_{'_'.join(sequence_ids)}"

    def make_run_command(self, script_path: Path) -> str:
        """Build the Lua command that can be pasted into Resolve Console."""

        normalized = str(script_path).replace("\\", "/")
        return f"dofile([[{normalized}]])"

    def _build_lua(
        self,
        source_map: dict[str, Path],
        tasks: tuple[GenerationTask, ...],
        output_dir: Path,
        cache_dir: Path,
        gallery_dir: Path,
        aspect_ratio: ExportAspectRatio,
        timeline_names: tuple[str, ...],
        output_names: tuple[str, ...],
    ) -> str:
        """Build the Resolve Lua script source."""

        width, height = ASPECT_RATIO_SETTINGS[aspect_ratio]
        import_lines = ",\n".join(
            f"  {self._lua_string(str(path))}" for path in source_map.values()
        )
        clip_map_lines = "\n".join(
            f'clipMap["{item_id}"] = importedClips[{index}]'
            for index, item_id in enumerate(source_map.keys(), start=1)
        )
        sequence_blocks = []
        for index, task in enumerate(tasks, start=1):
            clip_lines = ", ".join(f'clipMap["{item_id}"]' for item_id in task.clip_ids)
            sequence_blocks.append(
                "\n".join(
                    [
                        f"-- Task {task.task_id}: layer={task.layer}, pattern={task.pattern_type}",
                        f"local timelineName = {self._lua_string(timeline_names[index - 1])}",
                        "local timeline = mediaPool:CreateEmptyTimeline(timelineName)",
                        "if timeline == nil then error('Failed to create timeline: ' .. timelineName) end",
                        "if not project:SetCurrentTimeline(timeline) then error('Failed to activate timeline: ' .. timelineName) end",
                        f"local clips = {{ {clip_lines} }}",
                        "local appended = mediaPool:AppendToTimeline(clips)",
                        "if appended == nil then error('Failed to append clips to timeline: ' .. timelineName) end",
                        "local settings = {",
                        f"  TargetDir = {self._lua_string(str(output_dir))},",
                        f"  CustomName = {self._lua_string(output_names[index - 1])},",
                        "}",
                        "if not project:SetRenderSettings(settings) then error('Failed to apply render settings: ' .. timelineName) end",
                        "local renderJobId = project:AddRenderJob()",
                        "if renderJobId == nil or renderJobId == '' then error('Failed to add render job: ' .. timelineName) end",
                    ]
                )
            )

        sequence_section = "\n\n".join(sequence_blocks)
        return "\n".join(
            [
                "-- Auto-generated by Batch Video Concat Tool",
                "local resolve = nil",
                "if type(Resolve) == 'function' then",
                "  resolve = Resolve()",
                "end",
                "if resolve == nil and type(app) == 'table' and type(app.GetResolve) == 'function' then",
                "  resolve = app:GetResolve()",
                "end",
                "if resolve == nil and type(fusion) == 'table' and type(fusion.GetResolve) == 'function' then",
                "  resolve = fusion:GetResolve()",
                "end",
                "if resolve == nil and _G.resolve ~= nil then",
                "  resolve = _G.resolve",
                "end",
                "if resolve == nil then error('Resolve object is unavailable. Please run this script from DaVinci Resolve Workspace > Scripts or a Resolve Lua console with scripting enabled.') end",
                "local projectManager = resolve:GetProjectManager()",
                "if projectManager == nil then error('Project manager is unavailable.') end",
                "local project = projectManager:GetCurrentProject()",
                "if project == nil then error('No project is currently open in Resolve.') end",
                "local mediaPool = project:GetMediaPool()",
                "if mediaPool == nil then error('Media Pool is unavailable.') end",
                f"local cacheDir = {self._lua_string(str(cache_dir))}",
                f"local galleryDir = {self._lua_string(str(gallery_dir))}",
                "local function applyWorkingFolderOverrides()",
                "  local settings = project:GetSetting()",
                "  if type(settings) ~= 'table' then",
                "    return",
                "  end",
                "  for key, _ in pairs(settings) do",
                "    local rawKey = tostring(key)",
                "    local lowerKey = string.lower(rawKey)",
                "    if string.find(lowerKey, 'cache') then",
                "      project:SetSetting(rawKey, cacheDir)",
                "    elseif string.find(lowerKey, 'gallery') or string.find(lowerKey, 'still') then",
                "      project:SetSetting(rawKey, galleryDir)",
                "    end",
                "  end",
                "end",
                "applyWorkingFolderOverrides()",
                f"if not project:SetSetting('timelineResolutionWidth', '{width}') then error('Failed to set timeline width.') end",
                f"if not project:SetSetting('timelineResolutionHeight', '{height}') then error('Failed to set timeline height.') end",
                f"if not project:SetSetting('timelineOutputResolutionWidth', '{width}') then error('Failed to set output width.') end",
                f"if not project:SetSetting('timelineOutputResolutionHeight', '{height}') then error('Failed to set output height.') end",
                "project:SetCurrentRenderMode(1)",
                "local renderCodecSet = project:SetCurrentRenderFormatAndCodec('mp4', 'H264')",
                "if not renderCodecSet then",
                "  renderCodecSet = project:SetCurrentRenderFormatAndCodec('mp4', 'H.264')",
                "end",
                "if not renderCodecSet then error('Failed to set render format to mp4/H.264.') end",
                "",
                "local importPaths = {",
                import_lines,
                "}",
                "local importedClips = mediaPool:ImportMedia(importPaths)",
                f"if importedClips == nil or #importedClips ~= {len(source_map)} then error('Resolve failed to import one or more source clips.') end",
                "local clipMap = {}",
                clip_map_lines,
                "",
                sequence_section,
                "",
                "if not project:StartRendering() then",
                "  error('Failed to start rendering.')",
                "end",
                "print('Render jobs queued and started successfully.')",
            ]
        ) + "\n"

    def _lua_string(self, value: str) -> str:
        """Quote a string for safe use in Lua source."""

        normalized = value.replace("\\", "/")
        escaped = normalized.replace("]]", "] ]")
        return f"[[{escaped}]]"
