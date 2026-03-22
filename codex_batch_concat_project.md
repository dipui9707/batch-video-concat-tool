# Windows 批量视频组合拼接工具（DaVinci Resolve）项目说明

## 1. 当前项目定位

这是一个面向 Windows 普通用户的 PySide6 桌面程序。

当前真实工作流是：

1. 用户在 GUI 中选择素材、设置参数
2. 程序生成 3 层组合任务
3. 程序导出 DaVinci Resolve Lua 脚本
4. 用户在 Resolve 的 Lua Console 中手动运行脚本
5. Resolve 完成导入素材、创建时间线、加入渲染队列和开始渲染

## 2. 当前组合规则

定义：

- `N`：素材总数
- `K`：每条输出使用素材数
- `G = floor(N / K)`：完整分组数

只有前 `G*K` 个素材参与生成。
剩余素材会被忽略，并在 GUI 和日志中显示。

### Layer 1

- 按导入顺序，每 `K` 个素材形成一组
- 每组生成 1 条任务

公式：

- `L1 = G`

### Layer 2

- 从 `G` 个完整分组中选 `K` 组
- 构造 `K x K` 矩阵
- 生成 shift `0..K-1` 的全部稳定任务

公式：

- `L2 = C(G, K) * K^2`

### Layer 3

- 恰好有 1 个分组提供 2 个素材
- 剩余 `K-2` 个素材分别来自不同的其它分组

结构：

- `2 + 1 + 1 + ... + 1`

公式：

- `L3 = G * C(G-1, K-2) * C(K,2) * K^(K-2)`

### 总量

- `T = L1 + L2 + L3`

示例：

当 `N=20, K=4` 时：

- `G=5`
- `L1=5`
- `L2=80`
- `L3=2880`
- `T=2965`

### 固定顺序

任务必须按下面顺序输出：

1. 全部 `L1`
2. 全部 `L2`
3. 全部 `L3`

## 3. 当前项目结构

```text
src/batch_concat/
├─ main.py
├─ core/
│  ├─ config_store.py
│  ├─ models.py
│  ├─ permutation_engine.py
│  └─ validation.py
├─ resolve/
│  └─ script_exporter.py
├─ services/
│  └─ app_service.py
└─ ui/
   └─ main_window.py
```

## 4. 关键模块职责

### `core/models.py`

定义：

- `VideoItem`
- `GenerationRequest`
- `GenerationSummary`
- `GenerationTask`
- `GenerationResult`
- `JobInput`
- `ExportAspectRatio`

### `core/permutation_engine.py`

负责：

- 计算 `G / L1 / L2 / L3 / T`
- 生成全部候选任务
- 保证任务顺序稳定
- 对 `count` 做截断

### `core/validation.py`

负责：

- `K >= 2`
- `count >= 1`
- `N >= K`
- 文件存在
- 输出目录存在且可写
- item id 唯一

### `services/app_service.py`

负责：

- 调用校验
- 调用组合引擎
- 输出 GUI 日志
- 将任务喂给 Lua 脚本导出器

### `resolve/script_exporter.py`

负责把生成任务导出成可在 Resolve 中执行的 Lua，包括：

- 导入素材
- 建立 clip 映射
- 创建 timeline
- 按任务顺序追加素材
- 设置输出目录与文件名
- 加入 render queue
- 开始渲染

### `ui/main_window.py`

负责：

- 素材导入与排序
- 参数输入
- 统计显示
- 不支持格式提示
- 脚本导出

## 5. GUI 当前状态

当前 GUI 已支持：

- 显示推荐导入格式
- 设置 `K`
- 设置导出任务数量
- 显示 `N / G / L1 / L2 / L3 / T / 忽略素材`
- 显示当前公式
- 选择视频输出目录
- 选择导出比例
- 提示同名脚本会被覆盖

## 6. 当前导出策略

### 脚本路径

脚本固定导出到：

- `generated_scripts/batch_concat_resolve_job.lua`

重复导出会覆盖上一份同名脚本。

### 视频输出

视频输出目录由用户在 GUI 中指定。

### 导出格式

默认导出：

- `mp4`

脚本内部会优先尝试：

- `mp4 + H.264`

失败时回退：

- `mp4 + H264`

### 比例预设

- `竖屏 9:16`
- `竖屏 3:4`
- `横屏 16:9`
- `横屏 4:3`
- `方形 1:1`

## 7. 当前测试覆盖

已覆盖：

- `N=20, K=4 => G=5, L1=5, L2=80, L3=2880, T=2965`
- `N=8, K=4 => G=2, L1=2, L2=0, L3=0`
- `N=10, K=4 => leftover=2`
- `count > T` 自动截断
- Layer 3 顺序稳定性
- GUI 计数刷新
- GUI 不支持格式提示
- Lua 脚本导出
- 配置读写

## 8. 本地开发命令

安装：

```powershell
python -m pip install -e .[dev]
```

测试：

```powershell
python -m pytest -q
```

启动：

```powershell
python -m batch_concat.main
```

打包：

```powershell
.\build_windows.ps1
```
