"""Main window for the batch video concat desktop application."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from batch_concat.core.models import ExportAspectRatio, JobInput
from batch_concat.services.app_service import AppService


SUPPORTED_IMPORT_SUFFIXES: tuple[str, ...] = (
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".mxf",
    ".mts",
    ".m2ts",
)


class MainWindow(QMainWindow):
    """Desktop GUI for configuring and exporting batch concat jobs."""

    def __init__(self, app_service: AppService | None = None) -> None:
        super().__init__()
        self._app_service = app_service or AppService()
        self.setWindowTitle("批量视频组合拼接工具")
        self.resize(980, 720)

        self.video_list = QListWidget()
        self.video_list.currentRowChanged.connect(self._update_button_states)

        self.add_button = QPushButton("添加视频")
        self.remove_button = QPushButton("删除选中")
        self.move_up_button = QPushButton("上移")
        self.move_down_button = QPushButton("下移")
        self.output_dir_edit = QLineEdit()
        self.browse_output_button = QPushButton("选择目录")
        self.k_spinbox = QSpinBox()
        self.k_spinbox.setMinimum(2)
        self.k_spinbox.valueChanged.connect(self._refresh_generation_stats)
        self.count_spinbox = QSpinBox()
        self.count_spinbox.setMinimum(1)
        self.count_spinbox.valueChanged.connect(self._sync_count_hint)
        self.aspect_ratio_group = QButtonGroup(self)
        self.aspect_ratio_buttons: dict[ExportAspectRatio, QRadioButton] = {}
        self.item_count_label = QLabel("N：0")
        self.group_count_label = QLabel("G：0")
        self.layer1_label = QLabel("L1：0")
        self.layer2_label = QLabel("L2：0")
        self.layer3_label = QLabel("L3：0")
        self.total_count_label = QLabel("T：0")
        self.leftover_label = QLabel("忽略素材：0")
        self.formula_label = QLabel("公式：G=floor(N/K)，L1=G，L2=C(G,K)*K^2，L3=G*C(G-1,K-2)*C(K,2)*K^(K-2)")
        self.formula_hint_label = QLabel("说明：N=素材总数，K=每条输出使用素材数；仅前 G*K 个素材参与组合，其余会被忽略；T=L1+L2+L3。")
        self.layer_logic_hint_label = QLabel("层级说明：L1=组内直出；L2=每组最多取1个素材的跨组组合；L3=恰好1组取2个素材，其余组各取1个素材。")
        self.script_overwrite_hint_label = QLabel("脚本说明：脚本固定导出为 generated_scripts/batch_concat_resolve_job.lua；重复导出会覆盖上一份脚本。")
        self.status_label = QLabel("就绪")
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.start_button = QPushButton("导出脚本")

        self._setup_ui()
        self._connect_signals()
        self._load_saved_paths()
        self._update_button_states()
        self._refresh_generation_stats()

    def _setup_ui(self) -> None:
        """Build the main window layout."""

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.addWidget(self._build_video_group())
        root_layout.addWidget(self._build_options_group())
        root_layout.addWidget(self._build_log_group())

        footer_layout = QHBoxLayout()
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self.start_button)
        root_layout.addLayout(footer_layout)

    def _build_video_group(self) -> QGroupBox:
        """Create the video selection group."""

        group = QGroupBox("素材列表")
        layout = QVBoxLayout(group)
        supported_text = "推荐导入格式：mp4、mov、mkv、avi、mxf、mts、m2ts"
        layout.addWidget(QLabel(supported_text))
        layout.addWidget(self.video_list)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.move_up_button)
        button_layout.addWidget(self.move_down_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)
        return group

    def _build_options_group(self) -> QGroupBox:
        """Create the parameter input group."""

        group = QGroupBox("组合设置")
        layout = QGridLayout(group)

        layout.addWidget(QLabel("每条输出使用素材数 K"), 0, 0)
        layout.addWidget(self.k_spinbox, 0, 1)
        layout.addWidget(QLabel("导出任务数量"), 0, 2)
        layout.addWidget(self.count_spinbox, 0, 3)
        layout.addWidget(self.total_count_label, 0, 4)

        layout.addWidget(self.item_count_label, 1, 0)
        layout.addWidget(self.group_count_label, 1, 1)
        layout.addWidget(self.layer1_label, 1, 2)
        layout.addWidget(self.layer2_label, 1, 3)
        layout.addWidget(self.layer3_label, 1, 4)
        layout.addWidget(self.leftover_label, 2, 4)

        stats_hint = QLabel("统计说明：N=素材总数，G=完整分组数，L1/L2/L3=三层任务数，T=总任务数")
        layout.addWidget(stats_hint, 3, 0, 1, 5)
        layout.addWidget(self.formula_label, 4, 0, 1, 5)
        layout.addWidget(self.formula_hint_label, 5, 0, 1, 5)
        layout.addWidget(self.layer_logic_hint_label, 6, 0, 1, 5)
        layout.addWidget(self.script_overwrite_hint_label, 7, 0, 1, 5)

        layout.addWidget(QLabel("视频输出目录"), 8, 0)
        layout.addWidget(self.output_dir_edit, 8, 1, 1, 3)
        layout.addWidget(self.browse_output_button, 8, 4)

        layout.addWidget(QLabel("导出比例"), 9, 0)
        ratio_layout = QHBoxLayout()
        self._add_aspect_ratio_option(ratio_layout, "竖屏 9:16", ExportAspectRatio.VERTICAL_9_16, checked=True)
        self._add_aspect_ratio_option(ratio_layout, "竖屏 3:4", ExportAspectRatio.VERTICAL_3_4)
        self._add_aspect_ratio_option(ratio_layout, "横屏 16:9", ExportAspectRatio.HORIZONTAL_16_9)
        self._add_aspect_ratio_option(ratio_layout, "横屏 4:3", ExportAspectRatio.HORIZONTAL_4_3)
        self._add_aspect_ratio_option(ratio_layout, "方形 1:1", ExportAspectRatio.SQUARE_1_1)
        layout.addLayout(ratio_layout, 9, 1, 1, 4)
        return group

    def _add_aspect_ratio_option(
        self,
        layout: QHBoxLayout,
        label: str,
        aspect_ratio: ExportAspectRatio,
        checked: bool = False,
    ) -> None:
        """Add one aspect ratio radio option to the layout."""

        button = QRadioButton(label)
        button.setChecked(checked)
        self.aspect_ratio_group.addButton(button)
        self.aspect_ratio_buttons[aspect_ratio] = button
        layout.addWidget(button)

    def _build_log_group(self) -> QGroupBox:
        """Create the log output group."""

        group = QGroupBox("导出日志")
        layout = QVBoxLayout(group)
        layout.addWidget(self.log_output)
        return group

    def _connect_signals(self) -> None:
        """Connect UI signals to actions."""

        self.add_button.clicked.connect(self._add_videos)
        self.remove_button.clicked.connect(self._remove_selected_video)
        self.move_up_button.clicked.connect(self._move_selected_up)
        self.move_down_button.clicked.connect(self._move_selected_down)
        self.browse_output_button.clicked.connect(self._choose_output_dir)
        self.start_button.clicked.connect(self._start_batch)

    def _add_videos(self) -> None:
        """Open a file picker and append selected videos to the list."""

        selected_files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "Video Files (*.mp4 *.mov *.mkv *.avi *.mxf *.mts *.m2ts);;All Files (*.*)",
        )
        if not selected_files:
            return

        supported_paths, unsupported_paths = self._split_supported_paths(
            [Path(file_path) for file_path in selected_files]
        )
        if unsupported_paths:
            self._show_unsupported_format_warning(unsupported_paths)
        if not supported_paths:
            return

        for file_path in supported_paths:
            self.video_list.addItem(QListWidgetItem(str(file_path)))

        first_parent = supported_paths[0].parent
        self._app_service.set_recent_video_dir(first_parent)
        self._renumber_video_items()
        self._refresh_generation_stats()
        self.append_log(f"已添加 {len(supported_paths)} 个视频")

    def _remove_selected_video(self) -> None:
        """Remove the currently selected video item."""

        current_row = self.video_list.currentRow()
        if current_row < 0:
            return
        self.video_list.takeItem(current_row)
        self._renumber_video_items()
        self._refresh_generation_stats()

    def _move_selected_up(self) -> None:
        """Move the selected video one row upward."""

        current_row = self.video_list.currentRow()
        if current_row <= 0:
            return
        item = self.video_list.takeItem(current_row)
        self.video_list.insertItem(current_row - 1, item)
        self.video_list.setCurrentRow(current_row - 1)
        self._renumber_video_items()

    def _move_selected_down(self) -> None:
        """Move the selected video one row downward."""

        current_row = self.video_list.currentRow()
        if current_row < 0 or current_row >= self.video_list.count() - 1:
            return
        item = self.video_list.takeItem(current_row)
        self.video_list.insertItem(current_row + 1, item)
        self.video_list.setCurrentRow(current_row + 1)
        self._renumber_video_items()

    def _choose_output_dir(self) -> None:
        """Open a directory picker for the rendered video output path."""

        selected_dir = QFileDialog.getExistingDirectory(self, "选择视频输出目录")
        if selected_dir:
            self.output_dir_edit.setText(selected_dir)
            self._app_service.set_last_output_dir(Path(selected_dir))

    def _start_batch(self) -> None:
        """Collect GUI input and export a Resolve script."""

        try:
            job_input = self._build_job_input()
        except ValueError as exc:
            self._show_error(str(exc))
            return

        self.status_label.setText("导出中")
        self.start_button.setEnabled(False)
        try:
            result = self._app_service.export_batch_script(job_input, log=self.append_log)
        except Exception as exc:
            self.status_label.setText("导出失败")
            self._show_error(str(exc))
        else:
            self.status_label.setText("导出完成")
            self.append_log(
                f"脚本导出完成，共 {result.task_count} 个素材组合任务，"
                f"脚本路径：{result.exported_script.script_path}"
            )
            self.append_log(f"视频输出目录：{job_input.output_dir}")
            self.append_log(f"Lua 运行代码：{result.exported_script.run_command}")
            self.append_log("提示：重复导出会覆盖 generated_scripts 下的同名脚本文件。")
            self.append_log("请在 DaVinci Resolve 中手动运行该 Lua 脚本。")
            QMessageBox.information(
                self,
                "完成",
                "脚本已导出。\n\n"
                f"脚本路径：\n{result.exported_script.script_path}\n\n"
                f"视频输出目录：\n{job_input.output_dir}\n\n"
                f"Lua 运行代码：\n{result.exported_script.run_command}\n\n"
                "注意：重复导出会覆盖同名脚本文件。",
            )
        finally:
            self.start_button.setEnabled(True)

    def _build_job_input(self) -> JobInput:
        """Create a validated job input object from the current UI state."""

        paths = self.get_video_paths()
        if len(paths) < 2:
            raise ValueError("请至少添加 2 个视频文件。")

        output_dir_text = self.output_dir_edit.text().strip()
        if not output_dir_text:
            raise ValueError("请选择视频输出目录。")

        return JobInput(
            videos=self._app_service.build_video_items(paths),
            clips_per_output=self.k_spinbox.value(),
            count=self.count_spinbox.value(),
            aspect_ratio=self._selected_aspect_ratio(),
            output_dir=Path(output_dir_text),
        )

    def _selected_aspect_ratio(self) -> ExportAspectRatio:
        """Return the currently selected aspect ratio option."""

        for aspect_ratio, button in self.aspect_ratio_buttons.items():
            if button.isChecked():
                return aspect_ratio
        return ExportAspectRatio.VERTICAL_9_16

    def _load_saved_paths(self) -> None:
        """Load persisted paths into the GUI on startup."""

        config = self._app_service.get_config()
        if config.last_output_dir:
            self.output_dir_edit.setText(config.last_output_dir)

    def _renumber_video_items(self) -> None:
        """Refresh item labels to show the current base order."""

        for index in range(self.video_list.count()):
            item = self.video_list.item(index)
            raw_path = item.data(0x0100)
            if raw_path is None:
                raw_path = item.text()
            item.setData(0x0100, raw_path)
            item.setText(f"{index + 1}. {raw_path}")

        self._update_button_states()

    def _refresh_generation_stats(self) -> None:
        """Update generation counters and clamp count when needed."""

        video_count = self.video_list.count()
        clips_per_output = self.k_spinbox.value()
        summary = self._app_service.preview_generation(video_count, clips_per_output)

        self.item_count_label.setText(f"N：{summary.item_count}")
        self.group_count_label.setText(f"G：{summary.group_count}")
        self.layer1_label.setText(f"L1：{summary.layer1_count}")
        self.layer2_label.setText(f"L2：{summary.layer2_count}")
        self.layer3_label.setText(f"L3：{summary.layer3_count}")
        self.total_count_label.setText(f"T：{summary.total_count}")
        self.leftover_label.setText(f"忽略素材：{summary.leftover_count}")

        maximum = max(summary.total_count, 1)
        self.count_spinbox.setMaximum(maximum)
        if summary.total_count == 0:
            self.count_spinbox.setValue(1)
        elif self.count_spinbox.value() > summary.total_count:
            self.count_spinbox.setValue(summary.total_count)
            self.append_log(f"请求生成数量已自动调整为 {summary.total_count}。")

    def _sync_count_hint(self) -> None:
        """Keep the status line aligned with the current count selection."""

        self.status_label.setText(f"当前导出任务数量：{self.count_spinbox.value()}")

    def _update_button_states(self) -> None:
        """Enable or disable move/remove buttons based on current selection."""

        current_row = self.video_list.currentRow()
        has_selection = current_row >= 0
        self.remove_button.setEnabled(has_selection)
        self.move_up_button.setEnabled(has_selection and current_row > 0)
        self.move_down_button.setEnabled(has_selection and current_row < self.video_list.count() - 1)

    def append_log(self, message: str) -> None:
        """Append one message to the visible GUI log."""

        self.log_output.appendPlainText(message)

    def get_video_paths(self) -> list[Path]:
        """Return the current ordered list of selected video paths."""

        paths: list[Path] = []
        for index in range(self.video_list.count()):
            item = self.video_list.item(index)
            raw_path = item.data(0x0100)
            if raw_path is None:
                raw_path = item.text()
            normalized = str(raw_path)
            if ". " in normalized:
                _, normalized = normalized.split(". ", 1)
            paths.append(Path(normalized))
        return paths

    def add_video_paths(self, paths: list[Path]) -> None:
        """Helper used by tests to inject ordered video paths."""

        supported_paths, unsupported_paths = self._split_supported_paths(paths)
        if unsupported_paths:
            self.append_log(
                "以下文件格式当前未加入推荐导入范围，已跳过："
                + "，".join(path.name for path in unsupported_paths)
            )
        for path in supported_paths:
            self.video_list.addItem(QListWidgetItem(str(path)))
        self._renumber_video_items()
        self._refresh_generation_stats()

    def _show_error(self, message: str) -> None:
        """Show a user-friendly error dialog and log the same message."""

        self.append_log(f"错误：{message}")
        QMessageBox.critical(self, "错误", message)

    def _split_supported_paths(self, paths: list[Path]) -> tuple[list[Path], list[Path]]:
        """Split selected files into supported and unsupported suffix groups."""

        supported: list[Path] = []
        unsupported: list[Path] = []
        for path in paths:
            if path.suffix.lower() in SUPPORTED_IMPORT_SUFFIXES:
                supported.append(path)
            else:
                unsupported.append(path)
        return supported, unsupported

    def _show_unsupported_format_warning(self, unsupported_paths: list[Path]) -> None:
        """Warn users when selected files are outside the supported import suffix list."""

        names = "，".join(path.name for path in unsupported_paths)
        message = (
            "以下文件格式当前未加入 Windows 免费版 DaVinci Resolve 的推荐导入范围，已跳过：\n"
            f"{names}\n\n"
            "推荐格式：mp4、mov、mkv、avi、mxf、mts、m2ts。"
        )
        self.append_log(f"提示：{message.replace(chr(10), ' ')}")
        QMessageBox.warning(self, "格式提示", message)
