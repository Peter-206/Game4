"""Validated, user-local settings for Pizza Box Party."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path


DISPLAY_MODES = ("borderless", "windowed", "fullscreen")
GUI_SCALES = tuple(round(value / 100, 2) for value in range(80, 121, 5))


@dataclass
class AppSettings:
    display_mode: str = "borderless"
    display_index: int = 0
    resolution: tuple[int, int] | None = None
    gui_scale: float = 1.0
    game_volume: float = 0.8
    muted: bool = False

    @classmethod
    def from_mapping(cls, data) -> "AppSettings":
        if not isinstance(data, dict):
            return cls()
        mode = data.get("display_mode", "borderless")
        if mode not in DISPLAY_MODES:
            mode = "borderless"
        index = data.get("display_index", 0)
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            index = 0
        resolution = data.get("resolution")
        if (not isinstance(resolution, (list, tuple)) or len(resolution) != 2
                or any(not isinstance(v, int) or isinstance(v, bool) or v < 640
                       for v in resolution)):
            resolution = None
        else:
            resolution = tuple(resolution)
        gui_scale = data.get("gui_scale", 1.0)
        if not isinstance(gui_scale, (int, float)) or isinstance(gui_scale, bool):
            gui_scale = 1.0
        gui_scale = min(GUI_SCALES, key=lambda value: abs(value - gui_scale))
        volume = data.get("game_volume", 0.8)
        if not isinstance(volume, (int, float)) or isinstance(volume, bool):
            volume = 0.8
        volume = max(0.0, min(1.0, round(float(volume), 2)))
        muted = data.get("muted", False)
        if not isinstance(muted, bool):
            muted = False
        return cls(mode, index, resolution, gui_scale, volume, muted)


def default_settings_path() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if root:
        return Path(root) / "PizzaBoxParty" / "settings.json"
    return Path.home() / ".config" / "pizza_box_party" / "settings.json"


def load_settings(path: Path | None = None) -> AppSettings:
    path = Path(path) if path is not None else default_settings_path()
    try:
        return AppSettings.from_mapping(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return AppSettings()


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    path = Path(path) if path is not None else default_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = asdict(AppSettings.from_mapping(asdict(settings)))
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
