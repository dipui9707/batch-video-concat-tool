"""Tests for the main Qt window."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel
import pytest

from batch_concat.core.models import ExportAspectRatio, GenerationSummary, JobInput
from batch_concat.resolve.script_exporter import ExportedScript
from batch_concat.services.app_service import AppService, BatchExportResult
from batch_concat.ui.main_window import MainWindow


class FakeGuiService(AppService):
    """Minimal service stub used by GUI tests."""

    def __init__(self) -> None:
        super().__init__()
        self.received_job_input: JobInput | None = None

    def preview_generation(self, video_count: int, clips_per_output: int):
        group_count = video_count // clips_per_output if clips_per_output else 0
        usable_count = group_count * clips_per_output
        leftover_count = max(video_count - usable_count, 0)
        layer1_count = group_count
        if group_count < clips_per_output:
            layer2_count = 0
        else:
            layer2_count = clips_per_output * clips_per_output
        if clips_per_output < 3 or group_count < clips_per_output - 1:
            layer3_count = 0
        else:
            from math import comb

            layer3_count = (
                group_count
                * comb(group_count - 1, clips_per_output - 2)
                * comb(clips_per_output, 2)
                * (clips_per_output ** (clips_per_output - 2))
            )

        return GenerationSummary(
            item_count=video_count,
            clips_per_output=clips_per_output,
            group_count=group_count,
            usable_count=usable_count,
            leftover_count=leftover_count,
            layer1_count=layer1_count,
            layer2_count=layer2_count,
            layer3_count=layer3_count,
            total_count=layer1_count + layer2_count + layer3_count,
        )

    def export_batch_script(self, job_input: JobInput, log=None) -> BatchExportResult:
        self.received_job_input = job_input
        if log is not None:
            log("stub export")
        return BatchExportResult(
            validation=self.preview_generation(len(job_input.videos), job_input.clips_per_output),
            task_count=job_input.count,
            exported_script=ExportedScript(
                script_path=Path(r"C:\Users\jxhak\Desktop\cut\generated_scripts\batch_concat_resolve_job.lua"),
                timeline_names=tuple(),
                output_names=tuple(),
                run_command="dofile([[C:/Users/jxhak/Desktop/cut/generated_scripts/batch_concat_resolve_job.lua]])",
            ),
            was_clamped=False,
        )


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_tracks_generation_stats(tmp_path: Path) -> None:
    _get_app()
    window = MainWindow(app_service=FakeGuiService())
    first = tmp_path / "a.mp4"
    second = tmp_path / "b.mp4"
    third = tmp_path / "c.mp4"
    fourth = tmp_path / "d.mp4"

    window.add_video_paths([first, second, third, fourth])

    assert window.item_count_label.text() == "N：4"
    assert window.group_count_label.text() == "G：2"
    assert window.layer1_label.text() == "L1：2"
    assert window.layer2_label.text() == "L2：4"
    assert window.layer3_label.text() == "L3：0"
    assert window.total_count_label.text() == "T：6"


def test_main_window_defaults_to_k2_and_vertical_ratio() -> None:
    _get_app()
    window = MainWindow(app_service=FakeGuiService())

    assert window.k_spinbox.value() == 2
    assert window._selected_aspect_ratio() is ExportAspectRatio.VERTICAL_9_16
    assert "G=floor(N/K)" in window.formula_label.text()
    assert "T=L1+L2+L3" in window.formula_hint_label.text()
    assert "L1=组内直出" in window.layer_logic_hint_label.text()
    assert window.video_list.parentWidget().findChildren(QLabel)[0].text().startswith("推荐导入格式：")
    assert "重复导出会覆盖上一份脚本" in window.script_overwrite_hint_label.text()


def test_main_window_clamps_requested_count_to_total(tmp_path: Path) -> None:
    _get_app()
    window = MainWindow(app_service=FakeGuiService())
    for name in ("a.mp4", "b.mp4", "c.mp4", "d.mp4"):
        (tmp_path / name).write_bytes(b"x")

    window.add_video_paths(
        [
            tmp_path / "a.mp4",
            tmp_path / "b.mp4",
            tmp_path / "c.mp4",
            tmp_path / "d.mp4",
        ]
    )
    window.count_spinbox.setValue(6)
    window.k_spinbox.setValue(4)

    assert window.count_spinbox.maximum() == 1
    assert window.count_spinbox.value() == 1


def test_main_window_builds_job_input_from_form(tmp_path: Path) -> None:
    _get_app()
    service = FakeGuiService()
    window = MainWindow(app_service=service)
    first = tmp_path / "a.mp4"
    second = tmp_path / "b.mp4"
    window.add_video_paths([first, second])
    window.output_dir_edit.setText(str(tmp_path))
    window.k_spinbox.setValue(2)
    window.count_spinbox.setValue(1)

    job_input = window._build_job_input()

    assert job_input.clips_per_output == 2
    assert job_input.aspect_ratio is ExportAspectRatio.VERTICAL_9_16
    assert job_input.output_dir == tmp_path


def test_main_window_skips_unsupported_suffix_when_adding_paths(tmp_path: Path) -> None:
    _get_app()
    window = MainWindow(app_service=FakeGuiService())
    supported = tmp_path / "a.mp4"
    unsupported = tmp_path / "note.txt"

    window.add_video_paths([supported, unsupported])

    assert window.video_list.count() == 1
    assert "note.txt" in window.log_output.toPlainText()


def test_main_window_start_batch_passes_job_input_to_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _get_app()
    service = FakeGuiService()
    window = MainWindow(app_service=service)
    first = tmp_path / "a.mp4"
    second = tmp_path / "b.mp4"
    window.add_video_paths([first, second])
    window.output_dir_edit.setText(str(tmp_path))
    window.k_spinbox.setValue(2)
    window.count_spinbox.setValue(1)

    monkeypatch.setattr("batch_concat.ui.main_window.QMessageBox.information", lambda *args, **kwargs: None)
    window._start_batch()

    assert service.received_job_input is not None
    assert service.received_job_input.clips_per_output == 2
    assert "Lua 运行代码：" in window.log_output.toPlainText()
    assert "重复导出会覆盖 generated_scripts 下的同名脚本文件" in window.log_output.toPlainText()


def test_main_window_warns_for_unsupported_suffixes_in_picker_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _get_app()
    window = MainWindow(app_service=FakeGuiService())
    supported = tmp_path / "a.mp4"
    unsupported = tmp_path / "note.txt"

    monkeypatch.setattr(
        "batch_concat.ui.main_window.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(supported), str(unsupported)], ""),
    )
    captured: list[str] = []
    monkeypatch.setattr(
        "batch_concat.ui.main_window.QMessageBox.warning",
        lambda *args, **kwargs: captured.append(args[2]),
    )

    window._add_videos()

    assert window.video_list.count() == 1
    assert captured
    assert "note.txt" in captured[0]
