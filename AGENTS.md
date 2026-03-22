## Project
Windows 批量视频组合拼接工具（DaVinci Resolve）

## Mission
Build a Windows desktop app for non-CLI users that batches full-length source videos into deterministic combination tasks and exports them through DaVinci Resolve Lua scripting.

## Hard boundaries
- No video cutting
- No AI recognition
- No subtitles
- No transitions
- No web app
- No cloud backend
- No random generation
- No full permutation mode in the current version

## Tech stack
- Python 3.11+
- PySide6
- PyInstaller
- JSON config
- DaVinci Resolve Lua scripting

## Engineering rules
- Keep UI and business logic separate
- Use type hints
- Add docstrings
- Add tests for core logic
- Prefer simple architecture
- Handle user-facing errors clearly
- Do not add unnecessary dependencies
- Build incrementally

## Current workflow
- The desktop app does not auto-connect to Resolve.
- The app exports a Lua script.
- The user runs that script manually in DaVinci Resolve Lua Console.

## Current generation-logic override

This section is the authoritative rule for generation.

### Definitions
- `N` = total imported clips
- `K` = clips per output video
- `G = floor(N / K)` = complete group count

Only the first `G * K` clips participate.
Leftover clips are ignored and must be shown in UI/logs.

### Layer 1
Split clips by import order into groups of size `K`.
Each group generates one direct task.

Formula:
- `L1 = G`

### Layer 2
Choose `K` groups from the `G` complete groups and form a `K x K` matrix.
Layer 2 includes:
- same-column extraction
- all non-zero cyclic-shift extraction

Formula:
- `L2 = C(G, K) * K^2`

### Layer 3
Exactly one group contributes 2 clips.
The remaining `K-2` clips each come from different other groups.

Generic structure:
- `2 + 1 + 1 + ... + 1`

Formula:
- `L3 = G * C(G-1, K-2) * C(K,2) * K^(K-2)`

### Total
- `T = L1 + L2 + L3`

### Required generation order
1. all Layer 1 tasks
2. all Layer 2 tasks
3. all Layer 3 tasks

Inside Layer 2:
- group combinations in stable order
- shifts from `0` to `K-1`
- columns left to right

Inside Layer 3:
- double-source group ascending
- single-source group combination order stable
- 2-clip combination in the double-source group stable
- remaining single-source clip selections lexicographic and reproducible

### Validation requirements
- `K < 2` is invalid
- `N < K` cannot generate tasks
- if `G < K`, then `L2 = 0`
- if `K < 3` or `G < K-1`, then `L3 = 0`
- if requested `count > T`, clamp to `T` and show a message
- no crashes on edge cases

### Minimum test expectations
- `N=20, K=4 => G=5, L1=5, L2=80, L3=2880, T=2965`
- `N=8, K=4 => G=2, L1=2, L2=0, L3=0`
- `N=10, K=4 => G=2, leftover=2`
- requested `count > T` clamps to `T`
