# Batch Video Concat Tool

Windows desktop app for non-CLI users that generates deterministic multi-layer video-combination tasks and exports a DaVinci Resolve Lua script for manual execution.

## Current status

Implemented:

- 3-layer generation engine based on `N / K / G`
- Validation for `K`, `count`, file paths, and output directory
- PySide6 Windows GUI
- Resolve Lua script export
- Manual Resolve Console workflow
- Aspect ratio presets
- Unsupported import format warning
- Core unit tests

Not implemented:

- Desktop app auto-connect / auto-run DaVinci Resolve

## Current generation logic

Definitions:

- `N`: total imported clips
- `K`: clips per output video
- `G = floor(N / K)`: complete group count

Only the first `G * K` clips participate. Leftover clips are ignored and reported in the UI/logs.

Layers:

1. `L1 = G`
   Split clips by import order into groups of size `K`, then output one task per group.
2. `L2 = C(G, K) * K^2`
   Choose `K` groups and build a `K x K` matrix. Generate all `shift=0..K-1` tasks in stable order.
3. `L3 = G * C(G-1, K-2) * C(K,2) * K^(K-2)`
   Exactly one group contributes 2 clips. The remaining `K-2` clips each come from a different other group.

Total:

- `T = L1 + L2 + L3`

Example for `N=20, K=4`:

- `G = 5`
- `L1 = 5`
- `L2 = 80`
- `L3 = 2880`
- `T = 2965`

Generation order is fixed and deterministic:

1. all Layer 1 tasks
2. all Layer 2 tasks
3. all Layer 3 tasks

## Current workflow

1. Add multiple full video files in the GUI.
2. Reorder them as the base import order.
3. Set `K` (clips per output video).
4. Set the requested generation count.
5. Review the live counters: `N`, `G`, `L1`, `L2`, `L3`, `T`, and ignored leftovers.
6. Choose the rendered video output directory.
7. Choose the export aspect ratio.
8. Click `导出脚本`.
9. The app writes a Lua script to:
   - `generated_scripts/batch_concat_resolve_job.lua`
   - repeated exports overwrite the previous script at the same path
10. Copy the generated Lua command from the GUI log:

```lua
dofile([[C:/.../generated_scripts/batch_concat_resolve_job.lua]])
```

11. Run that command in DaVinci Resolve Lua Console.

## Export settings

Default output format:

- `mp4`
- `H.264` with `H264` fallback in the Resolve script
- Resolve cache-related folders are redirected under the selected video output directory when supported by the current project settings

Recommended import suffixes for Windows free DaVinci Resolve:

- `mp4`
- `mov`
- `mkv`
- `avi`
- `mxf`
- `mts`
- `m2ts`

Supported aspect ratios:

- `竖屏 9:16` -> `1080x1920`
- `竖屏 3:4` -> `1080x1440`
- `横屏 16:9` -> `1920x1080`
- `横屏 4:3` -> `1440x1080`
- `方形 1:1` -> `1080x1080`

## Local development

Install:

```powershell
python -m pip install -e .[dev]
```

Run tests:

```powershell
python -m pytest -q
```

Start the app:

```powershell
python -m batch_concat.main
```

## Windows packaging

Build the distributable app:

```powershell
.\build_windows.ps1
```

After packaging, the one-click Windows app is here:

- `dist/BatchVideoConcatTool/BatchVideoConcatTool.exe`

Notes:

- The Python runtime and required Qt environment are bundled inside the `dist/BatchVideoConcatTool` folder.
- Ordinary Windows users can run `BatchVideoConcatTool.exe` directly without installing Python.
- Keep the whole `dist/BatchVideoConcatTool` folder together when copying to another machine.
