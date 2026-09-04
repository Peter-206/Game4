"""Validation and idempotency helpers for the LAN game protocol."""

from __future__ import annotations

from dataclasses import dataclass, field


MESSAGE_TYPES = frozenset({
    "join", "reconnect", "roll", "event_response", "leave",
    "room_state", "turn_state", "roll_result", "event_prompt",
    "event_resolved", "drink_state", "pause", "game_end",
    "hot_seat_state",
})
CLIENT_MESSAGE_TYPES = frozenset({"join", "reconnect", "roll", "event_response", "leave"})


class ProtocolError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _nonempty_text(value: object, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ProtocolError("invalid_message", f"{field_name} must contain 1 to {maximum} characters.")
    return value.strip()


def _identity(value: object, field_name: str) -> str:
    return _nonempty_text(value, field_name, 256)


def _positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ProtocolError("invalid_message", f"{field_name} must be a positive integer.")
    return value


def validate_client_message(payload: object) -> dict:
    """Return a normalized controller message or raise a safe protocol error."""
    if not isinstance(payload, dict) or payload.get("type") not in CLIENT_MESSAGE_TYPES:
        raise ProtocolError("invalid_message", "Unsupported controller message.")
    kind = payload["type"]
    normalized = {"type": kind}
    if kind == "join":
        normalized["name"] = _nonempty_text(payload.get("name"), "name", 24)
        normalized["token_name"] = _nonempty_text(payload.get("token_name"), "token_name", 64)
    elif kind == "reconnect":
        normalized["session_token"] = _identity(payload.get("session_token"), "session_token")
    elif kind == "roll":
        normalized["turn_id"] = _positive_int(payload.get("turn_id"), "turn_id")
    elif kind == "event_response":
        normalized["turn_id"] = _positive_int(payload.get("turn_id"), "turn_id")
        normalized["prompt_id"] = _identity(payload.get("prompt_id"), "prompt_id")
        response = payload.get("response")
        if not isinstance(response, (str, int, float, bool)) or len(str(response)) > 500:
            raise ProtocolError("invalid_message", "response must be a scalar no longer than 500 characters.")
        normalized["response"] = response
    return normalized


@dataclass
class TurnActionGuard:
    """Tracks accepted action identities so retries cannot mutate state twice."""

    accepted_rolls: set[int] = field(default_factory=set)
    accepted_prompts: set[tuple[int, str]] = field(default_factory=set)

    def accept_roll(self, *, player_id: str | None, active_player_id: str | None,
                    submitted_turn: object, current_turn: int, can_roll: bool) -> bool:
        if (not can_roll or not player_id or player_id != active_player_id
                or submitted_turn != current_turn or current_turn in self.accepted_rolls):
            return False
        self.accepted_rolls.add(current_turn)
        return True

    def accept_prompt(self, *, player_id: str | None, owner_id: str | None,
                      submitted_turn: object, current_turn: int,
                      prompt_id: object, current_prompt_id: str | None) -> bool:
        key = (current_turn, str(prompt_id))
        if (not player_id or player_id != owner_id or submitted_turn != current_turn
                or prompt_id != current_prompt_id or key in self.accepted_prompts):
            return False
        self.accepted_prompts.add(key)
        return True

    def reset(self) -> None:
        self.accepted_rolls.clear()
        self.accepted_prompts.clear()
