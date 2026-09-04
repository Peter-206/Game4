"""Board-creator draft model and safe JSON persistence."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import tempfile
from typing import Mapping


MIN_CREATOR_SPACES = 5


@dataclass(frozen=True)
class EventOption:
    key: str
    label: str
    type: str | None = None
    effect: str | None = None
    value_field: bool = False
    target_field: bool = False
    message_field: bool = False
    component: str | None = None


CORE_EVENT_OPTIONS = (
    EventOption("normal", "Normal / No Effect", "normal", "none"),
    EventOption("sip", "Sip", "sip", "sip", value_field=True),
    EventOption("shot", "Shot", "shot", "shot"),
    EventOption("everyone_sip", "Everyone Sips", "everyone_sip", "everyone_sip"),
    EventOption("forward", "Move Forward", "forward", "forward", value_field=True),
    EventOption("back", "Move Back", "back", "back", value_field=True),
    EventOption("skip", "Skip Turns", "event", "skip", value_field=True),
    EventOption("ladder", "Ladder / Jump", "event", "ladder", target_field=True),
    EventOption("custom", "Custom Message", "event", "custom", message_field=True),
)


class BoardCreatorError(ValueError):
    """Raised when a board draft cannot be saved."""


def available_event_options(components: Mapping[str, Mapping]) -> list[EventOption]:
    """Return built-in choices followed by every registered party component."""
    options = list(CORE_EVENT_OPTIONS)
    for key, component in components.items():
        label = str(component.get("label") or key.replace("_", " ").title())
        options.append(EventOption(f"component:{key}", label, component=key))
    return options


def event_key_for_space(space: Mapping) -> str:
    component = space.get("component")
    if component:
        return f"component:{component}"
    effect = space.get("effect", "none")
    return "normal" if effect in ("none", "start", "finish") else str(effect)


class BoardDraft:
    """Mutable, UI-independent representation of a new board."""

    def __init__(self, name: str, description: str, spaces: list[dict]):
        self.name = name
        self.description = description
        self.spaces = spaces
        self.dirty = False
        self._renumber()

    @classmethod
    def create_default(cls, count: int = MIN_CREATOR_SPACES) -> "BoardDraft":
        if count < MIN_CREATOR_SPACES:
            raise BoardCreatorError(f"board creator requires at least {MIN_CREATOR_SPACES} spaces")
        spaces = [{"id": 0, "label": "Start", "type": "start", "effect": "none"}]
        spaces.extend(
            {"id": index, "label": f"Space {index}", "type": "normal", "effect": "none"}
            for index in range(1, count - 1)
        )
        spaces.append({"id": count - 1, "label": "Finish", "type": "finish", "effect": "finish"})
        return cls("", "", spaces)

    def _renumber(self) -> None:
        for index, space in enumerate(self.spaces):
            space["id"] = index

    def set_metadata(self, field: str, value: str) -> None:
        if field not in ("name", "description"):
            raise KeyError(field)
        if getattr(self, field) != value:
            setattr(self, field, value)
            self.dirty = True

    def set_space_field(self, index: int, field: str, value) -> None:
        if not 0 <= index < len(self.spaces):
            raise IndexError(index)
        if field not in ("label", "value", "target", "msg"):
            raise KeyError(field)
        if self.spaces[index].get(field) != value:
            self.spaces[index][field] = value
            self.dirty = True

    def add_space(self) -> int:
        finish_index = len(self.spaces) - 1
        self.spaces.insert(finish_index, {
            "id": finish_index,
            "label": f"Space {finish_index}",
            "type": "normal",
            "effect": "none",
        })
        self._renumber()
        self.dirty = True
        return finish_index

    def remove_space(self, index: int) -> int:
        if len(self.spaces) <= MIN_CREATOR_SPACES:
            raise BoardCreatorError(f"boards created here need at least {MIN_CREATOR_SPACES} spaces")
        if index <= 0 or index >= len(self.spaces) - 1:
            raise BoardCreatorError("Start and Finish cannot be removed")
        self.spaces.pop(index)
        self._renumber()
        self.dirty = True
        return min(index, len(self.spaces) - 2)

    def set_event(self, index: int, option_key: str,
                  components: Mapping[str, Mapping]) -> None:
        if index <= 0 or index >= len(self.spaces) - 1:
            raise BoardCreatorError("Start and Finish event types are locked")
        options = {option.key: option for option in available_event_options(components)}
        option = options.get(option_key)
        if option is None:
            raise BoardCreatorError(f"unknown event option: {option_key}")

        current_label = str(self.spaces[index].get("label", f"Space {index}"))
        if option.component:
            default_label = str(components[option.component].get("label") or option.label)
            replacement = {"id": index, "label": default_label, "component": option.component}
        else:
            replacement = {
                "id": index,
                "label": current_label,
                "type": option.type,
                "effect": option.effect,
            }
            if option.value_field:
                replacement["value"] = 1
            if option.target_field:
                replacement["target"] = min(index + 1, len(self.spaces) - 1)
            if option.message_field:
                replacement["msg"] = "{name} landed on {label}."
        self.spaces[index] = replacement
        self.dirty = True

    def to_json_data(self) -> dict:
        return {
            "name": self.name.strip(),
            "description": self.description.strip(),
            "spaces": [dict(space) for space in self.spaces],
        }

    def validate(self, validate_board_data) -> dict:
        data = self.to_json_data()
        if not data["name"]:
            raise BoardCreatorError("Board name is required.")
        for space in data["spaces"][1:-1]:
            if not str(space.get("label", "")).strip():
                raise BoardCreatorError(f"Space {space['id']} needs a label.")
            effect = space.get("effect")
            if effect in ("sip", "forward", "back", "skip"):
                value = space.get("value")
                if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                    raise BoardCreatorError(f"Space {space['id']} needs a positive number.")
            if effect == "ladder":
                target = space.get("target")
                if not isinstance(target, int) or isinstance(target, bool) or not 0 <= target < len(self.spaces):
                    raise BoardCreatorError(f"Space {space['id']} needs a valid target.")
            if effect == "custom" and not str(space.get("msg", "")).strip():
                raise BoardCreatorError(f"Space {space['id']} needs a custom message.")
        try:
            validate_board_data(data, "board creator")
        except ValueError as exc:
            raise BoardCreatorError(str(exc)) from exc
        return data


def _safe_stem(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9 _-]+", "", name).strip().replace(" ", "_")
    stem = re.sub(r"_+", "_", stem).strip("._-")
    return stem or "board"


def save_new_board(draft: BoardDraft, boards_dir: str, validate_board_data) -> str:
    """Validate and atomically save a draft without overwriting another board."""
    data = draft.validate(validate_board_data)
    os.makedirs(boards_dir, exist_ok=True)
    stem = _safe_stem(data["name"])
    path = os.path.join(boards_dir, f"{stem}.json")
    suffix = 2
    while os.path.exists(path):
        path = os.path.join(boards_dir, f"{stem}_{suffix}.json")
        suffix += 1

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=boards_dir, prefix=f".{stem}_",
            suffix=".tmp", delete=False,
        ) as file:
            temporary_path = file.name
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, path)
    except OSError as exc:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
        raise BoardCreatorError(f"Could not save board: {exc}") from exc
    draft.dirty = False
    return path
