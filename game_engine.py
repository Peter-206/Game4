"""Authoritative, display-independent rules for Pizza Box Party."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(eq=False)
class PlayerState:
    """Mutable player state; ``token_image`` remains opaque to the engine."""

    name: str
    token_name: str
    token_image: Any = None
    position: int = 0
    shots: int = 0
    sips: int = 0
    finished: bool = False
    skip_turns: int = 0
    whirlpool_position: int | None = None
    is_beer_bitch: bool = False
    distance_traveled: int = 0
    backward_steps: int = 0
    events_landed: int = 0
    turns_taken: int = 0
    total_skips: int = 0

    def reset(self) -> None:
        self.position = 0
        self.shots = 0
        self.sips = 0
        self.finished = False
        self.skip_turns = 0
        self.whirlpool_position = None
        self.is_beer_bitch = False
        self.distance_traveled = 0
        self.backward_steps = 0
        self.events_landed = 0
        self.turns_taken = 0
        self.total_skips = 0


@dataclass
class RulesEngine:
    """Game mutations that must remain authoritative across all front ends."""

    players: list[PlayerState] = field(default_factory=list)
    finish_index: int = 35
    mates: dict[PlayerState, PlayerState] = field(default_factory=dict)

    def reset(self) -> None:
        self.mates.clear()
        for player in self.players:
            player.reset()

    def movement_steps(self, player: PlayerState, distance: int) -> list[int]:
        if distance < 0:
            raise ValueError("distance must be non-negative")
        final = min(player.position + distance, self.finish_index)
        return list(range(player.position + 1, final + 1))

    def movement_to(self, player: PlayerState, target: int) -> list[int]:
        """Return each clamped hop to an absolute forced-movement target."""
        destination = max(0, min(self.finish_index, target))
        if destination == player.position:
            return []
        direction = 1 if destination > player.position else -1
        return list(range(player.position + direction, destination + direction, direction))

    def move_relative(self, player: PlayerState, distance: int) -> int:
        if distance > 0:
            player.distance_traveled += distance
        elif distance < 0:
            player.backward_steps += abs(distance)
        player.position = max(0, min(self.finish_index, player.position + distance))
        if player.position == self.finish_index:
            player.finished = True
        return player.position

    def add_skipped_turns(self, player: PlayerState, count: int = 1) -> None:
        if count < 0:
            raise ValueError("skip count must be non-negative")
        player.skip_turns += count
        player.total_skips += count

    def advance_turn(self, current_index: int) -> tuple[int, list[PlayerState]]:
        """Select the next eligible player and consume skipped turns.

        Returns the selected index plus every player automatically skipped on
        the way. If all players owe a skipped turn, one is consumed from each
        before normal rotation resumes.
        """
        if not self.players:
            raise ValueError("cannot advance an empty game")
        if not 0 <= current_index < len(self.players):
            raise IndexError("current player index is out of range")

        next_index = current_index
        skipped: list[PlayerState] = []
        while True:
            next_index = (next_index + 1) % len(self.players)
            player = self.players[next_index]
            if player.skip_turns == 0:
                return next_index, skipped
            player.skip_turns -= 1
            skipped.append(player)

    def give_sips(self, player: PlayerState, count: int, *, group: bool = False) -> None:
        if count < 0:
            raise ValueError("sip count must be non-negative")
        player.sips += count
        if not group and (mate := self.mates.get(player)) is not None:
            mate.sips += count

    def give_shots(self, player: PlayerState, count: int = 1, *, group: bool = False) -> None:
        if count < 0:
            raise ValueError("shot count must be non-negative")
        player.shots += count
        if not group and (mate := self.mates.get(player)) is not None:
            mate.shots += count

    def give_group_sips(self, count: int = 1) -> None:
        for player in self.players:
            self.give_sips(player, count, group=True)

    def give_group_shots(self, count: int = 1) -> None:
        for player in self.players:
            self.give_shots(player, count, group=True)

    def pair_mates(self, first: PlayerState, second: PlayerState) -> None:
        if first is second:
            raise ValueError("a player cannot be their own mate")
        if first not in self.players or second not in self.players:
            raise ValueError("both mates must belong to this game")
        self.unpair(first)
        self.unpair(second)
        self.mates[first] = second
        self.mates[second] = first

    def unpair(self, player: PlayerState) -> None:
        mate = self.mates.pop(player, None)
        if mate is not None:
            self.mates.pop(mate, None)

    def remove_player(self, player: PlayerState, current_index: int) -> int:
        """Remove a player and preserve the identity of the current turn.

        If the current player is removed, the player immediately after them
        becomes current (wrapping at the end). Mate links are always repaired.
        """
        if player not in self.players:
            raise ValueError("player does not belong to this game")
        if not 0 <= current_index < len(self.players):
            raise IndexError("current player index is out of range")
        if len(self.players) == 1:
            raise ValueError("cannot remove the last player")

        removed_index = self.players.index(player)
        current_player = self.players[current_index]
        self.unpair(player)
        self.players.remove(player)

        if player is current_player:
            return removed_index % len(self.players)
        return self.players.index(current_player)
