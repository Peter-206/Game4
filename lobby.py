"""Thread-safe authoritative LAN lobby state."""

from __future__ import annotations

import secrets
import threading
from dataclasses import asdict, dataclass


class LobbyError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class LobbyPlayer:
    player_id: str
    session_token: str
    name: str
    token_name: str
    connected: bool = True

    def public(self) -> dict:
        state = asdict(self)
        state.pop("session_token")
        return state


class HostLobby:
    def __init__(self, token_names: list[str], max_players: int = 15):
        if not token_names:
            raise ValueError("at least one token is required")
        self.token_names = tuple(token_names)
        self.max_players = max_players
        self.players: list[LobbyPlayer] = []
        self.started = False
        self._lock = threading.RLock()

    def join(self, name: object, token_name: object) -> LobbyPlayer:
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 24:
            raise LobbyError("invalid_name", "Name must contain 1 to 24 characters.")
        if token_name not in self.token_names:
            raise LobbyError("invalid_token", "Choose one of the available tokens.")
        with self._lock:
            if self.started:
                raise LobbyError("game_started", "This game has already started.")
            if len(self.players) >= self.max_players:
                raise LobbyError("lobby_full", "The lobby is full.")
            claimed = {player.token_name for player in self.players}
            unclaimed = set(self.token_names) - claimed
            if token_name in claimed and unclaimed:
                raise LobbyError("token_claimed", "That token was claimed; choose another.")
            player = LobbyPlayer(
                player_id=secrets.token_urlsafe(12),
                session_token=secrets.token_urlsafe(32),
                name=name.strip(),
                token_name=str(token_name),
            )
            self.players.append(player)
            return player

    def reconnect(self, session_token: object) -> LobbyPlayer:
        if not isinstance(session_token, str):
            raise LobbyError("invalid_session", "The saved player session is invalid.")
        with self._lock:
            for player in self.players:
                if secrets.compare_digest(player.session_token, session_token):
                    player.connected = True
                    return player
        raise LobbyError("invalid_session", "The saved player session has expired.")

    def disconnect(self, player_id: str) -> None:
        with self._lock:
            for player in self.players:
                if player.player_id == player_id:
                    player.connected = False
                    return

    def remove(self, player_id: str, *, during_game: bool = False) -> LobbyPlayer:
        with self._lock:
            if self.started and not during_game:
                raise LobbyError("game_started", "Players cannot be removed here after start.")
            for index, player in enumerate(self.players):
                if player.player_id == player_id:
                    return self.players.pop(index)
        raise LobbyError("unknown_player", "Player was not found.")

    def return_to_lobby(self) -> None:
        """Re-open setup while preserving joined phone sessions and order."""
        with self._lock:
            self.started = False

    def start(self) -> None:
        with self._lock:
            if len(self.players) < 2:
                raise LobbyError("not_enough_players", "At least two players must join.")
            self.started = True

    def public_state(self) -> dict:
        with self._lock:
            return {
                "type": "room_state",
                "started": self.started,
                "can_start": len(self.players) >= 2 and not self.started,
                "players": [player.public() for player in self.players],
                "available_tokens": list(self.token_names),
            }
