"""JSON-backed local configuration storage."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Persisted user preferences for the desktop app."""

    last_output_dir: str = ""
    recent_video_dir: str = ""


class ConfigStore:
    """Read and write the app config from a local JSON file."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or self.default_config_path()

    @staticmethod
    def default_config_path() -> Path:
        """Return the default per-user config file path."""

        appdata = Path.home() / "AppData" / "Roaming"
        return appdata / "BatchConcatTool" / "config.json"

    def load(self) -> AppConfig:
        """Load config from disk, returning defaults when absent or invalid."""

        if not self._config_path.exists():
            return AppConfig()

        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AppConfig()

        return AppConfig(
            last_output_dir=str(data.get("last_output_dir", "")),
            recent_video_dir=str(data.get("recent_video_dir", "")),
        )

    def save(self, config: AppConfig) -> None:
        """Persist config to disk."""

        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_output_dir": config.last_output_dir,
            "recent_video_dir": config.recent_video_dir,
        }
        self._config_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
