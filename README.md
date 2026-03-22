# Batch Video Concat Tool

![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)
![DaVinci Resolve](https://img.shields.io/badge/Backend-DaVinci%20Resolve%20Lua-1A1A1A)
![Build](https://img.shields.io/badge/Build-PyInstaller-orange)

Windows desktop app for non-CLI users that builds deterministic multi-layer video-combination tasks and exports a DaVinci Resolve Lua script for manual execution.

## What It Does

- Import multiple full-length video files in a Windows GUI
- Reorder clips as the base source order
- Generate deterministic combination tasks with `L1 + L2 + L3`
- Export a Resolve Lua script instead of requiring command-line use
- Let the user manually run the Lua script inside DaVinci Resolve
- Batch-create timelines and render tasks with default `mp4` output

## Current Product Shape

This project intentionally keeps a narrow scope:

- Windows desktop app
- PySide6 GUI
- DaVinci Resolve Lua export workflow
- No clip cutting
- No scene analysis
- No subtitles
- No transitions
- No random generation
- No full permutation mode

## Screenshot

No repository screenshot asset is included yet.

Recommended next step:

1. Launch the packaged app
2. Capture the main window
3. Save it under `docs/images/main-window.png`
4. Replace this section with:

```md
![Main Window](docs/images/main-window.png)
```

## Generation Logic

Definitions:

- `N`: total imported clips
- `K`: clips per output video
- `G = floor(N / K)`: complete group count

Only the first `G * K` clips participate.
Leftover clips are ignored in this version and are shown in the UI and logs.

### Layer 1

Split clips by import order into groups of size `K`.
Each group generates one direct task.

- `L1 = G`

### Layer 2

Choose `K` groups from the `G` complete groups and form a `K x K` matrix.
Layer 2 includes:

- same-column extraction
- all cyclic shifts from `0` to `K-1`

- `L2 = C(G, K) * K^2`

### Layer 3

Exactly one group contributes `2` clips.
The remaining `K-2` clips each come from a different other group.

Generic structure:

- `2 + 1 + 1 + ... + 1`

- `L3 = G * C(G-1, K-2) * C(K, 2) * K^(K-2)`

### Total

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

## Workflow

1. Add multiple full video files in the GUI
2. Reorder them as the base import order
3. Set `K`
4. Set the requested generation count
5. Review live counters: `N`, `G`, `L1`, `L2`, `L3`, `T`, and leftover clips
6. Choose the video output directory
7. Choose the export aspect ratio
8. Click `导出脚本`
9. The app writes a Lua file to:
   - `generated_scripts/batch_concat_resolve_job.lua`
   - repeated exports overwrite the previous file at the same path
10. Copy the Lua command shown in the GUI log
11. Run it in DaVinci Resolve Lua Console

Example Lua command:

```lua
dofile([[C:/.../generated_scripts/batch_concat_resolve_job.lua]])
```

## Output Defaults

Default render output:

- `mp4`
- `H.264`

If the current Resolve build rejects one codec string, the script tries the compatible fallback.

Supported aspect ratio presets:

- `竖屏 9:16` -> `1080x1920`
- `竖屏 3:4` -> `1080x1440`
- `横屏 16:9` -> `1920x1080`
- `横屏 4:3` -> `1440x1080`
- `方形 1:1` -> `1080x1080`

Recommended import suffixes for Windows free DaVinci Resolve:

- `mp4`
- `mov`
- `mkv`
- `avi`
- `mxf`
- `mts`
- `m2ts`

## Download

### Source Code

- Repository: <https://github.com/dipui9707/batch-video-concat-tool>

### Packaged Windows Build

Current packaged build file name:

- `BatchVideoConcatTool-win64.zip`

Recommended distribution flow:

1. Open the repository `Releases` page after a release is published
2. Download `BatchVideoConcatTool-win64.zip`
3. Extract the full archive
4. Run `BatchVideoConcatTool.exe`

Notes:

- Do not copy out only the `.exe`
- Keep the full extracted folder structure
- Python does not need to be installed on the target machine

## Local Development

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

## Windows Packaging

Build the distributable app:

```powershell
.\build_windows.ps1
```

Packaged app path:

- `dist/BatchVideoConcatTool/BatchVideoConcatTool.exe`

Zip release path:

- `release/BatchVideoConcatTool-win64.zip`

## Project Status

Implemented:

- 3-layer generation engine
- deterministic task ordering
- validation for `K`, `count`, file paths, and output directory
- PySide6 Windows GUI
- Resolve Lua script export
- manual Resolve Console workflow
- aspect ratio presets
- unsupported import format warning
- unit tests for core generation logic
- Windows packaging with PyInstaller

Not implemented:

- direct auto-connection to DaVinci Resolve
- automatic script execution inside Resolve

