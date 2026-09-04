"""Display-independent world layout and horizontal camera helpers."""

from __future__ import annotations

import random
from dataclasses import dataclass


WORLD_MARGIN = 110
SPACE_GAP = 155
WORLD_HEIGHT = 800
Y_POSITIONS = (570, 470, 305, 175, 245, 420, 610, 505, 325, 155, 225, 405)


def make_world_positions(count: int = 36, rng=None) -> list[tuple[int, int]]:
    """Return a randomized, monotonically left-to-right winding path.

    Each vertical coordinate averages one to five distinct safe candidates.
    Larger samples pull spaces toward the middle of the board, making sharp
    vertical changes possible but less common.
    """
    if count < 1:
        return []
    random_source = rng if rng is not None else random
    positions = []
    for index in range(count):
        sample_count = random_source.randint(1, 5)
        candidates = random_source.sample(Y_POSITIONS, sample_count)
        y = round(sum(candidates) / len(candidates))
        positions.append((WORLD_MARGIN + index * SPACE_GAP, y))
    return positions


def world_width(positions: list[tuple[int, int]], margin: int = WORLD_MARGIN) -> int:
    return (positions[-1][0] + margin) if positions else margin * 2


@dataclass
class HorizontalCamera:
    viewport_width: int
    world_width: int
    position: float = 0.0
    target: float = 0.0
    speed: float = 900.0
    settled: bool = True

    @property
    def maximum(self) -> float:
        return float(max(0, self.world_width - self.viewport_width))

    def clamp(self, value: float) -> float:
        return max(0.0, min(self.maximum, float(value)))

    def focus(self, world_x: float) -> None:
        self.target = self.clamp(world_x - self.viewport_width / 2)
        self.settled = abs(self.target - self.position) < 0.5
        if self.settled:
            self.position = self.target

    def snap(self, world_x: float) -> None:
        self.focus(world_x)
        self.position = self.target
        self.settled = True

    def update(self, elapsed_seconds: float, *, paused: bool = False) -> bool:
        if paused or self.settled:
            return self.settled
        distance = self.target - self.position
        step = max(0.0, elapsed_seconds) * self.speed
        if abs(distance) <= max(0.5, step):
            self.position = self.target
            self.settled = True
        else:
            self.position += step if distance > 0 else -step
        return self.settled

    def world_to_screen(self, point: tuple[float, float]) -> tuple[int, int]:
        return round(point[0] - self.position), round(point[1])

    def visible_x(self, world_x: float, padding: float = 0.0) -> bool:
        return self.position - padding <= world_x <= self.position + self.viewport_width + padding
