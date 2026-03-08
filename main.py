"""
main.py — Pizza Box Party! entry point and game loop.
Run with:  python main.py
"""

import pygame
import sys
import random
import math
import os

from game_data import *
from game_data import get_token_offsets, list_boards, load_board
from models import Player

# ---------------------------------------------------------------------------
# Token image generation — creates PNG files in assets/tokens/default/
# ---------------------------------------------------------------------------

def _gen_pizza(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    h = size
    pts  = [(h // 2, 4),      (4, h - 6),  (h - 4, h - 6)]
    pts2 = [(h // 2, 12),     (9, h - 10), (h - 9, h - 10)]
    pts3 = [(h // 2, 18),     (14, h - 16),(h - 14, h - 16)]
    pygame.draw.polygon(s, (255, 195, 40), pts)
    pygame.draw.polygon(s, (215, 70,  45), pts2)
    pygame.draw.polygon(s, (255, 225, 85), pts3)
    pygame.draw.line(s, (165, 115, 25), (4, h - 6), (h - 4, h - 6), 8)
    pygame.draw.polygon(s, (140, 80, 18), pts, 3)
    for px, py in [(h//2, h//2+4), (h//2-8, h-18), (h//2+8, h-18)]:
        pygame.draw.circle(s, (185, 38, 38), (px, py), 5)
        pygame.draw.circle(s, (210, 62, 62), (px, py), 3)
    return s


def _gen_beer(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    body = pygame.Rect(8, 20, 40, 38)
    pygame.draw.rect(s, (225, 175, 28), body, border_radius=4)
    pygame.draw.rect(s, (168, 122, 18), body, 3, border_radius=4)
    pygame.draw.arc(s, (168, 122, 18), (44, 26, 16, 22), -1.2, 1.2, 5)
    foam_pts = [(8, 24), (12, 13), (20, 20), (28, 11), (36, 18), (44, 13), (48, 24)]
    pygame.draw.polygon(s, (252, 252, 252), foam_pts)
    pygame.draw.lines(s, (210, 210, 210), False, foam_pts, 2)
    pygame.draw.circle(s, (232, 188, 48), (20, 38), 3)
    pygame.draw.circle(s, (232, 188, 48), (32, 46), 3)
    return s


def _gen_dice(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(s, (252, 252, 252), (4, 4, 56, 56), border_radius=10)
    pygame.draw.rect(s, (28, 28, 28), (4, 4, 56, 56), 3, border_radius=10)
    for px, py in [(18, 18), (46, 18), (32, 32), (18, 46), (46, 46)]:
        pygame.draw.circle(s, (18, 18, 18), (px, py), 6)
    return s


def _gen_cup(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pts = [(14, 6), (50, 6), (54, 58), (10, 58)]
    pygame.draw.polygon(s, (198, 38, 38), pts)
    pygame.draw.polygon(s, (148, 18, 18), pts, 3)
    pygame.draw.rect(s, (228, 228, 228), (11, 4, 42, 7), border_radius=2)
    for y in [20, 32, 44]:
        t = (y - 6) / 52
        xl = max(12, int(14 + t * (54 - 14) - 2))
        xr = min(52, int(50 - t * (50 - 10) + 2))
        pygame.draw.line(s, (215, 68, 68), (xl, y), (xr, y), 2)
    return s


def _gen_star(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    outer_r, inner_r = 29, 12
    pts = []
    for i in range(10):
        angle = math.pi / 5 * i - math.pi / 2
        r = outer_r if i % 2 == 0 else inner_r
        pts.append((int(cx + r * math.cos(angle)), int(cy + r * math.sin(angle))))
    pygame.draw.polygon(s, (255, 215, 0), pts)
    pygame.draw.polygon(s, (198, 152, 0), pts, 3)
    pygame.draw.circle(s, (255, 242, 120), (cx, cy), 8)
    return s


def _gen_nerf(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    # Orange body
    pygame.draw.rect(s, (255, 115, 28), (22, 18, 20, 34), border_radius=5)
    pygame.draw.rect(s, (200, 78, 10), (22, 18, 20, 34), 2, border_radius=5)
    # Yellow suction tip
    pygame.draw.ellipse(s, (255, 218, 18), (18, 10, 28, 16))
    pygame.draw.ellipse(s, (200, 165, 10), (18, 10, 28, 16), 2)
    pygame.draw.ellipse(s, (200, 165, 10), (22, 12, 20, 10), 2)  # inner ring
    # Orange stripe band
    pygame.draw.rect(s, (200, 78, 10), (22, 36, 20, 4))
    # Blue tail fins
    pygame.draw.polygon(s, (42, 95, 218), [(22, 48), (8, 60), (22, 56)])
    pygame.draw.polygon(s, (42, 95, 218), [(42, 48), (56, 60), (42, 56)])
    pygame.draw.polygon(s, (25, 65, 185), [(22, 48), (8, 60), (22, 56)], 1)
    pygame.draw.polygon(s, (25, 65, 185), [(42, 48), (56, 60), (42, 56)], 1)
    return s


def _gen_lion(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2 + 3
    # Mane spikes
    for i in range(10):
        ang = math.pi * 2 * i / 10
        x1 = int(cx + 22 * math.cos(ang))
        y1 = int(cy + 22 * math.sin(ang))
        x2 = int(cx + 30 * math.cos(ang))
        y2 = int(cy + 30 * math.sin(ang))
        pygame.draw.line(s, (185, 95, 8), (x1, y1), (x2, y2), 5)
    # Mane circle
    pygame.draw.circle(s, (215, 128, 18), (cx, cy), 22)
    pygame.draw.circle(s, (168, 92, 8), (cx, cy), 22, 2)
    # Face
    pygame.draw.circle(s, (255, 212, 58), (cx, cy), 17)
    pygame.draw.circle(s, (198, 158, 25), (cx, cy), 17, 2)
    # Ears
    for ex in [cx - 15, cx + 15]:
        pygame.draw.circle(s, (255, 212, 58), (ex, cy - 17), 6)
        pygame.draw.circle(s, (198, 158, 25), (ex, cy - 17), 6, 2)
        pygame.draw.circle(s, (228, 155, 128), (ex, cy - 17), 3)
    # Eyes
    pygame.draw.circle(s, (55, 35, 8), (cx - 6, cy - 4), 4)
    pygame.draw.circle(s, (55, 35, 8), (cx + 6, cy - 4), 4)
    pygame.draw.circle(s, (255, 255, 255), (cx - 5, cy - 5), 1)
    pygame.draw.circle(s, (255, 255, 255), (cx + 7, cy - 5), 1)
    # Nose & muzzle
    pygame.draw.ellipse(s, (248, 198, 168), (cx - 7, cy + 1, 14, 9))
    pygame.draw.circle(s, (195, 95, 78), (cx, cy + 3), 4)
    pygame.draw.arc(s, (148, 72, 55), (cx - 5, cy + 6, 5, 5), math.pi, 0, 2)
    pygame.draw.arc(s, (148, 72, 55), (cx, cy + 6, 5, 5), math.pi, 0, 2)
    # Whiskers
    for wy in [cy + 3, cy + 6]:
        pygame.draw.line(s, (215, 178, 118), (cx - 8, wy), (cx - 20, wy - 1), 1)
        pygame.draw.line(s, (215, 178, 118), (cx + 8, wy), (cx + 20, wy - 1), 1)
    return s


def _gen_ducky(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    y_col = (255, 222, 28)
    y_dark = (198, 165, 10)
    # Body
    pygame.draw.ellipse(s, y_col, (6, 30, 48, 30))
    pygame.draw.ellipse(s, y_dark, (6, 30, 48, 30), 2)
    # Head
    pygame.draw.circle(s, y_col, (40, 24), 15)
    pygame.draw.circle(s, y_dark, (40, 24), 15, 2)
    # Beak
    pygame.draw.polygon(s, (255, 145, 18), [(50, 21), (62, 24), (50, 28)])
    pygame.draw.polygon(s, (200, 105, 8), [(50, 21), (62, 24), (50, 28)], 1)
    pygame.draw.line(s, (200, 105, 8), (50, 24), (61, 24), 1)
    # Eye
    pygame.draw.circle(s, (18, 18, 18), (44, 20), 3)
    pygame.draw.circle(s, (255, 255, 255), (45, 19), 1)
    # Wing
    pygame.draw.arc(s, y_dark, (12, 36, 28, 16), math.radians(30), math.radians(150), 2)
    # Tail bump
    pygame.draw.arc(s, y_col, (2, 38, 12, 14), math.radians(90), math.radians(270), 8)
    return s


def _gen_plane(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    body_col  = (238, 238, 248)
    body_dark = (155, 155, 180)
    stripe    = (48, 108, 205)
    # Fuselage (vertical)
    pygame.draw.ellipse(s, body_col, (22, 5, 20, 54))
    # Stripe
    pygame.draw.rect(s, stripe, (22, 16, 20, 32))
    pygame.draw.ellipse(s, body_col, (22, 5, 20, 54))
    pygame.draw.ellipse(s, body_dark, (22, 5, 20, 54), 2)
    # Left wing
    pygame.draw.polygon(s, body_col, [(22, 26), (2, 22), (2, 34), (22, 38)])
    pygame.draw.polygon(s, body_dark, [(22, 26), (2, 22), (2, 34), (22, 38)], 2)
    # Right wing
    pygame.draw.polygon(s, body_col, [(42, 26), (62, 22), (62, 34), (42, 38)])
    pygame.draw.polygon(s, body_dark, [(42, 26), (62, 22), (62, 34), (42, 38)], 2)
    # Left tail fin
    pygame.draw.polygon(s, body_col, [(22, 46), (12, 54), (12, 58), (22, 52)])
    # Right tail fin
    pygame.draw.polygon(s, body_col, [(42, 46), (52, 54), (52, 58), (42, 52)])
    # Windows
    for wy in [20, 30, 40]:
        pygame.draw.ellipse(s, (148, 208, 255), (27, wy, 10, 7))
        pygame.draw.ellipse(s, (95, 158, 215), (27, wy, 10, 7), 1)
    return s


def _gen_spoon(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    silver     = (205, 208, 218)
    silver_drk = (148, 152, 168)
    cx = size // 2
    # Handle
    pygame.draw.rect(s, silver, (cx - 5, 32, 10, 28), border_radius=4)
    pygame.draw.rect(s, silver_drk, (cx - 5, 32, 10, 28), 2, border_radius=4)
    # Bowl
    pygame.draw.ellipse(s, silver, (10, 4, 44, 32))
    pygame.draw.ellipse(s, silver_drk, (10, 4, 44, 32), 2)
    # Sheen
    pygame.draw.ellipse(s, (235, 238, 245), (15, 8, 18, 10))
    # Face — eyes
    pygame.draw.circle(s, (38, 38, 58), (cx - 7, 16), 4)
    pygame.draw.circle(s, (38, 38, 58), (cx + 7, 16), 4)
    pygame.draw.circle(s, (255, 255, 255), (cx - 6, 15), 1)
    pygame.draw.circle(s, (255, 255, 255), (cx + 8, 15), 1)
    # Smile
    pygame.draw.arc(s, (38, 38, 58), (cx - 7, 20, 14, 9), math.pi, 0, 2)
    # Rosy cheeks
    blush = pygame.Surface((8, 5), pygame.SRCALPHA)
    pygame.draw.ellipse(blush, (255, 155, 155, 120), (0, 0, 8, 5))
    s.blit(blush, (cx - 15, 22))
    s.blit(blush, (cx + 7,  22))
    return s


def _gen_cactus(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    green  = (58, 162, 58)
    dark_g = (38, 118, 38)
    # Main trunk
    pygame.draw.rect(s, green, (23, 16, 18, 44), border_radius=7)
    pygame.draw.rect(s, dark_g, (23, 16, 18, 44), 2, border_radius=7)
    # Left arm
    pygame.draw.rect(s, green, (8, 28, 17, 10), border_radius=5)
    pygame.draw.rect(s, dark_g, (8, 28, 17, 10), 2, border_radius=5)
    pygame.draw.rect(s, green, (8, 20, 10, 18), border_radius=5)
    pygame.draw.rect(s, dark_g, (8, 20, 10, 18), 2, border_radius=5)
    # Right arm
    pygame.draw.rect(s, green, (39, 32, 17, 10), border_radius=5)
    pygame.draw.rect(s, dark_g, (39, 32, 17, 10), 2, border_radius=5)
    pygame.draw.rect(s, green, (46, 26, 10, 16), border_radius=5)
    pygame.draw.rect(s, dark_g, (46, 26, 10, 16), 2, border_radius=5)
    # Spines
    sp = (195, 215, 175)
    for (sx, sy, ex, ey) in [(29, 24, 23, 20), (36, 30, 42, 26),
                              (29, 40, 23, 36), (36, 46, 42, 42),
                              (12, 23, 7,  20), (12, 30, 7,  33),
                              (52, 28, 57, 25), (52, 34, 57, 37)]:
        pygame.draw.line(s, sp, (sx, sy), (ex, ey), 1)
    # Flower
    pygame.draw.circle(s, (235, 72, 72), (32, 16), 6)
    pygame.draw.circle(s, (255, 215, 18), (32, 16), 3)
    return s


def _gen_crown(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    gold  = (255, 202, 18)
    dark_g = (198, 148, 8)
    # Base band
    pygame.draw.rect(s, gold, (7, 40, 50, 18), border_radius=4)
    pygame.draw.rect(s, dark_g, (7, 40, 50, 18), 2, border_radius=4)
    # Three crown points
    for pts in [[(7, 42), (7, 15), (20, 30)],
                [(21, 42), (32, 6), (43, 42)],
                [(44, 42), (57, 15), (57, 42)]]:
        pygame.draw.polygon(s, gold, pts)
        pygame.draw.polygon(s, dark_g, pts, 2)
    # Gems on band
    for (gx, col) in [(20, (218, 28, 28)), (32, (28, 78, 218)), (44, (218, 28, 28))]:
        pygame.draw.circle(s, col, (gx, 49), 5)
        pygame.draw.circle(s, dark_g, (gx, 49), 5, 1)
        pygame.draw.circle(s, (255, 255, 255), (gx - 1, 48), 2)
    # Top center gem
    pygame.draw.circle(s, (35, 198, 35), (32, 12), 5)
    pygame.draw.circle(s, dark_g, (32, 12), 5, 1)
    pygame.draw.circle(s, (255, 255, 255), (31, 11), 2)
    return s


def _gen_taco(size=64) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    shell  = (225, 178, 65)
    dark_s = (172, 125, 32)
    # Top half of shell
    top = [(5, 32), (8, 20), (18, 12), (32, 8), (46, 12), (56, 20), (59, 32)]
    # Bottom half
    bot = [(5, 32), (8, 44), (18, 52), (32, 56), (46, 52), (56, 44), (59, 32)]
    pygame.draw.polygon(s, shell, top + [(59, 32)])
    pygame.draw.polygon(s, (205, 158, 48), bot + [(59, 32)])
    # Toppings inside the gap at front
    pygame.draw.rect(s, (68, 185, 68), (18, 22, 32, 18), border_radius=3)
    pygame.draw.rect(s, (148, 82, 32), (22, 24, 22, 14), border_radius=2)
    pygame.draw.rect(s, (255, 212, 28), (18, 22, 10, 8), border_radius=1)
    pygame.draw.circle(s, (215, 52, 38), (48, 26), 5)
    pygame.draw.circle(s, (238, 88, 68), (43, 29), 4)
    # Shell outlines
    pygame.draw.lines(s, dark_s, False, top, 3)
    pygame.draw.lines(s, dark_s, False, bot, 3)
    pygame.draw.line(s, dark_s, (5, 32), (5, 32), 3)
    return s


_TOKEN_GENERATORS = {
    "pizza":  _gen_pizza,
    "beer":   _gen_beer,
    "dice":   _gen_dice,
    "cup":    _gen_cup,
    "star":   _gen_star,
    "nerf":   _gen_nerf,
    "lion":   _gen_lion,
    "ducky":  _gen_ducky,
    "plane":  _gen_plane,
    "spoon":  _gen_spoon,
    "cactus": _gen_cactus,
    "crown":  _gen_crown,
    "taco":   _gen_taco,
}


def ensure_token_images():
    """Generate default token PNG files if they don't already exist."""
    os.makedirs(os.path.join(TOKENS_DIR, "default"), exist_ok=True)
    os.makedirs(os.path.join(TOKENS_DIR, "custom"),  exist_ok=True)
    for name, path in DEFAULT_TOKENS.items():
        if not os.path.exists(path) and name in _TOKEN_GENERATORS:
            surf = _TOKEN_GENERATORS[name](64)
            pygame.image.save(surf, path)


def load_token_surfaces() -> dict:
    """Load all token images as 64x64 pygame Surfaces."""
    surfaces = {}
    for name, path in ALL_TOKENS.items():
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                surfaces[name] = pygame.transform.smoothscale(img, (64, 64))
                continue
            except Exception:
                pass
        # Fallback: generate on-the-fly
        gen = _TOKEN_GENERATORS.get(name)
        surfaces[name] = gen(64) if gen else _gen_star(64)
    return surfaces


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_text(surf, text, font, color, x, y, align="center"):
    rendered = font.render(str(text), True, color)
    rect = rendered.get_rect()
    if align == "center":
        rect.center = (x, y)
    elif align == "left":
        rect.midleft = (x, y)
    elif align == "right":
        rect.midright = (x, y)
    surf.blit(rendered, rect)


def draw_outlined_text(surf, text, font, color, outline_color, x, y, align="center"):
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
        draw_text(surf, text, font, outline_color, x + dx, y + dy, align)
    draw_text(surf, text, font, color, x, y, align)


def draw_rounded_rect(surf, color, rect, radius=10, border=0, border_color=(0, 0, 0)):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def draw_button(surf, rect, label, font, bg, fg, border_color=MARKER, radius=10, border=3):
    draw_rounded_rect(surf, bg, rect, radius, border, border_color)
    draw_text(surf, label, font, fg, rect.centerx, rect.centery)


def draw_die_face(surf, cx, cy, value, size=70):
    """Draw a die face centered at (cx, cy)."""
    rect = pygame.Rect(cx - size // 2, cy - size // 2, size, size)
    draw_rounded_rect(surf, WHITE, rect, 10, 3, MARKER)
    pad = size // 5
    dot_r = max(4, size // 11)
    dot_patterns = {
        1: [(0, 0)],
        2: [(-1, -1), (1, 1)],
        3: [(-1, -1), (0, 0), (1, 1)],
        4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
        5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
        6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)],
    }
    for px, py in dot_patterns.get(value, [(0, 0)]):
        pygame.draw.circle(surf, MARKER, (cx + px * pad, cy + py * pad), dot_r)


def draw_arrow(surf, color, start, end, width=5, head=14):
    """Draw an arrow from start to end."""
    pygame.draw.line(surf, color, start, end, width)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return
    dx, dy = dx / length, dy / length
    px, py = -dy, dx
    tip   = end
    base1 = (end[0] - dx * head + px * head // 2, end[1] - dy * head + py * head // 2)
    base2 = (end[0] - dx * head - px * head // 2, end[1] - dy * head - py * head // 2)
    pygame.draw.polygon(surf, color, [tip, base1, base2])


def make_cardboard_surface(width, height, seed=42) -> pygame.Surface:
    """Pre-render a cardboard-textured surface."""
    surf = pygame.Surface((width, height))
    base = CARDBOARD
    surf.fill(base)
    rng = random.Random(seed)
    # Horizontal grain lines
    for _ in range(height // 2):
        y = rng.randint(0, height - 1)
        v = rng.randint(-18, 6)
        c = tuple(max(0, min(255, base[i] + v - i * 2)) for i in range(3))
        pygame.draw.line(surf, c, (0, y), (width, y), 1)
    # Noise spots
    for _ in range(width * height // 300):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        v = rng.randint(-28, 10)
        c = tuple(max(0, min(255, base[i] + v)) for i in range(3))
        r = rng.randint(1, 3)
        pygame.draw.circle(surf, c, (x, y), r)
    return surf


# ---------------------------------------------------------------------------
# Main Game class
# ---------------------------------------------------------------------------

class Game:

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Pizza Box Party!")
        self.screen = pygame.display.set_mode(
            (SCREEN_W, SCREEN_H),
            pygame.FULLSCREEN | pygame.SCALED
        )
        self.clock  = pygame.time.Clock()

        # Fonts
        self.f_title  = self._font("impact",      72)
        self.f_header = self._font("impact",      36)
        self.f_label  = self._font("comicsansms", 22, bold=True)
        self.f_body   = self._font("arial",       20)
        self.f_small  = self._font("arial",       15)
        self.f_tiny   = self._font("arial",       12)
        self.f_space  = self._font("arial",       11, bold=True)
        self.f_spnum  = self._font("arial",        9)

        # Assets
        ensure_token_images()
        self.token_surfs = load_token_surfaces()  # {name: Surface 64x64}

        # Scaled-down token surfaces for board (38x38) and leaderboard (40x40)
        self.token_board  = {n: pygame.transform.smoothscale(s, (38, 38))
                             for n, s in self.token_surfs.items()}
        self.token_lead   = {n: pygame.transform.smoothscale(s, (40, 40))
                             for n, s in self.token_surfs.items()}

        # Game state
        self.state = "menu"
        self.menu_subtitle = random.choice(MENU_SUBTITLES)

        # Setup screen state
        self.num_players   = 3
        self.setup_names   = [""] * MAX_PLAYERS
        self.setup_tokens  = [i % len(TOKEN_NAMES) for i in range(MAX_PLAYERS)]
        self.active_input  = None                        # focused name-field index

        # Board selection
        self.boards             = list_boards()          # [{path, name, description}, ...]
        self.selected_board_idx = 0
        # Active board data (replaced each game start from JSON)
        self.board_spaces  = BOARD_SPACES
        self.finish_index  = FINISH_INDEX
        self.board_name    = "Classic Pizza Box"

        # Game state
        self.players       = []
        self.current_idx   = 0
        self.phase         = "wait_roll"   # wait_roll | rolling | moving | resolving
        self.die_value     = 1
        self.display_die   = 1
        self.roll_start    = 0
        self.resolve_start = 0
        self.roll_duration    = 650   # ms
        self.resolve_duration = 2000  # ms
        self.messages      = []
        self.msg_enter_ms  = 420
        self.msg_new_ms    = 1200
        self.winner        = None
        self.board_surf    = None   # pre-rendered static board

        # Movement animation
        self.anim_player    = None  # player currently hopping
        self.anim_from_pos  = 0    # board space index we're hopping FROM
        self.anim_to_pos    = 0    # board space index we're hopping TO
        self.anim_remaining = []   # remaining hop targets after current one
        self.anim_step_start = 0
        self.anim_step_dur   = 175  # ms per one-space hop

        # Last space effect (for the event banner)
        self.last_effect     = None  # "sip","shot","everyone_sip","back","win","custom"
        self.last_effect_val = 0    # numeric value (sips/spaces)
        self.last_effect_msg = ""   # full text for "custom" spaces

        # Interactive effects — set by _resolve_space, consumed by update_game
        self.pending_interactive = None   # phase name to enter after move ends

        # Mate system — paired players always drink together
        self.mates = {}   # {player_obj: mate_obj, mate_obj: player_obj}

        # House rules added via the New Rule tile
        self.house_rules   = []
        self.new_rule_text = ""

        # Pause / ESC overlay
        self.paused     = False
        self.show_rules = False

        # Player picker state (Mate + Drunk Driving tiles)
        self.pick_title    = ""
        self.pick_choices  = []   # list of Player objects to choose from
        self.pick_effect   = None
        self.pick_source   = None
        self.pick_phase_after = None  # phase to set when pick resolves
        self._pick_btns    = []

        # Option picker state (used by multi-choice event squares)
        self.option_title   = ""
        self.option_choices = []   # list[str]
        self.option_effect  = None
        self.option_source  = None
        self._option_btns   = []

        # Pause / rules overlay click targets
        self._pause_resume_btn = None
        self._pause_rules_btn  = None
        self._pause_quit_btn   = None

        # Sidebar button rects (computed relative to screen)
        roll_w, roll_h = 270, 58
        roll_x = SIDEBAR_X + (SIDEBAR_W - roll_w) // 2
        self.roll_btn = pygame.Rect(roll_x, 210, roll_w, roll_h)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _font(name: str, size: int, bold=False) -> pygame.font.Font:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            return pygame.font.Font(None, size)

    def add_message(self, msg: str):
        self.messages.insert(0, {
            "text": msg,
            "ts": pygame.time.get_ticks(),
        })
        if len(self.messages) > 4:
            self.messages = self.messages[:4]

    def _give_sips(self, player, n, _propagate=True):
        """Give sips to player; also propagates once to their mate if paired."""
        player.sips += n
        if _propagate:
            mate = self.mates.get(player)
            if mate:
                self._give_sips(mate, n, _propagate=False)

    def _give_shot(self, player, _propagate=True):
        """Give a shot to player; also propagates once to their mate if paired."""
        player.shots += 1
        if _propagate:
            mate = self.mates.get(player)
            if mate:
                self._give_shot(mate, _propagate=False)

    def _give_bonus(self, player, points, _propagate=True):
        """Give bonus points; also propagates once to their mate if paired."""
        player.bonus_pts += points
        if _propagate:
            mate = self.mates.get(player)
            if mate:
                self._give_bonus(mate, points, _propagate=False)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        while True:
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    if self.state == "game":
                        if self.show_rules:
                            self.show_rules = False
                        elif self.phase == "new_rule_typing":
                            # Cancel rule entry
                            self.phase = "resolving"
                            self.resolve_start = pygame.time.get_ticks()
                            self.last_effect = None
                        elif self.paused:
                            self.paused = False
                        else:
                            self.paused = True
                    else:
                        pygame.quit()
                        sys.exit()

            if self.state == "menu":
                self.handle_menu(events)
                self.draw_menu()
            elif self.state == "setup":
                self.handle_setup(events)
                self.draw_setup()
            elif self.state == "game":
                self.update_game()
                self.handle_game(events)
                self.draw_game()
            elif self.state == "end":
                self.handle_end(events)
                self.draw_end()

            pygame.display.flip()
            self.clock.tick(FPS)

    # ------------------------------------------------------------------
    # MENU
    # ------------------------------------------------------------------

    def handle_menu(self, events):
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self._play_btn.collidepoint(e.pos):
                    self.state = "setup"
                elif self._quit_btn.collidepoint(e.pos):
                    pygame.quit()
                    sys.exit()

    def draw_menu(self):
        # Background
        self.screen.blit(self._get_menu_bg(), (0, 0))

        # Title
        draw_outlined_text(self.screen, "PIZZA BOX PARTY!",
                           self.f_title, YELLOW, MARKER_BROWN,
                           SCREEN_W // 2, 200)
        draw_text(self.screen, self.menu_subtitle,
                  self.f_label, MARKER_BROWN, SCREEN_W // 2, 270)

        # Buttons
        play_r = pygame.Rect(SCREEN_W // 2 - 140, 350, 280, 70)
        quit_r = pygame.Rect(SCREEN_W // 2 - 140, 440, 280, 70)
        self._play_btn = play_r
        self._quit_btn = quit_r

        draw_button(self.screen, play_r, "PLAY!", self.f_header,
                    (80, 170, 80), WHITE, MARKER, 12, 4)
        draw_button(self.screen, quit_r, "Quit", self.f_body,
                    CARDBOARD_DARK, WHITE, MARKER, 12, 3)

        # Decorative doodles
        self._draw_menu_doodles()

    def _get_menu_bg(self) -> pygame.Surface:
        if not hasattr(self, "_menu_bg"):
            self._menu_bg = make_cardboard_surface(SCREEN_W, SCREEN_H, seed=7)
            # Border lines (marker tape look)
            for t in range(0, 4):
                pygame.draw.rect(self._menu_bg, MARKER_BROWN,
                                 (t, t, SCREEN_W - t * 2, SCREEN_H - t * 2), 1)
            pygame.draw.rect(self._menu_bg, MARKER,
                             (8, 8, SCREEN_W - 16, SCREEN_H - 16), 3)
        return self._menu_bg

    def _draw_menu_doodles(self):
        # Pizza slice doodle (top-left)
        pts = [(60, 80), (30, 140), (90, 140)]
        pygame.draw.polygon(self.screen, (255, 195, 40), pts)
        pygame.draw.polygon(self.screen, MARKER_BROWN, pts, 3)
        pygame.draw.circle(self.screen, (190, 40, 40), (60, 120), 6)
        # Star doodle (top-right)
        self._draw_small_star(self.screen, SCREEN_W - 80, 70, 28, YELLOW)
        self._draw_small_star(self.screen, SCREEN_W - 40, 130, 18, ORANGE)
        # Bottom pizza slice
        pts2 = [(SCREEN_W - 80, SCREEN_H - 80),
                (SCREEN_W - 110, SCREEN_H - 30),
                (SCREEN_W - 50, SCREEN_H - 30)]
        pygame.draw.polygon(self.screen, (255, 195, 40), pts2)
        pygame.draw.polygon(self.screen, MARKER_BROWN, pts2, 3)
        # Wavy underline under title
        for i in range(0, 300, 8):
            x1 = SCREEN_W // 2 - 150 + i
            x2 = x1 + 8
            y1 = 295 if (i // 8) % 2 == 0 else 299
            y2 = 299 if (i // 8) % 2 == 0 else 295
            pygame.draw.line(self.screen, MARKER_BROWN, (x1, y1), (x2, y2), 2)

    @staticmethod
    def _draw_small_star(surf, cx, cy, r, color):
        pts = []
        for i in range(10):
            angle = math.pi / 5 * i - math.pi / 2
            ri = r if i % 2 == 0 else r // 2
            pts.append((int(cx + ri * math.cos(angle)), int(cy + ri * math.sin(angle))))
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, MARKER_BROWN, pts, 2)

    # ------------------------------------------------------------------
    # SETUP
    # ------------------------------------------------------------------

    def handle_setup(self, events):
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self._back_btn.collidepoint(e.pos):
                    self.state = "menu"
                    self.active_input = None
                    return
                if self._start_btn.collidepoint(e.pos):
                    self._start_game()
                    return
                if self._minus_btn.collidepoint(e.pos):
                    self.num_players = max(MIN_PLAYERS, self.num_players - 1)
                if self._plus_btn.collidepoint(e.pos):
                    self.num_players = min(MAX_PLAYERS, self.num_players + 1)
                if self.boards and hasattr(self, "_board_left_btn"):
                    if self._board_left_btn.collidepoint(e.pos):
                        self.selected_board_idx = (self.selected_board_idx - 1) % len(self.boards)
                    if self._board_right_btn.collidepoint(e.pos):
                        self.selected_board_idx = (self.selected_board_idx + 1) % len(self.boards)
                self.active_input = None
                for i in range(self.num_players):
                    name_r, left_r, right_r = self._setup_row_rects(i)
                    if name_r.collidepoint(e.pos):
                        self.active_input = i
                    if left_r.collidepoint(e.pos):
                        self.setup_tokens[i] = (self.setup_tokens[i] - 1) % len(TOKEN_NAMES)
                    if right_r.collidepoint(e.pos):
                        self.setup_tokens[i] = (self.setup_tokens[i] + 1) % len(TOKEN_NAMES)

            if e.type == pygame.KEYDOWN and self.active_input is not None:
                idx = self.active_input
                if e.key == pygame.K_BACKSPACE:
                    self.setup_names[idx] = self.setup_names[idx][:-1]
                elif e.key in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
                    self.active_input = None
                elif e.unicode and len(self.setup_names[idx]) < 12:
                    self.setup_names[idx] += e.unicode

    def _two_col(self) -> bool:
        """Use two-column layout when more than 7 players."""
        return self.num_players > 7

    def _setup_row_rects(self, i):
        """Return (name_rect, left_arrow_rect, right_arrow_rect) for player slot i."""
        if self._two_col():
            col      = i // 8          # 0 = left col, 1 = right col
            row      = i % 8
            col_x    = 10 if col == 0 else 650
            row_h    = 62
            y        = 140 + row * row_h
            name_r   = pygame.Rect(col_x + 82, y - 14, 160, 30)
            left_r   = pygame.Rect(col_x + 252, y - 14, 26, 28)
            right_r  = pygame.Rect(col_x + 352, y - 14, 26, 28)
        else:
            row_h    = max(58, (SCREEN_H - 220) // self.num_players)
            y        = 155 + i * row_h
            name_r   = pygame.Rect(185, y - 15, 200, 32)
            left_r   = pygame.Rect(470, y - 15, 28, 30)
            right_r  = pygame.Rect(600, y - 15, 28, 30)
        return name_r, left_r, right_r

    def draw_setup(self):
        self.screen.blit(self._get_menu_bg(), (0, 0))

        draw_outlined_text(self.screen, "PLAYER SETUP",
                           self.f_header, YELLOW, MARKER_BROWN,
                           SCREEN_W // 2, 38)

        # Board selector (left side of header row)
        if self.boards:
            brd = self.boards[self.selected_board_idx]
            bl_r = pygame.Rect(10,  75, 28, 30)
            br_r = pygame.Rect(462, 75, 28, 30)
            bn_r = pygame.Rect(42,  75, 416, 30)
            self._board_left_btn  = bl_r
            self._board_right_btn = br_r
            draw_button(self.screen, bl_r, "<", self.f_tiny,
                        CARDBOARD_DARK, WHITE, MARKER, 5, 2)
            draw_button(self.screen, br_r, ">", self.f_tiny,
                        CARDBOARD_DARK, WHITE, MARKER, 5, 2)
            draw_rounded_rect(self.screen, CARDBOARD_LITE, bn_r, 5, 2, MARKER)
            bname_short = brd["name"][:34]
            draw_text(self.screen, bname_short, self.f_small, MARKER,
                      bn_r.centerx, bn_r.centery - 6)
            draw_text(self.screen, brd["description"][:52], self.f_tiny, MARKER_BROWN,
                      bn_r.centerx, bn_r.centery + 9)

        # Player count selector (right side of header row)
        draw_text(self.screen, "Players:", self.f_body, MARKER, 510, 90)
        minus_r = pygame.Rect(580, 75, 34, 30)
        count_r = pygame.Rect(616, 75, 48, 30)
        plus_r  = pygame.Rect(666, 75, 34, 30)
        self._minus_btn = minus_r
        self._plus_btn  = plus_r

        draw_button(self.screen, minus_r, "-", self.f_label,
                    CARDBOARD_DARK, WHITE, MARKER, 6, 3)
        draw_rounded_rect(self.screen, CARDBOARD_LITE, count_r, 6, 2, MARKER)
        draw_text(self.screen, str(self.num_players), self.f_label,
                  MARKER, count_r.centerx, count_r.centery)
        draw_button(self.screen, plus_r, "+", self.f_label,
                    CARDBOARD_DARK, WHITE, MARKER, 6, 3)

        cursor_vis  = (pygame.time.get_ticks() // 500) % 2 == 0
        two_col     = self._two_col()

        # Column-divider line for 2-col mode
        if two_col:
            pygame.draw.line(self.screen, MARKER_BROWN,
                             (640, 115), (640, SCREEN_H - 70), 2)

        for i in range(self.num_players):
            name_r, left_r, right_r = self._setup_row_rects(i)
            col   = i // 8 if two_col else 0
            row   = i % 8  if two_col else i
            col_x = 10 if col == 0 else 650

            # Row background stripe (alternate)
            if i % 2 == 0:
                stripe = pygame.Rect(col_x + 2, name_r.y - 4,
                                     630 if two_col else 800,
                                     name_r.height + 8)
                pygame.draw.rect(self.screen, (220, 188, 130), stripe,
                                 border_radius=4)

            # Label
            lx = col_x + 40 if two_col else 90
            draw_text(self.screen, f"P{i + 1}", self.f_small,
                      MARKER_BROWN, lx, name_r.centery)

            # Name field
            is_active = self.active_input == i
            field_bg  = WHITE if is_active else CARDBOARD_LITE
            draw_rounded_rect(self.screen, field_bg, name_r, 5,
                              3 if is_active else 2, MARKER)
            display_name = self.setup_names[i] or f"Player {i + 1}"
            name_color   = MARKER if self.setup_names[i] else (160, 140, 100)
            fn = self.f_small if two_col else self.f_body
            draw_text(self.screen, display_name, fn, name_color,
                      name_r.x + 6, name_r.centery, align="left")
            if is_active and cursor_vis:
                cx = name_r.x + 6 + fn.size(self.setup_names[i])[0] + 2
                pygame.draw.line(self.screen, MARKER,
                                 (cx, name_r.top + 4), (cx, name_r.bottom - 4), 2)

            # Token picker
            tok_idx  = self.setup_tokens[i]
            tok_name = TOKEN_NAMES[tok_idx]
            tok_surf = self.token_surfs.get(tok_name)

            draw_button(self.screen, left_r,  "<", self.f_tiny,
                        CARDBOARD_DARK, WHITE, MARKER, 4, 2)
            draw_button(self.screen, right_r, ">", self.f_tiny,
                        CARDBOARD_DARK, WHITE, MARKER, 4, 2)

            # Token image (between arrows)
            tok_size = 26 if two_col else 42
            if tok_surf:
                ts = pygame.transform.smoothscale(tok_surf, (tok_size, tok_size))
                tx = left_r.right + 2
                ty = name_r.centery - tok_size // 2
                self.screen.blit(ts, (tx, ty))
            # Token name text under image
            mid_x = left_r.right + (right_r.left - left_r.right) // 2
            draw_text(self.screen, tok_name, self.f_tiny, MARKER_BROWN,
                      mid_x, name_r.bottom + 4)

        # Bottom buttons
        back_r  = pygame.Rect(80,  SCREEN_H - 68, 150, 48)
        start_r = pygame.Rect(SCREEN_W // 2 - 155, SCREEN_H - 68, 310, 48)
        self._back_btn  = back_r
        self._start_btn = start_r

        draw_button(self.screen, back_r, "< Back", self.f_body,
                    CARDBOARD_DARK, WHITE, MARKER, 10, 3)
        draw_button(self.screen, start_r, "START GAME!", self.f_header,
                    (80, 170, 80), WHITE, MARKER, 12, 4)

    # ------------------------------------------------------------------
    # Game startup
    # ------------------------------------------------------------------

    def _start_game(self):
        self.players = []
        used_tokens = []
        for i in range(self.num_players):
            name = self.setup_names[i].strip() or f"Player {i + 1}"
            tok_idx  = self.setup_tokens[i]
            tok_name = TOKEN_NAMES[tok_idx]
            # Avoid duplicate tokens if possible
            if tok_name in used_tokens and len(TOKEN_NAMES) > self.num_players:
                for alt in TOKEN_NAMES:
                    if alt not in used_tokens:
                        tok_name = alt
                        break
            used_tokens.append(tok_name)
            img = self.token_surfs.get(tok_name, list(self.token_surfs.values())[0])
            self.players.append(Player(name, tok_name, img))

        # Load selected board from JSON (falls back to built-in if no boards found)
        if self.boards:
            brd = self.boards[self.selected_board_idx]
            self.board_spaces, self.finish_index, self.board_name = load_board(brd["path"])
        else:
            self.board_spaces = BOARD_SPACES
            self.finish_index = FINISH_INDEX
            self.board_name   = "Classic Pizza Box"

        self.current_idx   = 0
        self.phase         = "wait_roll"
        self.messages      = []
        self.winner        = None
        self.display_die   = 1
        self.last_effect   = None
        self.pending_interactive = None
        self.mates         = {}
        self.house_rules   = []
        self.new_rule_text = ""
        self.pick_title    = ""
        self.pick_choices  = []
        self.pick_effect   = None
        self.pick_source   = None
        self.option_title   = ""
        self.option_choices = []
        self.option_effect  = None
        self.option_source  = None
        self.paused        = False
        self.show_rules    = False
        self.board_surf    = self._render_board()
        self.add_message("Roll to start! Good luck!")
        self.state         = "game"

    # ------------------------------------------------------------------
    # GAME — update
    # ------------------------------------------------------------------

    def update_game(self):
        now = pygame.time.get_ticks()

        if self.phase == "rolling":
            self.display_die = random.randint(1, 6)
            if now - self.roll_start >= self.roll_duration:
                self.die_value   = random.randint(1, 6)
                self.display_die = self.die_value
                self._start_move(self.players[self.current_idx], self.die_value)

        elif self.phase == "moving":
            if now - self.anim_step_start >= self.anim_step_dur:
                # Commit this hop
                self.anim_player.position = self.anim_to_pos

                if self.anim_player.position >= self.finish_index:
                    # Landed on or past finish
                    self.anim_player.position = self.finish_index
                    self.anim_player.finished = True
                    self.winner = self.anim_player
                    self.add_message(f"{self.anim_player.name} rolled {self.die_value} and WINS!")
                    self.last_effect = "win"
                    self.phase = "resolving"
                    self.resolve_start = now
                    self.anim_player = None

                elif self.anim_remaining:
                    # More hops to go
                    self.anim_from_pos   = self.anim_to_pos
                    self.anim_to_pos     = self.anim_remaining.pop(0)
                    self.anim_step_start = now

                else:
                    # Final hop done — resolve the space
                    msg = self._resolve_space(self.anim_player, self.die_value)
                    self.add_message(msg)
                    if self.anim_player.finished:
                        self.winner = self.anim_player
                    self.phase         = "resolving"
                    self.resolve_start = now
                    self.anim_player   = None

        elif self.phase == "resolving":
            if now - self.resolve_start >= self.resolve_duration:
                if self.pending_interactive:
                    self.phase = self.pending_interactive
                    self.pending_interactive = None
                elif self.winner:
                    self.state = "end"
                else:
                    self._advance_turn()

    def _start_move(self, player: Player, roll: int):
        """Kick off the one-space-at-a-time hop animation."""
        start = player.position
        final = min(start + roll, self.finish_index)
        steps = list(range(start + 1, final + 1))

        if not steps:
            self.phase = "resolving"
            self.resolve_start = pygame.time.get_ticks()
            return

        self.anim_player     = player
        self.anim_from_pos   = start
        self.anim_to_pos     = steps[0]
        self.anim_remaining  = steps[1:]
        self.anim_step_start = pygame.time.get_ticks()
        self.phase = "moving"

    def _resolve_space(self, player: Player, roll: int) -> str:
        space  = self.board_spaces[player.position]
        # Use "effect" field if present; fall back to "type" for old-style spaces
        effect = space.get("effect", space.get("type", "none"))
        label  = space["label"]
        value  = space.get("value", 1)

        intro = f"{player.name} rolled {roll}. "
        self.last_effect     = effect
        self.last_effect_val = value

        # ------------------------------------------------------------------
        # BUILT-IN EFFECTS
        # ------------------------------------------------------------------

        if effect == "sip":
            self._give_sips(player, value)
            suffix = "s" if value > 1 else ""
            return intro + f"Landed on {label}. Take {value} sip{suffix}!"

        if effect == "shot":
            self._give_shot(player)
            return intro + f"Landed on {label}. TAKE A SHOT!"

        if effect == "everyone_sip":
            for p in self.players:
                self._give_sips(p, 1, _propagate=False)
            return intro + f"Landed on {label}. EVERYONE TAKES A SIP!"

        if effect == "back":
            prev_pos = player.position
            player.position = max(0, player.position - value)
            suffix = "s" if value > 1 else ""
            landed_label = self.board_spaces[player.position]["label"]

            # Resolve the new tile after sliding back so drinks/points are counted
            # from the actual landing spot (and banner reflects that final effect).
            if player.position != prev_pos:
                chained_msg = self._resolve_space(player, roll)
                intro_prefix = f"{player.name} rolled {roll}. "
                if chained_msg.startswith(intro_prefix):
                    chained_msg = chained_msg[len(intro_prefix):]
                return (
                    intro
                    + f"Landed on {label}. Slides back {value} space{suffix} to {landed_label}. "
                    + chained_msg
                )
            return intro + f"Landed on {label}. Slides back {value} space{suffix} to {landed_label}."

        if effect == "forward":
            player.position = min(self.finish_index, player.position + value)
            return intro + f"Landed on {label}. Zooms forward {value}!"

        if effect == "finish":
            player.finished  = True
            self.last_effect = "win"
            return intro + f"WINS at {label}!"

        # ------------------------------------------------------------------
        # PARTY EVENT COMPONENT EFFECTS
        # ------------------------------------------------------------------

        if effect == "chicks_dicks":
            self.option_title = "Choose: Chicks or Dicks"
            self.option_choices = ["Chicks", "Dicks"]
            self.option_effect = "chicks_dicks"
            self.option_source = player
            self.pending_interactive = "pick_option"
            self.last_effect = None
            return intro + "Chicks / Dicks: pick one option."

        if effect == "androids_iphones":
            self.option_title = "Choose: Androids or iPhones"
            self.option_choices = ["Androids", "iPhones"]
            self.option_effect = "androids_iphones"
            self.option_source = player
            self.pending_interactive = "pick_option"
            self.last_effect = None
            return intro + "Androids / iPhones: pick one option."

        if effect == "shotgun":
            self._give_shot(player)
            self.last_effect = "shot"
            return intro + f"{player.name} hits Shotgun. Take 1 shot!"

        if effect == "double_or_single_shot":
            shots = 2 if random.random() < 0.5 else 1
            for _ in range(shots):
                self._give_shot(player)
            self.last_effect = "shot"
            return intro + f"{player.name} chose {shots} shot{'s' if shots > 1 else ''}."

        if effect == "karaoke":
            self._give_shot(player)
            self.last_effect = "shot"
            return intro + f"{player.name} landed on Karaoke. Sing now!"

        if effect in ("thunderstruck", "rattlin_bog"):
            for p in self.players:
                self._give_shot(p, _propagate=False)
                self._give_bonus(p, 20, _propagate=False)  # 100 from shot +20 bonus = 120
            self.last_effect = "shot"
            name = "Thunderstruck" if effect == "thunderstruck" else "Rattlin Bog"
            return intro + f"{name}: everyone takes a shot (+120 pts each)."

        if effect == "mate":
            choices = [p for p in self.players if p is not player]
            if not choices:
                self.last_effect = None
                return intro + "No available player to pair as Mate."
            self.pick_title = f"{player.name}: pick your Mate"
            self.pick_choices = choices
            self.pick_effect = "mate"
            self.pick_source = player
            self.pending_interactive = "pick_player"
            return intro + "Mate event! Choose another player to pair for the game."

        if effect == "hot_seat":
            self.last_effect = "custom"
            self.last_effect_msg = f"{player.name} is in the Hot Seat. No drinks, no points - discussion time."
            return self.last_effect_msg

        if effect == "drunk_driving":
            choices = list(self.players)
            self.pick_title = "Drunk Driving: group picks who 'lost'"
            self.pick_choices = choices
            self.pick_effect = "drunk_driving"
            self.pick_source = player
            self.pending_interactive = "pick_player"
            return intro + "Drunk Driving event! Pick one player for the penalty."

        if effect == "new_rule":
            self.new_rule_text = ""
            self.pending_interactive = "new_rule_typing"
            self.last_effect = "custom"
            self.last_effect_msg = f"{player.name} can add a new house rule."
            return self.last_effect_msg

        # ------------------------------------------------------------------
        # CUSTOM EFFECT — shows the space's "msg" as a big banner.
        # Players read the text and follow the instruction themselves.
        # ------------------------------------------------------------------

        if effect == "custom":
            template = space.get("msg", "{name} landed on {label}!")
            full_msg = template.format(name=player.name, label=label)
            self.last_effect_msg = full_msg
            return full_msg

        # ------------------------------------------------------------------
        # NONE / NORMAL — nothing happens
        # ------------------------------------------------------------------

        self.last_effect = None
        return intro + f"Landed on {label}."

    def _advance_turn(self):
        n = len(self.players)
        self.current_idx = (self.current_idx + 1) % n
        self.phase = "wait_roll"

    # ------------------------------------------------------------------
    # GAME — input
    # ------------------------------------------------------------------

    def handle_game(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN and self.phase == "new_rule_typing":
                if e.key == pygame.K_RETURN:
                    txt = self.new_rule_text.strip()
                    if txt:
                        self.house_rules.append(txt)
                        self.add_message(f"New Rule added: {txt}")
                    self.phase = "resolving"
                    self.resolve_start = pygame.time.get_ticks()
                    self.last_effect = None
                elif e.key == pygame.K_BACKSPACE:
                    self.new_rule_text = self.new_rule_text[:-1]
                elif e.unicode and len(self.new_rule_text) < 100:
                    self.new_rule_text += e.unicode

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.paused:
                    if self.show_rules:
                        self.show_rules = False
                        return
                    if self._pause_resume_btn and self._pause_resume_btn.collidepoint(e.pos):
                        self.paused = False
                        return
                    if self._pause_rules_btn and self._pause_rules_btn.collidepoint(e.pos):
                        self.show_rules = True
                        return
                    if self._pause_quit_btn and self._pause_quit_btn.collidepoint(e.pos):
                        self.state = "end"
                        self.paused = False
                        return

                if self.phase == "pick_player":
                    for btn, choice in self._pick_btns:
                        if btn.collidepoint(e.pos):
                            self._resolve_player_pick(choice)
                            return

                if self.phase == "pick_option":
                    for btn, choice in self._option_btns:
                        if btn.collidepoint(e.pos):
                            self._resolve_option_pick(choice)
                            return

                if (self.phase == "wait_roll"
                        and self.roll_btn.collidepoint(e.pos)):
                    self.phase      = "rolling"
                    self.roll_start = pygame.time.get_ticks()

    def _resolve_player_pick(self, choice: Player):
        if self.pick_effect == "mate":
            source = self.pick_source
            # Clear old pairings on both sides before assigning.
            old_a = self.mates.pop(source, None)
            if old_a:
                self.mates.pop(old_a, None)
            old_b = self.mates.pop(choice, None)
            if old_b:
                self.mates.pop(old_b, None)
            self.mates[source] = choice
            self.mates[choice] = source
            self.add_message(f"{source.name} and {choice.name} are now Mates.")

        elif self.pick_effect == "drunk_driving":
            self._give_shot(choice, _propagate=False)
            choice.penalty_pts += 100
            self.add_message(f"{choice.name} takes 1 shot for Drunk Driving (net 0 score change).")

        self.pick_title = ""
        self.pick_choices = []
        self.pick_effect = None
        self.pick_source = None
        self._pick_btns = []
        self.phase = "resolving"
        self.resolve_start = pygame.time.get_ticks()
        self.last_effect = None

    def _resolve_option_pick(self, choice: str):
        player = self.option_source
        if player is not None:
            self._give_sips(player, 1)
            self.last_effect = "custom"
            self.last_effect_msg = (
                f"{choice} selected. {player.name} takes 1 sip."
            )
            self.add_message(self.last_effect_msg)

        self.option_title = ""
        self.option_choices = []
        self.option_effect = None
        self.option_source = None
        self._option_btns = []
        self.phase = "resolving"
        self.resolve_start = pygame.time.get_ticks()

    # ------------------------------------------------------------------
    # GAME — draw
    # ------------------------------------------------------------------

    def draw_game(self):
        self.screen.blit(self.board_surf, (0, 0))
        self._draw_tokens()
        if self.phase == "resolving" and self.last_effect:
            self._draw_event_banner()
        self._draw_sidebar()
        if self.phase == "pick_player":
            self._draw_player_picker()
        if self.phase == "pick_option":
            self._draw_option_picker()
        if self.phase == "new_rule_typing":
            self._draw_new_rule_overlay()
        if self.paused:
            self._draw_pause_overlay()

    def _draw_event_banner(self):
        # Built-in effects: one bold headline
        builtin = {
            "sip":          (BLUE,   f"TAKE {self.last_effect_val} SIP{'S' if self.last_effect_val != 1 else ''}!"),
            "shot":         (RED,    "TAKE A SHOT!"),
            "everyone_sip": (TEAL,   "EVERYONE SIPS!"),
            "back":         (ORANGE, f"SLIDE BACK {self.last_effect_val}!"),
            "win":          (GOLD,   "WINNER!"),
        }

        if self.last_effect in builtin:
            color, headline = builtin[self.last_effect]
            bw, bh = BOARD_W - 60, 100
            bx, by = 30, (SCREEN_H - bh) // 2
            overlay = pygame.Surface((bw, bh), pygame.SRCALPHA)
            overlay.fill((18, 12, 6, 210))
            pygame.draw.rect(overlay, color, (0, 0, bw, bh), 4, border_radius=14)
            self.screen.blit(overlay, (bx, by))
            draw_outlined_text(self.screen, headline, self.f_title,
                               color, MARKER, bx + bw // 2, by + bh // 2)

        elif self.last_effect == "custom":
            # Custom spaces: word-wrapped message in a taller banner
            color = ORANGE
            bw    = BOARD_W - 60
            bx    = 30

            # Word-wrap the message to fit the banner width
            words  = self.last_effect_msg.split()
            lines, line = [], ""
            for w in words:
                test = (line + " " + w).strip()
                if self.f_label.size(test)[0] < bw - 32:
                    line = test
                else:
                    if line:
                        lines.append(line)
                    line = w
            if line:
                lines.append(line)

            line_h = self.f_label.get_height() + 4
            bh     = max(90, len(lines) * line_h + 36)
            by     = (SCREEN_H - bh) // 2

            overlay = pygame.Surface((bw, bh), pygame.SRCALPHA)
            overlay.fill((18, 12, 6, 218))
            pygame.draw.rect(overlay, color, (0, 0, bw, bh), 4, border_radius=14)
            self.screen.blit(overlay, (bx, by))

            text_y = by + (bh - len(lines) * line_h) // 2 + line_h // 2
            for text_line in lines:
                draw_text(self.screen, text_line, self.f_label,
                          WHITE, bx + bw // 2, text_y)
                text_y += line_h

    def _draw_player_picker(self):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        self.screen.blit(ov, (0, 0))

        w, h = 560, 120 + len(self.pick_choices) * 50
        x, y = (SCREEN_W - w) // 2, (SCREEN_H - h) // 2
        panel = pygame.Rect(x, y, w, h)
        draw_rounded_rect(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
        draw_text(self.screen, self.pick_title or "Choose a player", self.f_label, MARKER,
                  panel.centerx, y + 28)

        self._pick_btns = []
        by = y + 56
        for p in self.pick_choices:
            btn = pygame.Rect(x + 20, by, w - 40, 38)
            draw_button(self.screen, btn, p.name, self.f_body, CARDBOARD_DARK, WHITE, MARKER, 8, 2)
            self._pick_btns.append((btn, p))
            by += 44

    def _draw_option_picker(self):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        self.screen.blit(ov, (0, 0))

        w, h = 560, 120 + len(self.option_choices) * 50
        x, y = (SCREEN_W - w) // 2, (SCREEN_H - h) // 2
        panel = pygame.Rect(x, y, w, h)
        draw_rounded_rect(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
        draw_text(self.screen, self.option_title or "Choose an option", self.f_label, MARKER,
                  panel.centerx, y + 28)

        self._option_btns = []
        by = y + 56
        for opt in self.option_choices:
            btn = pygame.Rect(x + 20, by, w - 40, 38)
            draw_button(self.screen, btn, opt, self.f_body, CARDBOARD_DARK, WHITE, MARKER, 8, 2)
            self._option_btns.append((btn, opt))
            by += 44

    def _draw_new_rule_overlay(self):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))

        w, h = 760, 210
        x, y = (SCREEN_W - w) // 2, (SCREEN_H - h) // 2
        panel = pygame.Rect(x, y, w, h)
        draw_rounded_rect(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
        draw_text(self.screen, "NEW RULE", self.f_header, MARKER_BROWN, panel.centerx, y + 34)
        draw_text(self.screen, "Type a house rule and press Enter", self.f_small, MARKER,
                  panel.centerx, y + 62)
        input_r = pygame.Rect(x + 26, y + 84, w - 52, 46)
        draw_rounded_rect(self.screen, WHITE, input_r, 8, 2, MARKER)
        txt = self.new_rule_text if self.new_rule_text else "Anyone who says 'um' drinks."
        col = MARKER if self.new_rule_text else (120, 120, 120)
        draw_text(self.screen, txt, self.f_body, col, input_r.x + 10, input_r.centery, align="left")
        draw_text(self.screen, "ESC to cancel", self.f_tiny, MARKER_BROWN,
                  panel.centerx, y + h - 24)

    def _draw_pause_overlay(self):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))

        if self.show_rules:
            w, h = 860, 560
            x, y = (SCREEN_W - w) // 2, (SCREEN_H - h) // 2
            panel = pygame.Rect(x, y, w, h)
            draw_rounded_rect(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
            draw_text(self.screen, "RULES", self.f_header, MARKER_BROWN, panel.centerx, y + 30)
            draw_text(self.screen, "House Rules", self.f_label, MARKER, x + 26, y + 72, align="left")
            if self.house_rules:
                ry = y + 104
                for i, rule in enumerate(self.house_rules[:14]):
                    draw_text(self.screen, f"{i + 1}. {rule}", self.f_small, MARKER,
                              x + 26, ry, align="left")
                    ry += 30
            else:
                draw_text(self.screen, "No house rules yet.", self.f_small, MARKER_BROWN,
                          x + 26, y + 110, align="left")
            draw_text(self.screen, "Click anywhere or press ESC to go back", self.f_tiny, MARKER_BROWN,
                      panel.centerx, y + h - 24)
            return

        w, h = 420, 290
        x, y = (SCREEN_W - w) // 2, (SCREEN_H - h) // 2
        panel = pygame.Rect(x, y, w, h)
        draw_rounded_rect(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
        draw_text(self.screen, "PAUSED", self.f_header, MARKER_BROWN, panel.centerx, y + 36)

        self._pause_resume_btn = pygame.Rect(x + 60, y + 78, 300, 48)
        self._pause_rules_btn  = pygame.Rect(x + 60, y + 136, 300, 48)
        self._pause_quit_btn   = pygame.Rect(x + 60, y + 194, 300, 48)

        draw_button(self.screen, self._pause_resume_btn, "Resume", self.f_body,
                    (80, 170, 80), WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._pause_rules_btn, "Rules", self.f_body,
                    CARDBOARD_DARK, WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._pause_quit_btn, "Quit Early", self.f_body,
                    (150, 70, 60), WHITE, MARKER, 10, 3)

    def _draw_tokens(self):
        # Group non-animating players by position
        pos_groups: dict[int, list] = {}
        for p in self.players:
            if p is self.anim_player:
                continue
            pos_groups.setdefault(p.position, []).append(p)

        for pos, group in pos_groups.items():
            space = self.board_spaces[pos]
            cx, cy = space["pos"]
            n = len(group)
            offsets = get_token_offsets(n)
            for i, player in enumerate(group):
                ox, oy = offsets[i] if i < len(offsets) else (0, 0)
                img = self.token_board.get(player.token_name)
                if img:
                    self.screen.blit(img, (cx + ox - 19, cy + oy - 19))

        # Draw the animating player with a parabolic hop arc
        if self.anim_player is not None and self.phase == "moving":
            elapsed = pygame.time.get_ticks() - self.anim_step_start
            t = min(1.0, elapsed / max(1, self.anim_step_dur))

            fx, fy = self.board_spaces[self.anim_from_pos]["pos"]
            tx, ty = self.board_spaces[self.anim_to_pos]["pos"]

            ax = fx + (tx - fx) * t
            ay = fy + (ty - fy) * t
            # Parabolic arc: peak at t=0.5
            arc_offset = -36 * 4 * t * (1.0 - t)
            # Scale up slightly at arc peak for a "pop" feel
            scale = 1.0 + 0.25 * 4 * t * (1.0 - t)
            sz = int(38 * scale)

            img = self.token_surfs.get(self.anim_player.token_name)
            if img:
                scaled = pygame.transform.smoothscale(img, (sz, sz))
                self.screen.blit(scaled, (int(ax) - sz // 2, int(ay + arc_offset) - sz // 2))

            # Shadow under the token (flattened ellipse on the board)
            shadow_surf = pygame.Surface((38, 12), pygame.SRCALPHA)
            alpha = int(80 * (1.0 - 0.6 * 4 * t * (1.0 - t)))  # fades at peak
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha), (0, 0, 38, 12))
            self.screen.blit(shadow_surf, (int(ax) - 19, int(ay) - 6))

    def _draw_sidebar(self):
        # Background
        sb = pygame.Rect(SIDEBAR_X, 0, SIDEBAR_W, SCREEN_H)
        draw_rounded_rect(self.screen, SIDEBAR_BG, sb, 0, 4, MARKER_BROWN)
        pygame.draw.line(self.screen, MARKER, (SIDEBAR_X, 0), (SIDEBAR_X, SCREEN_H), 4)

        current = self.players[self.current_idx]

        # --- Current player banner ---
        banner = pygame.Rect(SIDEBAR_X + 8, 8, SIDEBAR_W - 16, 75)
        draw_rounded_rect(self.screen, CARDBOARD_DARK, banner, 10, 3, MARKER)
        tok = self.token_lead.get(current.token_name)
        if tok:
            self.screen.blit(tok, (SIDEBAR_X + 14, 17))
        turn_x = SIDEBAR_X + 62
        draw_text(self.screen, "IT'S YOUR TURN,", self.f_small,
                  CARDBOARD_LITE, turn_x, 28, align="left")
        name_display = current.name[:10] + ("…" if len(current.name) > 10 else "")
        draw_text(self.screen, name_display.upper() + "!", self.f_label,
                  YELLOW, turn_x, 52, align="left")

        # --- Die display ---
        die_cx = SIDEBAR_X + SIDEBAR_W // 2
        draw_die_face(self.screen, die_cx, 148, self.display_die, 72)
        die_label = "ROLLING..." if self.phase == "rolling" else f"Rolled: {self.die_value}"
        draw_text(self.screen, die_label, self.f_small, MARKER,
                  die_cx, 195)

        # --- Roll button ---
        can_roll = (self.phase == "wait_roll")
        btn_color = (72, 168, 72) if can_roll else (130, 130, 120)
        draw_button(self.screen, self.roll_btn, "ROLL THE DIE", self.f_label,
                    btn_color, WHITE, MARKER, 12, 4)

        # --- Message area ---
        msg_y = 285
        now = pygame.time.get_ticks()
        pygame.draw.line(self.screen, MARKER_BROWN,
                         (SIDEBAR_X + 10, msg_y - 8), (SIDEBAR_X + SIDEBAR_W - 10, msg_y - 8), 2)
        for i, entry in enumerate(self.messages[:3]):
            msg = entry["text"] if isinstance(entry, dict) else str(entry)
            age = now - entry.get("ts", 0) if isinstance(entry, dict) else self.msg_new_ms + 1
            alpha = 255 - i * 70
            t = min(1.0, max(0.0, age / max(1, self.msg_enter_ms)))
            y_offset = int((1.0 - t) * 12)

            # Wrap long messages
            words = msg.split()
            lines, line = [], ""
            for w in words:
                test = (line + " " + w).strip()
                if self.f_small.size(test)[0] < SIDEBAR_W - 20:
                    line = test
                else:
                    if line:
                        lines.append(line)
                    line = w
            if line:
                lines.append(line)

            # New message transition cue: subtle highlight + badge.
            if age < self.msg_new_ms:
                pulse = 1.0 - (age / max(1, self.msg_new_ms))
                hl_alpha = int(95 * pulse)
                hl_h = len(lines[:2]) * 18 + 6
                hl = pygame.Surface((SIDEBAR_W - 16, hl_h), pygame.SRCALPHA)
                hl.fill((255, 220, 120, hl_alpha))
                self.screen.blit(hl, (SIDEBAR_X + 8, msg_y - 2 + y_offset))
                if i == 0:
                    draw_text(self.screen, "NEW", self.f_tiny, ORANGE,
                              SIDEBAR_X + SIDEBAR_W - 20, msg_y + 7 + y_offset, align="right")

            for j, text_line in enumerate(lines[:2]):
                col_val = max(0, min(255, MARKER[0] + (255 - alpha) * 2 // 3))
                draw_text(self.screen, text_line, self.f_small,
                          (col_val, col_val // 2, 0),
                          SIDEBAR_X + SIDEBAR_W // 2, msg_y + y_offset + j * 18)
            msg_y += len(lines[:2]) * 18 + 6

        # --- Leaderboard ---
        lb_y = 400
        pygame.draw.line(self.screen, MARKER_BROWN,
                         (SIDEBAR_X + 10, lb_y - 8), (SIDEBAR_X + SIDEBAR_W - 10, lb_y - 8), 2)
        draw_text(self.screen, "STANDINGS", self.f_small, MARKER_BROWN,
                  SIDEBAR_X + SIDEBAR_W // 2, lb_y)
        lb_y += 18

        sorted_players = sorted(self.players,
                                key=lambda p: (-p.score, -p.position))
        rank_colors = [GOLD, SILVER, BRONZE]
        n_players   = len(sorted_players)
        row_h       = max(36, (SCREEN_H - lb_y - 8) // n_players)
        compact     = row_h < 52   # tight layout when many players

        for rank, p in enumerate(sorted_players):
            ry   = lb_y + rank * row_h
            card = pygame.Rect(SIDEBAR_X + 4, ry + 2, SIDEBAR_W - 8, row_h - 4)
            bg   = (205, 175, 95) if p is current else CARDBOARD_DARK
            draw_rounded_rect(self.screen, bg, card, 7, 2, MARKER_BROWN)

            mid = ry + row_h // 2

            # Rank circle
            rc = rank_colors[rank] if rank < 3 else CARDBOARD_LITE
            pygame.draw.circle(self.screen, rc, (SIDEBAR_X + 18, mid), 10)
            draw_text(self.screen, str(rank + 1), self.f_tiny, MARKER,
                      SIDEBAR_X + 18, mid)

            # Token (fits in row height minus padding)
            tok_sz  = min(row_h - 8, 36)
            tok     = self.token_surfs.get(p.token_name)
            if tok:
                ts = pygame.transform.smoothscale(tok, (tok_sz, tok_sz))
                self.screen.blit(ts, (SIDEBAR_X + 32, mid - tok_sz // 2))

            tx = SIDEBAR_X + 32 + tok_sz + 4

            if compact:
                # Single line: name  |  shots/sips  |  score
                short = p.name[:7] + ("…" if len(p.name) > 7 else "")
                draw_text(self.screen, short, self.f_tiny, WHITE,
                          tx, mid, align="left")
                stat_str = f"{p.shots}sh {p.sips}si"
                draw_text(self.screen, stat_str, self.f_tiny, CARDBOARD_LITE,
                          tx + 62, mid, align="left")
                draw_text(self.screen, f"{p.score}p", self.f_tiny, YELLOW,
                          card.right - 4, mid, align="right")
            else:
                # Two lines: name on top, stats on bottom
                short = p.name[:10] + ("…" if len(p.name) > 10 else "")
                draw_text(self.screen, short, self.f_small, WHITE,
                          tx, mid - 9, align="left")
                # Score prominently right-aligned
                draw_text(self.screen, f"{p.score} pts", self.f_small, YELLOW,
                          card.right - 5, mid - 9, align="right")
                # Shots and sips with coloured labels
                shot_str = f"{p.shots} shots"
                sip_str  = f"{p.sips} sips"
                draw_text(self.screen, shot_str, self.f_tiny, (255, 130, 130),
                          tx, mid + 8, align="left")
                draw_text(self.screen, f"•", self.f_tiny, CARDBOARD_LITE,
                          tx + 58, mid + 8)
                draw_text(self.screen, sip_str, self.f_tiny, (130, 180, 255),
                          tx + 68, mid + 8, align="left")
                title = get_flavor_title(p.score)
                draw_text(self.screen, title, self.f_tiny, ORANGE,
                          card.right - 5, mid + 8, align="right")

    # ------------------------------------------------------------------
    # Board pre-render
    # ------------------------------------------------------------------

    def _render_board(self) -> pygame.Surface:
        surf = make_cardboard_surface(BOARD_W, SCREEN_H)

        # Border
        for t in range(4):
            pygame.draw.rect(surf, MARKER_BROWN, (t, t, BOARD_W - t * 2, SCREEN_H - t * 2), 1)
        pygame.draw.rect(surf, MARKER, (6, 6, BOARD_W - 12, SCREEN_H - 12), 3)

        # Board title (uses the loaded board's name)
        title_font = self._font("impact", 26)
        draw_text(surf, self.board_name.upper(), title_font, MARKER_BROWN,
                  BOARD_W // 2, 24)

        # Path lines between consecutive spaces
        for i in range(len(self.board_spaces) - 1):
            a = self.board_spaces[i]["pos"]
            b = self.board_spaces[i + 1]["pos"]
            pygame.draw.line(surf, MARKER_BROWN, a, b, 7)
            pygame.draw.line(surf, CARDBOARD_DARK, a, b, 4)

        # Back arrows (orange marker on the space itself)
        for sp in self.board_spaces:
            if sp["type"] == "back":
                cx, cy = sp["pos"]
                v = sp.get("value", 1)
                prev_pos = max(0, sp["id"] - v)
                tgt = self.board_spaces[prev_pos]["pos"]
                draw_arrow(surf, (210, 100, 30), sp["pos"], tgt, width=4, head=12)

        # Space circles
        sp_font  = self.f_space
        num_font = self.f_spnum
        for sp in self.board_spaces:
            cx, cy = sp["pos"]
            stype  = sp["type"]
            color  = sp.get("color", SPACE_COLORS.get(stype, CARDBOARD_LITE))

            # Outer ring (marker outline)
            pygame.draw.circle(surf, MARKER, (cx, cy), SPACE_RADIUS + 3)
            # Fill
            pygame.draw.circle(surf, color, (cx, cy), SPACE_RADIUS)
            # Inner ring
            pygame.draw.circle(surf, MARKER, (cx, cy), SPACE_RADIUS, 3)

            # Type icon
            icon = TYPE_ICONS.get(stype, "")
            if icon:
                draw_text(surf, icon, sp_font, MARKER, cx, cy)

            # Space number (below circle)
            draw_text(surf, str(sp["id"]), num_font, MARKER_BROWN, cx, cy + SPACE_RADIUS + 8)

        # Finish star decoration
        fx, fy = self.board_spaces[self.finish_index]["pos"]
        self._draw_small_star(surf, fx, fy - SPACE_RADIUS - 16, 14, GOLD)
        self._draw_small_star(surf, fx - 20, fy - SPACE_RADIUS - 12, 10, YELLOW)
        self._draw_small_star(surf, fx + 20, fy - SPACE_RADIUS - 12, 10, YELLOW)

        # Start label
        sx, sy = self.board_spaces[0]["pos"]
        draw_text(surf, "START", self._font("arial", 11, bold=True),
                  MARKER, sx, sy + SPACE_RADIUS + 20)

        return surf

    # ------------------------------------------------------------------
    # END SCREEN
    # ------------------------------------------------------------------

    def handle_end(self, events):
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self._again_btn.collidepoint(e.pos):
                    for p in self.players:
                        p.reset()
                    self.current_idx   = 0
                    self.phase         = "wait_roll"
                    self.messages      = []
                    self.winner        = None
                    self.display_die   = 1
                    self.last_effect   = None
                    self.pending_interactive = None
                    self.mates         = {}
                    self.house_rules   = []
                    self.new_rule_text = ""
                    self.pick_title    = ""
                    self.pick_choices  = []
                    self.pick_effect   = None
                    self.pick_source   = None
                    self.option_title   = ""
                    self.option_choices = []
                    self.option_effect  = None
                    self.option_source  = None
                    self.paused        = False
                    self.show_rules    = False
                    self.board_surf    = self._render_board()
                    self.add_message("Roll to start again!")
                    self.state         = "game"
                elif self._menu_btn.collidepoint(e.pos):
                    self.state = "menu"

    def draw_end(self):
        # Background
        self.screen.blit(self._get_menu_bg(), (0, 0))

        # Winner banner
        w = self.winner or self.players[0]
        draw_outlined_text(self.screen, "GAME OVER!", self.f_title,
                           YELLOW, MARKER_BROWN, SCREEN_W // 2, 90)
        tok = self.token_surfs.get(w.token_name)
        if tok:
            big_tok = pygame.transform.smoothscale(tok, (88, 88))
            self.screen.blit(big_tok, (SCREEN_W // 2 - 44, 140))
        draw_outlined_text(self.screen, f"{w.name} WINS!",
                           self.f_header, (80, 220, 80), MARKER,
                           SCREEN_W // 2, 250)

        # Rankings table
        sorted_players = sorted(self.players,
                                key=lambda p: (-p.score, -p.position))
        headers = ["#", "Player", "Score", "Shots", "Sips", "Title"]
        col_x   = [100, 200, 430, 560, 650, 760]
        th_y = 295
        for ci, (hdr, cx) in enumerate(zip(headers, col_x)):
            draw_text(self.screen, hdr, self.f_label, MARKER_BROWN, cx, th_y)

        rank_colors = [GOLD, SILVER, BRONZE]
        for rank, p in enumerate(sorted_players):
            ry = 325 + rank * 58
            row_bg = pygame.Rect(80, ry - 20, SCREEN_W - 160, 52)
            bg_col = (230, 200, 120) if rank == 0 else CARDBOARD_LITE
            draw_rounded_rect(self.screen, bg_col, row_bg, 8, 2, MARKER_BROWN)

            rc = rank_colors[rank] if rank < 3 else CARDBOARD
            pygame.draw.circle(self.screen, rc, (col_x[0], ry + 6), 14)
            draw_text(self.screen, str(rank + 1), self.f_body, MARKER,
                      col_x[0], ry + 6)

            tok_sm = self.token_lead.get(p.token_name)
            if tok_sm:
                self.screen.blit(tok_sm, (col_x[1] - 22, ry - 16))
            draw_text(self.screen, p.name, self.f_body, MARKER,
                      col_x[1] + 22, ry + 6, align="left")
            draw_text(self.screen, str(p.score),  self.f_body, MARKER, col_x[2], ry + 6)
            draw_text(self.screen, str(p.shots),  self.f_body, RED,    col_x[3], ry + 6)
            draw_text(self.screen, str(p.sips),   self.f_body, BLUE,   col_x[4], ry + 6)
            draw_text(self.screen, get_flavor_title(p.score), self.f_small,
                      MARKER_BROWN, col_x[5], ry + 6)

        # Buttons
        again_r = pygame.Rect(SCREEN_W // 2 - 270, SCREEN_H - 85, 240, 58)
        menu_r  = pygame.Rect(SCREEN_W // 2 + 30,  SCREEN_H - 85, 240, 58)
        self._again_btn = again_r
        self._menu_btn  = menu_r

        draw_button(self.screen, again_r, "Play Again!", self.f_header,
                    (72, 168, 72), WHITE, MARKER, 12, 4)
        draw_button(self.screen, menu_r, "Main Menu", self.f_label,
                    CARDBOARD_DARK, WHITE, MARKER, 12, 3)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    game = Game()
    game.run()
