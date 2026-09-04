"""Pure layout calculations shared by display code and tests."""

from __future__ import annotations

from dataclasses import dataclass


DESIGN_WIDTH = 1280
DESIGN_HEIGHT = 800
@dataclass(frozen=True)
class DisplayLayout:
    """Map the game's design coordinates onto the complete native viewport.

    Positions and rectangular regions reflow independently on each axis.  Sizes
    that must remain round (fonts, line widths, tokens, and circles) use
    ``uniform_scale`` so they are never distorted.
    """

    window_width: int
    window_height: int
    viewport_x: int
    viewport_y: int
    viewport_width: int
    viewport_height: int
    scale_x: float
    scale_y: float
    uniform_scale: float
    gui_scale: float

    @classmethod
    def from_window(cls, width: int, height: int, gui_scale: float = 1.0) -> "DisplayLayout":
        width = max(1, int(width))
        height = max(1, int(height))
        gui_scale = max(0.8, min(1.2, float(gui_scale)))
        viewport_width = width
        viewport_height = height
        viewport_x = 0
        viewport_y = 0
        scale_x = viewport_width / DESIGN_WIDTH
        scale_y = viewport_height / DESIGN_HEIGHT
        return cls(
            window_width=width,
            window_height=height,
            viewport_x=viewport_x,
            viewport_y=viewport_y,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            scale_x=scale_x,
            scale_y=scale_y,
            uniform_scale=min(scale_x, scale_y) * gui_scale,
            gui_scale=gui_scale,
        )

    @property
    def viewport(self) -> tuple[int, int, int, int]:
        return self.viewport_x, self.viewport_y, self.viewport_width, self.viewport_height

    def point(self, point: tuple[float, float]) -> tuple[int, int]:
        return round(point[0] * self.scale_x), round(point[1] * self.scale_y)

    def rect(self, rect: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
        x, y, width, height = rect
        return (
            round(x * self.scale_x),
            round(y * self.scale_y),
            max(1, round(width * self.scale_x)),
            max(1, round(height * self.scale_y)),
        )

    def size(self, value: float, *, minimum: int = 1) -> int:
        return max(minimum, round(value * self.uniform_scale))

    def window_to_design(self, point: tuple[int, int]) -> tuple[int, int] | None:
        x, y = point
        if not (
            self.viewport_x <= x < self.viewport_x + self.viewport_width
            and self.viewport_y <= y < self.viewport_y + self.viewport_height
        ):
            return None
        logical_x = int((x - self.viewport_x) / self.scale_x)
        logical_y = int((y - self.viewport_y) / self.scale_y)
        return (
            max(0, min(DESIGN_WIDTH - 1, logical_x)),
            max(0, min(DESIGN_HEIGHT - 1, logical_y)),
        )


def sidebar_row_height(player_count: int, available_height: int) -> int:
    if player_count < 1:
        return available_height
    return max(24, min(58, available_height // player_count))


def sidebar_rows_fit(player_count: int, available_height: int) -> bool:
    return sidebar_row_height(player_count, available_height) * player_count <= available_height
