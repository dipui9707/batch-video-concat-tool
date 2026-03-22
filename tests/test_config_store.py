"""Tests for JSON-backed app configuration."""

from __future__ import annotations

from pathlib import Path

from batch_concat.core.config_store import AppConfig, ConfigStore


def test_load_returns_default_when_file_missing(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")

    config = store.load()

    assert config == AppConfig()


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    expected = AppConfig(
        last_output_dir=r"C:\output",
        recent_video_dir=r"C:\video",
    )

    store.save(expected)

    assert store.load() == expected
