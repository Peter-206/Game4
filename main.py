"""
main.py — Pizza Box Party! entry point and game loop.
Run with:  python main.py
"""

import pygame
import io
import sys
import random
import math
import os
import time
from collections import OrderedDict
from dataclasses import replace

from game_data import *
from game_data import get_token_offsets, load_board, scan_boards
from board_creator import (
    BoardCreatorError,
    BoardDraft,
    available_event_options,
    event_key_for_space,
    save_new_board,
)
from app_settings import (AppSettings, DISPLAY_MODES, GUI_SCALES,
                          load_settings, save_settings)
from game_engine import RulesEngine
from board_view import HorizontalCamera, make_world_positions, world_width
from lan_server import LanServer, make_qr_png
from models import Player
from media_control import WindowsMediaPauser
from protocol import TurnActionGuard
from view_layout import DisplayLayout, sidebar_row_height


# ---------------------------------------------------------------------------
# Native-resolution drawing
# ---------------------------------------------------------------------------

_ORIGINAL_DRAW = pygame.draw
_RAW_BLIT = pygame.Surface.blit
_FONT_SPECS = {}
_SCALED_FONT_CACHE = {}
_SCALED_IMAGE_CACHE = OrderedDict()
_NEAREST_IMAGE_IDS = set()
_CANVAS_SCALE = (1.0, 1.0)
_GUI_SCALE = 1.0
_BUTTON_TEXTURE = None
_BACKGROUND_TEXTURE = None
_TEXTURE_REGION_CACHE = OrderedDict()
_BUTTON_FONT_CACHE = OrderedDict()
CARDBOARD_ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets", "Cardboard")

# Verified against the bundled 293-second studio recording. Parenthesized
# backing-vocal cues are timed at the sung word rather than the lyric line's
# opening syllable.
THUNDERSTRUCK_CUE_SECONDS = (
    29.020, 32.530, 36.210, 39.740, 43.480, 47.000, 50.680, 54.280,
    57.950, 61.440, 70.000, 77.000, 84.000, 92.000, 99.920, 109.680,
    160.050, 166.260, 167.700, 171.160, 222.780, 226.280, 228.670,
    233.320, 251.660, 253.940, 257.360, 259.170, 263.950, 264.360,
    268.780, 271.960, 274.960, 278.240, 281.140,
)
# Verified against the bundled 328-second Carlyle Fraser recording. Each cue
# is the start of a cumulative "With the ..." chain: the point at which the
# next player begins drinking until that verse reaches "valley-o".
RATTLIN_BOG_CUE_SECONDS = (
    16.240, 31.730, 47.760, 64.640, 82.940, 101.570, 121.410,
    142.050, 163.480, 185.630, 208.900, 232.700, 257.590, 282.770,
)
SONG_CUE_ANIMATION_MS = 900


def players_in_join_order(players):
    """Return a snapshot of the authoritative turn/join order."""
    return list(players)


def player_display_name(player):
    prefix = "Beer Bitch " if player.is_beer_bitch else ""
    return prefix + player.name


def _stroke_size(value, scale):
    return 0 if not value else max(1, round(value * scale))


class NativeSurface(pygame.Surface):
    """A native-pixel surface whose public drawing coordinates stay logical."""

    def __new__(cls, logical_size, scale_x, scale_y, flags=0, gui_scale=1.0):
        return super().__new__(cls)

    def __init__(self, logical_size, scale_x, scale_y, flags=0, gui_scale=1.0):
        logical_width, logical_height = logical_size
        native_size = (
            max(1, round(logical_width * scale_x)),
            max(1, round(logical_height * scale_y)),
        )
        super().__init__(native_size, flags, 32)
        self.logical_width = logical_width
        self.logical_height = logical_height
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.uniform_scale = min(scale_x, scale_y) * gui_scale

    def logical_point(self, point):
        return round(point[0] * self.scale_x), round(point[1] * self.scale_y)

    def logical_rect(self, rect):
        rect = pygame.Rect(rect)
        return pygame.Rect(
            round(rect.x * self.scale_x),
            round(rect.y * self.scale_y),
            max(1, round(rect.width * self.scale_x)),
            max(1, round(rect.height * self.scale_y)),
        )

    def blit(self, source, dest, area=None, special_flags=0):
        dest_rect = pygame.Rect(dest) if isinstance(dest, pygame.Rect) else None
        logical_dest = (dest_rect.x, dest_rect.y) if dest_rect else dest
        native_dest = self.logical_point(logical_dest)

        if isinstance(source, NativeSurface):
            native_area = source.logical_rect(area) if area is not None else None
            return _RAW_BLIT(self, source, native_dest, native_area, special_flags)

        if area is not None:
            source = source.subsurface(pygame.Rect(area))
        source_width, source_height = source.get_size()
        # Square assets are icons/tokens and must keep their aspect ratio. Other
        # temporary surfaces are layout regions and follow the responsive axes.
        if source_width == source_height:
            target_size = (
                max(1, round(source_width * self.uniform_scale)),
                max(1, round(source_height * self.uniform_scale)),
            )
        else:
            target_size = (
                max(1, round(source_width * self.scale_x)),
                max(1, round(source_height * self.scale_y)),
            )
        cache_key = None
        if source_width == source_height:
            cache_key = (id(source), source_width, source_height, target_size)
            cached = _SCALED_IMAGE_CACHE.get(cache_key)
            if cached is not None and cached[0] is source:
                scaled = cached[1]
                _SCALED_IMAGE_CACHE.move_to_end(cache_key)
            else:
                transform = pygame.transform.scale if id(source) in _NEAREST_IMAGE_IDS else pygame.transform.smoothscale
                scaled = transform(source, target_size)
                _SCALED_IMAGE_CACHE[cache_key] = (source, scaled)
                while len(_SCALED_IMAGE_CACHE) > 256:
                    _SCALED_IMAGE_CACHE.popitem(last=False)
        else:
            scaled = pygame.transform.smoothscale(source, target_size)
        return _RAW_BLIT(self, scaled, native_dest, None, special_flags)


class _NativeDraw:
    """Scale pygame's vector primitives when drawing on a NativeSurface."""

    def __init__(self, original):
        self.original = original

    @staticmethod
    def _native(surface):
        return isinstance(surface, NativeSurface)

    def rect(self, surface, color, rect, width=0, border_radius=-1,
             border_top_left_radius=-1, border_top_right_radius=-1,
             border_bottom_left_radius=-1, border_bottom_right_radius=-1):
        if not self._native(surface):
            return self.original.rect(surface, color, rect, width, border_radius,
                                      border_top_left_radius, border_top_right_radius,
                                      border_bottom_left_radius, border_bottom_right_radius)
        scale = surface.uniform_scale
        radius = lambda value: value if value < 0 else round(value * scale)
        return self.original.rect(
            surface, color, surface.logical_rect(rect), _stroke_size(width, scale),
            radius(border_radius), radius(border_top_left_radius),
            radius(border_top_right_radius), radius(border_bottom_left_radius),
            radius(border_bottom_right_radius),
        )

    def line(self, surface, color, start_pos, end_pos, width=1):
        if self._native(surface):
            return self.original.line(surface, color, surface.logical_point(start_pos),
                                      surface.logical_point(end_pos),
                                      max(1, round(width * surface.uniform_scale)))
        return self.original.line(surface, color, start_pos, end_pos, width)

    def lines(self, surface, color, closed, points, width=1):
        if self._native(surface):
            points = [surface.logical_point(point) for point in points]
            width = max(1, round(width * surface.uniform_scale))
        return self.original.lines(surface, color, closed, points, width)

    def polygon(self, surface, color, points, width=0):
        if self._native(surface):
            points = [surface.logical_point(point) for point in points]
            width = _stroke_size(width, surface.uniform_scale)
        return self.original.polygon(surface, color, points, width)

    def circle(self, surface, color, center, radius, width=0,
               draw_top_right=None, draw_top_left=None,
               draw_bottom_left=None, draw_bottom_right=None):
        if self._native(surface):
            center = surface.logical_point(center)
            radius = max(1, round(radius * surface.uniform_scale))
            width = _stroke_size(width, surface.uniform_scale)
        args = [surface, color, center, radius, width]
        if draw_top_right is not None:
            args.extend((draw_top_right, draw_top_left, draw_bottom_left, draw_bottom_right))
        return self.original.circle(*args)

    def ellipse(self, surface, color, rect, width=0):
        if self._native(surface):
            rect = surface.logical_rect(rect)
            width = _stroke_size(width, surface.uniform_scale)
        return self.original.ellipse(surface, color, rect, width)

    def arc(self, surface, color, rect, start_angle, stop_angle, width=1):
        if self._native(surface):
            rect = surface.logical_rect(rect)
            width = max(1, round(width * surface.uniform_scale))
        return self.original.arc(surface, color, rect, start_angle, stop_angle, width)

    def __getattr__(self, name):
        return getattr(self.original, name)


pygame.draw = _NativeDraw(_ORIGINAL_DRAW)


def _new_native_surface(logical_size, flags=0):
    return NativeSurface(logical_size, _CANVAS_SCALE[0], _CANVAS_SCALE[1],
                         flags, _GUI_SCALE)

# ---------------------------------------------------------------------------
# Token image generation & loading (Multi-resolution .ico and .png support)
# ---------------------------------------------------------------------------

from PIL import Image
from token_generator import generate_all_tokens, render_token_image


def _gen_token_surface(name: str, size: int = 64) -> pygame.Surface:
    img = render_token_image(name, size=size)
    return pygame.image.frombytes(img.tobytes(), (size, size), "RGBA")


def _gen_pizza(size=64):  return _gen_token_surface("pizza", size)
def _gen_beer(size=64):   return _gen_token_surface("beer", size)
def _gen_dice(size=64):   return _gen_token_surface("dice", size)
def _gen_cup(size=64):    return _gen_token_surface("cup", size)
def _gen_star(size=64):   return _gen_token_surface("star", size)
def _gen_nerf(size=64):   return _gen_token_surface("nerf", size)
def _gen_lion(size=64):   return _gen_token_surface("lion", size)
def _gen_ducky(size=64):  return _gen_token_surface("ducky", size)
def _gen_plane(size=64):  return _gen_token_surface("plane", size)
def _gen_spoon(size=64):  return _gen_token_surface("spoon", size)
def _gen_cactus(size=64): return _gen_token_surface("cactus", size)
def _gen_crown(size=64):  return _gen_token_surface("crown", size)
def _gen_taco(size=64):   return _gen_token_surface("taco", size)

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
    """Generate default token ICO and PNG files if they don't already exist."""
    default_dir = os.path.join(TOKENS_DIR, "default")
    os.makedirs(default_dir, exist_ok=True)
    os.makedirs(os.path.join(TOKENS_DIR, "custom"), exist_ok=True)
    missing = False
    for name in DEFAULT_TOKENS:
        ico_file = os.path.join(default_dir, f"{name}.ico")
        png_file = os.path.join(default_dir, f"{name}.png")
        if not os.path.exists(ico_file) or not os.path.exists(png_file):
            missing = True
            break
    if missing:
        generate_all_tokens(default_dir)


def load_token_surface(path: str, target_size: tuple[int, int] = (64, 64)) -> pygame.Surface:
    """Load token surface with multi-resolution quality from .ico or .png."""
    if not os.path.exists(path):
        base, _ = os.path.splitext(path)
        for ext in (".ico", ".png", ".jpg", ".jpeg"):
            if os.path.exists(base + ext):
                path = base + ext
                break
    if os.path.exists(path):
        if path.lower().endswith(".ico"):
            try:
                with Image.open(path) as img:
                    if hasattr(img, "ico") and hasattr(img.ico, "sizes"):
                        available = img.ico.sizes()
                        if target_size in available:
                            img.size = target_size
                        elif (256, 256) in available:
                            img.size = (256, 256)
                    converted = img.convert("RGBA")
                    if converted.size != target_size:
                        converted = converted.resize(target_size, Image.Resampling.LANCZOS)
                    return pygame.image.frombytes(converted.tobytes(), converted.size, "RGBA")
            except Exception:
                pass
        try:
            img = pygame.image.load(path).convert_alpha()
            if img.get_size() != target_size:
                img = pygame.transform.smoothscale(img, target_size)
            return img
        except Exception:
            try:
                with Image.open(path) as img:
                    converted = img.convert("RGBA")
                    if converted.size != target_size:
                        converted = converted.resize(target_size, Image.Resampling.LANCZOS)
                    return pygame.image.frombytes(converted.tobytes(), converted.size, "RGBA")
            except Exception:
                pass
    raise FileNotFoundError(f"Could not load token surface from {path}")


def load_token_surfaces() -> dict:
    """Load all token images as 64x64 pygame Surfaces with high resolution."""
    surfaces = {}
    for name, path in ALL_TOKENS.items():
        try:
            surfaces[name] = load_token_surface(path, (64, 64))
        except Exception:
            surfaces[name] = _gen_token_surface(name, size=64)
    return surfaces


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_text(surf, text, font, color, x, y, align="center"):
    render_font = font
    if isinstance(surf, NativeSurface):
        spec = _FONT_SPECS.get(id(font))
        if spec:
            name, size, bold = spec
            native_size = max(1, round(size * surf.uniform_scale))
            key = (name, native_size, bold)
            render_font = _SCALED_FONT_CACHE.get(key)
            if render_font is None:
                try:
                    render_font = pygame.font.SysFont(name, native_size, bold=bold)
                except Exception:
                    render_font = pygame.font.Font(None, native_size)
                _SCALED_FONT_CACHE[key] = render_font
    rendered = render_font.render(str(text), True, color)
    rect = rendered.get_rect()
    if isinstance(surf, NativeSurface):
        x, y = surf.logical_point((x, y))
    if align == "center":
        rect.center = (x, y)
    elif align == "left":
        rect.midleft = (x, y)
    elif align == "right":
        rect.midright = (x, y)
    if isinstance(surf, NativeSurface):
        _RAW_BLIT(surf, rendered, rect)
    else:
        surf.blit(rendered, rect)


def draw_outlined_text(surf, text, font, color, outline_color, x, y, align="center"):
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
        draw_text(surf, text, font, outline_color, x + dx, y + dy, align)
    draw_text(surf, text, font, color, x, y, align)


def draw_rounded_rect(surf, color, rect, radius=10, border=0, border_color=(0, 0, 0)):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def _texture_region(texture, size, radius=0, wash=None):
    """Return a cached, center-cropped texture with optional rounded clipping."""
    width, height = max(1, int(size[0])), max(1, int(size[1]))
    key = (id(texture), width, height, radius, wash)
    cached = _TEXTURE_REGION_CACHE.get(key)
    if cached is not None:
        _TEXTURE_REGION_CACHE.move_to_end(key)
        return cached

    source_w, source_h = texture.get_size()
    scale = max(width / source_w, height / source_h)
    scaled_size = (max(width, round(source_w * scale)),
                   max(height, round(source_h * scale)))
    scaled = pygame.transform.smoothscale(texture, scaled_size)
    x = (scaled_size[0] - width) // 2
    y = (scaled_size[1] - height) // 2
    region = scaled.subsurface((x, y, width, height)).copy().convert_alpha()

    if wash:
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill(wash)
        region.blit(overlay, (0, 0))
    if radius:
        mask = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(mask, WHITE, mask.get_rect(), border_radius=radius)
        region.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    _TEXTURE_REGION_CACHE[key] = region
    while len(_TEXTURE_REGION_CACHE) > 128:
        _TEXTURE_REGION_CACHE.popitem(last=False)
    return region


def draw_textured_rect(surf, texture, rect, radius=10, border=0,
                       border_color=MARKER, wash=None):
    rect = pygame.Rect(rect)
    if texture is None:
        draw_rounded_rect(surf, CARDBOARD, rect, radius, border, border_color)
        return
    surf.blit(_texture_region(texture, rect.size, radius, wash), rect.topleft)
    if border:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def draw_textured_circle(surf, texture, center, radius, tint):
    """Draw a cardboard disc with a translucent color wash."""
    diameter = radius * 2
    texture_disc = _texture_region(
        texture, (diameter, diameter), radius, (*tint, 112)
    )
    surf.blit(texture_disc, (center[0] - radius, center[1] - radius))


def draw_panel(surf, color, rect, radius=10, border=0, border_color=MARKER):
    """Draw a cardboard2-backed container while retaining its original accent."""
    wash = (*color, 24)
    draw_textured_rect(surf, _BACKGROUND_TEXTURE, rect, radius, border,
                       border_color, wash)


def centered_popup(width, height, margin=32):
    """Clamp a requested popup size to the viewport and center it."""
    width = max(1, min(round(width), SCREEN_W - margin * 2))
    height = max(1, min(round(height), SCREEN_H - margin * 2))
    return pygame.Rect((SCREEN_W - width) // 2, (SCREEN_H - height) // 2,
                       width, height)


def wrap_text(text, font, max_width):
    """Wrap text by measured pixel width, including overlong single words."""
    lines = []
    for paragraph in str(text).splitlines() or [""]:
        current = ""
        for word in paragraph.split() or [""]:
            candidate = (current + " " + word).strip()
            if not current or font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            lines.append(current)
            current = word
            while current and font.size(current)[0] > max_width:
                cut = len(current)
                while cut > 1 and font.size(current[:cut])[0] > max_width:
                    cut -= 1
                lines.append(current[:cut])
                current = current[cut:]
        lines.append(current)
    return lines or [""]


def _fit_button_label(label, font, max_width, max_height):
    """Shrink from the supplied font's size and ellipsize as a last resort."""
    label = str(label)
    spec = _FONT_SPECS.get(id(font))
    if not spec or (font.size(label)[0] <= max_width and font.get_height() <= max_height):
        return label, font
    name, maximum_size, bold = spec
    cache_key = (name, maximum_size, bold, label, max_width, max_height)
    cached = _BUTTON_FONT_CACHE.get(cache_key)
    if cached is not None:
        _BUTTON_FONT_CACHE.move_to_end(cache_key)
        return cached

    fitted = font
    for size in range(maximum_size - 1, 8, -1):
        fitted = pygame.font.SysFont(name, size, bold=bold)
        _FONT_SPECS[id(fitted)] = (name, size, bold)
        if fitted.size(label)[0] <= max_width and fitted.get_height() <= max_height:
            result = (label, fitted)
            break
    else:
        display = label
        while display and fitted.size(display + "…")[0] > max_width:
            display = display[:-1]
        result = ((display + "…") if display != label else display, fitted)

    _BUTTON_FONT_CACHE[cache_key] = result
    while len(_BUTTON_FONT_CACHE) > 256:
        _BUTTON_FONT_CACHE.popitem(last=False)
    return result


def draw_button(surf, rect, label, font, bg, fg, border_color=MARKER, radius=10, border=3):
    # Existing fill colors become semantic border cues around cardboard1.
    rect = pygame.Rect(rect)
    accent = border_color if bg == CARDBOARD_DARK and border_color != MARKER else bg
    draw_textured_rect(surf, _BUTTON_TEXTURE, rect, radius, border, accent,
                       (255, 246, 222, 18))
    if border and accent != MARKER:
        inner = pygame.Rect(rect).inflate(-border * 2, -border * 2)
        pygame.draw.rect(surf, MARKER, inner, 1,
                         border_radius=max(0, radius - border))
    label, fitted_font = _fit_button_label(label, font,
                                            max(1, rect.w - 16),
                                            max(1, rect.h - 10))
    draw_text(surf, label, fitted_font, MARKER, rect.centerx, rect.centery)


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


# ---------------------------------------------------------------------------
# Main Game class
# ---------------------------------------------------------------------------

class Game:

    def __init__(self):
        self.lan_server = LanServer(token_names=TOKEN_NAMES)
        self.lan_error = ""
        self.lan_join_url = ""
        self.lan_qr = None
        try:
            self.lan_server.start()
            self.lan_join_url = self.lan_server.join_url
        except (RuntimeError, TimeoutError) as exc:
            self.lan_error = str(exc)
        pygame.init()
        pygame.display.set_caption("Pizza Box Party!")
        self.settings = load_settings()
        self.settings_draft = replace(self.settings)
        self.settings_error = ""
        self._settings_confirmation = None
        self.window = None
        self.screen = None
        self._apply_display_settings(initial=True)
        if self.lan_join_url:
            try:
                raw_qr = pygame.image.load(io.BytesIO(make_qr_png(self.lan_join_url))).convert()
                self.lan_qr = pygame.transform.scale(raw_qr, (112, 112))
                _NEAREST_IMAGE_IDS.add(id(self.lan_qr))
            except (pygame.error, ValueError) as exc:
                self.lan_error = f"QR unavailable; use the join URL. {exc}"
        self.clock  = pygame.time.Clock()
        self.media_pauser = WindowsMediaPauser()
        self.song_channel = None

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
        global _BUTTON_TEXTURE, _BACKGROUND_TEXTURE
        _BUTTON_TEXTURE = pygame.image.load(
            os.path.join(CARDBOARD_ASSET_DIR, "cardboard1.png")
        ).convert()
        _BACKGROUND_TEXTURE = pygame.image.load(
            os.path.join(CARDBOARD_ASSET_DIR, "cardboard2.jpg")
        ).convert()
        _TEXTURE_REGION_CACHE.clear()
        ensure_token_images()
        self.token_surfs = load_token_surfaces()  # {name: Surface 64x64}

        # Scaled-down token surfaces for board (38x38) and player panels (40x40)
        self.token_board  = {n: pygame.transform.smoothscale(s, (38, 38))
                             for n, s in self.token_surfs.items()}
        self.token_lead   = {n: pygame.transform.smoothscale(s, (40, 40))
                             for n, s in self.token_surfs.items()}

        # Game state
        self.state = "menu"
        self.menu_subtitle = random.choice(MENU_SUBTITLES)

        # Board creator state (initialized when opened from the menu)
        self.board_draft = None
        self.creator_selected = 0
        self.creator_space_scroll = 0
        self.creator_option_scroll = 0
        self.creator_dropdown_open = False
        self.creator_active_field = None
        self.creator_error = ""
        self.creator_confirm_cancel = False

        # Setup screen state
        self.lobby_setup_players = []
        self._setup_remove_btns = []

        # Board selection
        self.boards, self.board_warnings = scan_boards()
        self.selected_board_idx = 0
        # Active board data (replaced each game start from JSON)
        self.board_spaces  = BOARD_SPACES
        self.finish_index  = FINISH_INDEX
        self.board_name    = "Classic Pizza Box"

        # Game state
        self.players       = []
        self.rules         = RulesEngine(self.players, self.finish_index)
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
        self.board_surf    = None   # native viewport cache for the scrolling board
        self._board_bg     = None
        self._board_camera_x = None
        self.world_width   = BOARD_W
        self.camera        = HorizontalCamera(BOARD_W, BOARD_W)
        self._last_turn_broadcast = None
        self._last_game_broadcast = None
        self._disconnect_pause_player_id = None
        self.turn_id        = 1
        self.action_guard   = TurnActionGuard()
        self.current_prompt = None
        self._last_prompt_broadcast = None
        self.hot_seat = None
        self._hot_seat_sent_prompts = set()
        self._last_hot_seat_broadcast = None
        self.song_event = None
        self.jfk_event = None
        self.chug_speak = None
        self.lap_event = None
        self._song_skip_btn = None
        self._hot_seat_host_btns = []

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
        self.mates = self.rules.mates

        # House rules added via the New Rule tile
        self.house_rules   = []
        self.rule_announcement = None
        self.rule_announcement_remaining_ms = 0

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
        self._pause_skip_btn = None
        self._pause_remove_btn = None
        self._pause_correct_btn = None
        self._pause_menu_btn = None
        self.correcting_drinks = False
        self.removing_player = False
        self.correction_player_idx = 0
        self._correction_btns = []
        self._removal_btns = []

        # Start/settings screen click targets.
        self._settings_btn = None
        self._settings_controls = {}
        self._settings_apply_btn = None
        self._settings_reset_btn = None
        self._settings_back_btn = None
        self._settings_keep_btn = None
        self._settings_revert_btn = None

        # Sidebar button rects (computed relative to screen)
        roll_w, roll_h = 270, 58
        roll_x = SIDEBAR_X + (SIDEBAR_W - roll_w) // 2
        self.roll_btn = pygame.Rect(roll_x, 210, roll_w, roll_h)

    def _desktop_sizes(self):
        try:
            sizes = pygame.display.get_desktop_sizes()
        except pygame.error:
            sizes = []
        return sizes or [(SCREEN_W, SCREEN_H)]

    def _available_resolutions(self, display_index=None):
        desktops = self._desktop_sizes()
        index = self.settings_draft.display_index if display_index is None else display_index
        index = max(0, min(len(desktops) - 1, index))
        try:
            modes = pygame.display.list_modes(display=index)
        except (pygame.error, TypeError):
            modes = []
        if modes == -1 or not modes:
            modes = [desktops[index]]
        modes = {tuple(mode) for mode in modes if mode[0] >= 800 and mode[1] >= 600}
        modes.add(tuple(desktops[index]))
        return sorted(modes, key=lambda size: (size[0] * size[1], size[0]), reverse=True)

    def _normalized_display_settings(self, settings):
        normalized = AppSettings.from_mapping(settings.__dict__)
        desktops = self._desktop_sizes()
        normalized.display_index = max(0, min(len(desktops) - 1, normalized.display_index))
        available = self._available_resolutions(normalized.display_index)
        if normalized.display_mode == "borderless":
            normalized.resolution = None
        elif normalized.display_mode == "fullscreen" and normalized.resolution not in available:
            normalized.resolution = None
        elif normalized.display_mode == "windowed" and normalized.resolution is not None:
            desktop = desktops[normalized.display_index]
            normalized.resolution = (
                max(800, min(desktop[0], normalized.resolution[0])),
                max(600, min(desktop[1], normalized.resolution[1])),
            )
        return normalized

    def _apply_display_settings(self, initial=False):
        """Create the requested display and rebuild every resolution-bound cache."""
        requested = self._normalized_display_settings(self.settings)
        desktops = self._desktop_sizes()
        desktop = desktops[requested.display_index]
        if requested.display_mode == "borderless":
            size, flags = desktop, pygame.NOFRAME
            requested.resolution = None
        elif requested.display_mode == "windowed":
            size = requested.resolution or (min(1280, desktop[0]), min(800, desktop[1]))
            flags = pygame.RESIZABLE
        else:
            size = requested.resolution or desktop
            flags = pygame.FULLSCREEN
        try:
            self.window = pygame.display.set_mode(size, flags, display=requested.display_index)
        except (pygame.error, TypeError) as exc:
            if not initial:
                self.settings_error = f"Display change failed: {exc}"
                return False
            requested = AppSettings(gui_scale=requested.gui_scale,
                                    game_volume=requested.game_volume,
                                    muted=requested.muted)
            self.window = pygame.display.set_mode(desktops[0], pygame.NOFRAME, display=0)
        self.settings = requested
        self._rebuild_render_targets()
        self._apply_audio_settings()
        self.settings_error = ""
        return True

    def _rebuild_render_targets(self):
        self._compute_present_rect()
        global _CANVAS_SCALE, _GUI_SCALE
        _CANVAS_SCALE = (self.display_layout.scale_x, self.display_layout.scale_y)
        _GUI_SCALE = self.settings.gui_scale
        self.screen = _new_native_surface((SCREEN_W, SCREEN_H))
        _SCALED_FONT_CACHE.clear()
        _SCALED_IMAGE_CACHE.clear()
        _BUTTON_FONT_CACHE.clear()
        if hasattr(self, "_menu_bg"):
            del self._menu_bg
        if hasattr(self, "_board_bg"):
            self._board_bg = None
        if hasattr(self, "board_surf"):
            self.board_surf = None
            self._board_camera_x = None

    def _compute_present_rect(self):
        ww, wh = self.window.get_size()
        self.display_layout = DisplayLayout.from_window(ww, wh, self.settings.gui_scale)
        self.present_scale = self.display_layout.uniform_scale
        self.present_w = self.display_layout.viewport_width
        self.present_h = self.display_layout.viewport_height
        self.present_ox = self.display_layout.viewport_x
        self.present_oy = self.display_layout.viewport_y
        self.present_rect = pygame.Rect(self.display_layout.viewport)

    def _effective_volume(self):
        settings = getattr(self, "settings", None) or AppSettings()
        return 0.0 if settings.muted else settings.game_volume

    def _apply_audio_settings(self):
        channel = getattr(self, "song_channel", None)
        if channel is not None:
            channel.set_volume(self._effective_volume())

    def _window_to_logical(self, pos):
        return self.display_layout.window_to_design(pos)

    def _map_event_to_logical(self, e):
        if e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            lp = self._window_to_logical(e.pos)
            if lp is None:
                return None
            d = dict(e.dict)
            d["pos"] = lp
            return pygame.event.Event(e.type, d)
        if e.type == pygame.MOUSEMOTION:
            lp = self._window_to_logical(e.pos)
            if lp is None:
                return None
            d = dict(e.dict)
            d["pos"] = lp
            return pygame.event.Event(e.type, d)
        return e

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _font(name: str, size: int, bold=False) -> pygame.font.Font:
        try:
            font = pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            font = pygame.font.Font(None, size)
        _FONT_SPECS[id(font)] = (name, size, bold)
        return font

    def add_message(self, msg: str):
        self.messages.insert(0, {
            "text": msg,
            "ts": pygame.time.get_ticks(),
        })
        if len(self.messages) > 4:
            self.messages = self.messages[:4]

    def _give_sips(self, player, n, _propagate=True):
        """Give sips to player; also propagates once to their mate if paired."""
        self.rules.give_sips(player, n, group=not _propagate)

    def _give_shot(self, player, _propagate=True):
        """Give a shot to player; also propagates once to their mate if paired."""
        self.rules.give_shots(player, group=not _propagate)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        while True:
            raw_events = pygame.event.get()
            events = []
            for e in raw_events:
                if (e.type == pygame.VIDEORESIZE
                        and self.settings.display_mode == "windowed"):
                    self.settings.resolution = (max(800, e.w), max(600, e.h))
                    self.window = pygame.display.set_mode(
                        self.settings.resolution, pygame.RESIZABLE,
                        display=self.settings.display_index)
                    self._rebuild_render_targets()
                    save_settings(self.settings)
                    continue
                mapped = self._map_event_to_logical(e)
                if mapped is not None:
                    events.append(mapped)

            for e in events:
                if e.type == pygame.QUIT:
                    self._shutdown()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    if self.state == "game":
                        if self.show_rules:
                            self.show_rules = False
                        elif self.correcting_drinks:
                            self.correcting_drinks = False
                        elif self.removing_player:
                            self.removing_player = False
                        elif self.paused:
                            self.paused = False
                        else:
                            self.paused = True
                    elif self.state == "settings":
                        if self._settings_confirmation:
                            self._revert_display_settings()
                        else:
                            self.settings_draft = replace(self.settings)
                            self.state = "menu"
                    elif self.state == "board_creator":
                        self._request_creator_cancel()
                    else:
                        self._shutdown()

            self._update_settings_confirmation()

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
            elif self.state == "settings":
                self.handle_settings(events)
                self.draw_settings()
            elif self.state == "board_creator":
                self.handle_board_creator(events)
                self.draw_board_creator()

            # The viewport is already rendered at native resolution.
            self.window.fill(BLACK)
            self.window.blit(self.screen, (self.present_ox, self.present_oy))
            pygame.display.flip()
            self.clock.tick(FPS)

    def _shutdown(self):
        self._stop_song_audio(resume_media=True)
        self.lan_server.stop()
        pygame.quit()
        raise SystemExit

    # ------------------------------------------------------------------
    # MENU
    # ------------------------------------------------------------------

    def handle_menu(self, events):
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self._play_btn.collidepoint(e.pos):
                    self.lan_server.lobby.return_to_lobby()
                    self.lan_server.publish(self.lan_server.lobby.public_state())
                    self.state = "setup"
                elif self._create_board_btn.collidepoint(e.pos):
                    self._begin_board_creator()
                elif self._settings_btn.collidepoint(e.pos):
                    self.settings_draft = replace(self.settings)
                    self.settings_error = ""
                    self.state = "settings"
                elif self._quit_btn.collidepoint(e.pos):
                    self._shutdown()

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
        play_r = pygame.Rect(SCREEN_W // 2 - 140, 310, 280, 58)
        create_r = pygame.Rect(SCREEN_W // 2 - 140, 382, 280, 58)
        settings_r = pygame.Rect(SCREEN_W // 2 - 140, 454, 280, 58)
        quit_r = pygame.Rect(SCREEN_W // 2 - 140, 526, 280, 58)
        self._play_btn = play_r
        self._create_board_btn = create_r
        self._settings_btn = settings_r
        self._quit_btn = quit_r

        draw_button(self.screen, play_r, "PLAY!", self.f_header,
                    (80, 170, 80), WHITE, MARKER, 12, 4)
        draw_button(self.screen, create_r, "Create Board", self.f_label,
                    (190, 120, 45), WHITE, MARKER, 12, 3)
        draw_button(self.screen, settings_r, "Settings", self.f_label,
                    CARDBOARD_DARK, WHITE, MARKER, 12, 3)
        draw_button(self.screen, quit_r, "Quit", self.f_body,
                    CARDBOARD_DARK, WHITE, MARKER, 12, 3)

        # Decorative doodles
        self._draw_menu_doodles()

    # ------------------------------------------------------------------
    # BOARD CREATOR
    # ------------------------------------------------------------------

    def _begin_board_creator(self):
        self.board_draft = BoardDraft.create_default()
        self.creator_selected = 0
        self.creator_space_scroll = 0
        self.creator_option_scroll = 0
        self.creator_dropdown_open = False
        self.creator_active_field = None
        self.creator_error = ""
        self.creator_confirm_cancel = False
        self.state = "board_creator"

    def _request_creator_cancel(self):
        if self.creator_confirm_cancel:
            self.creator_confirm_cancel = False
        elif self.board_draft is not None and self.board_draft.dirty:
            self.creator_confirm_cancel = True
            self.creator_active_field = None
            self.creator_dropdown_open = False
        else:
            self.state = "menu"

    def _creator_max_space_scroll(self):
        return max(0, len(self.board_draft.spaces) - 9)

    def _creator_keep_selected_visible(self):
        if self.creator_selected < self.creator_space_scroll:
            self.creator_space_scroll = self.creator_selected
        elif self.creator_selected >= self.creator_space_scroll + 9:
            self.creator_space_scroll = self.creator_selected - 8
        self.creator_space_scroll = max(
            0, min(self._creator_max_space_scroll(), self.creator_space_scroll)
        )

    def _creator_field_text(self, field):
        if field in ("name", "description"):
            return str(getattr(self.board_draft, field))
        return str(self.board_draft.spaces[self.creator_selected].get(field, ""))

    def _creator_set_field_text(self, field, text):
        if field in ("name", "description"):
            self.board_draft.set_metadata(field, text)
        elif field in ("value", "target"):
            self.board_draft.set_space_field(
                self.creator_selected, field, int(text) if text else ""
            )
        else:
            self.board_draft.set_space_field(self.creator_selected, field, text)
        self.creator_error = ""

    def _handle_creator_key(self, event):
        field = self.creator_active_field
        if field is None:
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            self.creator_active_field = None
            return
        value = self._creator_field_text(field)
        if event.key == pygame.K_BACKSPACE:
            self._creator_set_field_text(field, value[:-1])
            return
        character = getattr(event, "unicode", "")
        if not character or not character.isprintable():
            return
        if field in ("value", "target") and not character.isdigit():
            return
        limits = {
            "name": 60, "description": 160, "label": 80,
            "msg": 300, "value": 4, "target": 4,
        }
        if len(value) < limits[field]:
            self._creator_set_field_text(field, value + character)

    def _creator_select_option(self, option):
        try:
            self.board_draft.set_event(
                self.creator_selected, option.key, PARTY_SQUARE_COMPONENTS
            )
            self.creator_error = ""
        except BoardCreatorError as exc:
            self.creator_error = str(exc)
        self.creator_dropdown_open = False
        self.creator_active_field = None

    def _save_created_board(self):
        try:
            save_new_board(self.board_draft, BOARDS_DIR, validate_board_data)
        except BoardCreatorError as exc:
            self.creator_error = str(exc)
            return
        self.boards, self.board_warnings = scan_boards()
        self.selected_board_idx = min(self.selected_board_idx, max(0, len(self.boards) - 1))
        self.creator_confirm_cancel = False
        self.state = "menu"

    def handle_board_creator(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if not self.creator_confirm_cancel:
                    self._handle_creator_key(event)
                continue
            if event.type == pygame.MOUSEWHEEL and not self.creator_confirm_cancel:
                if self.creator_dropdown_open:
                    maximum = max(0, len(self._creator_options) - 8)
                    self.creator_option_scroll = max(
                        0, min(maximum, self.creator_option_scroll - event.y)
                    )
                else:
                    self.creator_space_scroll = max(
                        0, min(self._creator_max_space_scroll(),
                               self.creator_space_scroll - event.y)
                    )
                continue
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            if self.creator_confirm_cancel:
                if self._creator_discard_btn.collidepoint(event.pos):
                    self.creator_confirm_cancel = False
                    self.state = "menu"
                elif self._creator_keep_editing_btn.collidepoint(event.pos):
                    self.creator_confirm_cancel = False
                continue

            if self.creator_dropdown_open:
                for rect, option in self._creator_option_rects:
                    if rect.collidepoint(event.pos):
                        self._creator_select_option(option)
                        break
                else:
                    if not self._creator_dropdown_rect.collidepoint(event.pos):
                        self.creator_dropdown_open = False
                continue

            if self._creator_cancel_btn.collidepoint(event.pos):
                self._request_creator_cancel()
                continue
            if self._creator_save_btn.collidepoint(event.pos):
                self._save_created_board()
                continue
            if self._creator_add_btn.collidepoint(event.pos):
                self.creator_selected = self.board_draft.add_space()
                self._creator_keep_selected_visible()
                self.creator_error = ""
                continue
            if self._creator_remove_btn.collidepoint(event.pos):
                try:
                    self.creator_selected = self.board_draft.remove_space(
                        self.creator_selected
                    )
                    self._creator_keep_selected_visible()
                    self.creator_error = ""
                except BoardCreatorError as exc:
                    self.creator_error = str(exc)
                continue
            for rect, index in self._creator_space_rects:
                if rect.collidepoint(event.pos):
                    self.creator_selected = index
                    self.creator_active_field = None
                    self.creator_error = ""
                    break
            else:
                if self._creator_dropdown_rect.collidepoint(event.pos):
                    if 0 < self.creator_selected < len(self.board_draft.spaces) - 1:
                        self.creator_dropdown_open = True
                        current_key = event_key_for_space(
                            self.board_draft.spaces[self.creator_selected]
                        )
                        current_index = next(
                            (i for i, option in enumerate(self._creator_options)
                             if option.key == current_key), 0
                        )
                        self.creator_option_scroll = max(
                            0, min(current_index, len(self._creator_options) - 8)
                        )
                    continue
                for field, rect in self._creator_field_rects.items():
                    if rect.collidepoint(event.pos):
                        self.creator_active_field = field
                        break
                else:
                    self.creator_active_field = None

    def _creator_visible_text(self, text, font, width):
        text = str(text)
        while text and font.size(text)[0] > width:
            text = text[1:]
        return text

    def _draw_creator_field(self, label, field, rect, numeric=False):
        self._creator_field_rects[field] = rect
        draw_text(self.screen, label, self.f_small, MARKER_BROWN,
                  rect.x, rect.y - 12, align="left")
        border = BLUE if self.creator_active_field == field else MARKER_BROWN
        draw_panel(self.screen, WHITE, rect, 7, 3, border)
        value = self._creator_field_text(field)
        if self.creator_active_field == field:
            value += "|"
        visible = self._creator_visible_text(value, self.f_body, rect.w - 20)
        draw_text(self.screen, visible, self.f_body, MARKER,
                  rect.x + 10, rect.centery, align="left")
        if numeric and not value.rstrip("|"):
            draw_text(self.screen, "number", self.f_small, CARDBOARD_DARK,
                      rect.x + 10, rect.centery, align="left")

    def draw_board_creator(self):
        self.screen.blit(self._get_menu_bg(), (0, 0))
        draw_outlined_text(self.screen, "CREATE A BOARD", self.f_header,
                           YELLOW, MARKER_BROWN, SCREEN_W // 2, 34)
        self._creator_field_rects = {}
        self._creator_space_rects = []
        self._creator_option_rects = []
        self._creator_options = available_event_options(PARTY_SQUARE_COMPONENTS)

        self._draw_creator_field(
            "BOARD NAME", "name", pygame.Rect(175, 78, 390, 42)
        )
        self._draw_creator_field(
            "DESCRIPTION (OPTIONAL)", "description", pygame.Rect(690, 78, 510, 42)
        )

        left = pygame.Rect(32, 142, 355, 548)
        right = pygame.Rect(405, 142, 843, 548)
        draw_panel(self.screen, CARDBOARD_LITE, left, 12, 3, MARKER)
        draw_panel(self.screen, CARDBOARD_LITE, right, 12, 3, MARKER)
        draw_text(self.screen, f"SPACES ({len(self.board_draft.spaces)})",
                  self.f_label, MARKER_BROWN, left.centerx, 170)

        self._creator_keep_selected_visible()
        first = self.creator_space_scroll
        for row, index in enumerate(range(first, min(first + 9, len(self.board_draft.spaces)))):
            rect = pygame.Rect(left.x + 16, 194 + row * 45, left.w - 32, 38)
            self._creator_space_rects.append((rect, index))
            selected = index == self.creator_selected
            color = (235, 195, 95) if selected else CARDBOARD
            draw_panel(self.screen, color, rect, 7, 3 if selected else 1, MARKER_BROWN)
            space = self.board_draft.spaces[index]
            summary = f"{index}. {space.get('label', '')}"
            draw_text(self.screen,
                      self._creator_visible_text(summary, self.f_small, rect.w - 22),
                      self.f_small, MARKER, rect.x + 10, rect.centery, align="left")

        self._creator_add_btn = pygame.Rect(left.x + 16, left.bottom - 56, 154, 40)
        self._creator_remove_btn = pygame.Rect(left.x + 185, left.bottom - 56, 154, 40)
        draw_button(self.screen, self._creator_add_btn, "+ Add Space", self.f_small,
                    (80, 170, 80), WHITE, MARKER, 8, 2)
        removable = (len(self.board_draft.spaces) > 5 and
                     0 < self.creator_selected < len(self.board_draft.spaces) - 1)
        draw_button(self.screen, self._creator_remove_btn, "Remove", self.f_small,
                    (150, 70, 60) if removable else (130, 120, 100),
                    WHITE, MARKER, 8, 2)

        space = self.board_draft.spaces[self.creator_selected]
        draw_text(self.screen, f"EDIT SPACE {self.creator_selected}", self.f_label,
                  MARKER_BROWN, right.centerx, 174)
        self._draw_creator_field(
            "LABEL", "label", pygame.Rect(right.x + 36, 215, right.w - 72, 42)
        )

        locked = self.creator_selected in (0, len(self.board_draft.spaces) - 1)
        draw_text(self.screen, "EVENT", self.f_small, MARKER_BROWN,
                  right.x + 36, 285, align="left")
        self._creator_dropdown_rect = pygame.Rect(right.x + 36, 296, right.w - 72, 44)
        current_key = event_key_for_space(space)
        option = next((item for item in self._creator_options if item.key == current_key), None)
        event_label = ("Start (locked)" if self.creator_selected == 0 else
                       "Finish (locked)" if locked else
                       option.label if option else current_key)
        draw_button(self.screen, self._creator_dropdown_rect,
                    event_label + ("" if locked else "  v"), self.f_body,
                    (135, 125, 105) if locked else CARDBOARD_DARK,
                    WHITE, MARKER, 8, 2)

        if not locked and option:
            if option.value_field:
                self._draw_creator_field(
                    "POSITIVE NUMBER", "value",
                    pygame.Rect(right.x + 36, 385, 220, 42), numeric=True
                )
            elif option.target_field:
                self._draw_creator_field(
                    f"TARGET SPACE (0-{len(self.board_draft.spaces) - 1})", "target",
                    pygame.Rect(right.x + 36, 385, 220, 42), numeric=True
                )
            elif option.message_field:
                self._draw_creator_field(
                    "MESSAGE", "msg",
                    pygame.Rect(right.x + 36, 385, right.w - 72, 42)
                )
                draw_text(self.screen, "Use {name} for the player and {label} for this space.",
                          self.f_small, MARKER_BROWN, right.x + 36, 449, align="left")
            elif option.component:
                draw_text(self.screen,
                          "Registered event: its phone prompt and game behavior are automatic.",
                          self.f_small, MARKER_BROWN, right.x + 36, 390, align="left")
            else:
                draw_text(self.screen, "No additional settings for this event.",
                          self.f_small, MARKER_BROWN, right.x + 36, 390, align="left")

        self._creator_cancel_btn = pygame.Rect(390, 716, 210, 52)
        self._creator_save_btn = pygame.Rect(680, 716, 210, 52)
        draw_button(self.screen, self._creator_cancel_btn, "Cancel", self.f_body,
                    CARDBOARD_DARK, WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._creator_save_btn, "Save Board", self.f_label,
                    (80, 170, 80), WHITE, MARKER, 10, 3)
        if self.creator_error:
            draw_text(self.screen, self.creator_error[:115], self.f_small, RED,
                      SCREEN_W // 2, 696)

        if self.creator_dropdown_open:
            visible_options = self._creator_options[
                self.creator_option_scroll:self.creator_option_scroll + 8
            ]
            menu = pygame.Rect(self._creator_dropdown_rect.x,
                               self._creator_dropdown_rect.bottom,
                               self._creator_dropdown_rect.w,
                               len(visible_options) * 38 + 8)
            draw_panel(self.screen, CARDBOARD_LITE, menu, 7, 3, MARKER)
            for row, menu_option in enumerate(visible_options):
                rect = pygame.Rect(menu.x + 4, menu.y + 4 + row * 38,
                                   menu.w - 8, 36)
                self._creator_option_rects.append((rect, menu_option))
                selected = menu_option.key == current_key
                draw_panel(self.screen, (235, 195, 95) if selected else CARDBOARD,
                           rect, 4, 1, MARKER_BROWN)
                draw_text(self.screen, menu_option.label, self.f_small, MARKER,
                          rect.x + 10, rect.centery, align="left")

        if self.creator_confirm_cancel:
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 165))
            self.screen.blit(shade, (0, 0))
            popup = centered_popup(620, 250)
            draw_panel(self.screen, CARDBOARD_LITE, popup, 16, 4, MARKER)
            draw_text(self.screen, "Discard this unsaved board?", self.f_header,
                      MARKER_BROWN, popup.centerx, popup.y + 66)
            draw_text(self.screen, "Your draft will be lost.", self.f_body,
                      MARKER, popup.centerx, popup.y + 116)
            self._creator_keep_editing_btn = pygame.Rect(
                popup.x + 40, popup.bottom - 76, 245, 50
            )
            self._creator_discard_btn = pygame.Rect(
                popup.right - 285, popup.bottom - 76, 245, 50
            )
            draw_button(self.screen, self._creator_keep_editing_btn, "Keep Editing",
                        self.f_body, CARDBOARD_DARK, WHITE, MARKER, 9, 2)
            draw_button(self.screen, self._creator_discard_btn, "Discard",
                        self.f_body, (150, 70, 60), WHITE, MARKER, 9, 2)

    def _cycle_setting(self, key, direction):
        draft = self.settings_draft
        if key == "display_index":
            count = len(self._desktop_sizes())
            draft.display_index = (draft.display_index + direction) % count
            draft.resolution = None
        elif key == "display_mode":
            index = DISPLAY_MODES.index(draft.display_mode)
            draft.display_mode = DISPLAY_MODES[(index + direction) % len(DISPLAY_MODES)]
        elif key == "resolution":
            choices = [None] + self._available_resolutions(draft.display_index)
            current = draft.resolution if draft.resolution in choices else None
            draft.resolution = choices[(choices.index(current) + direction) % len(choices)]
        elif key == "gui_scale":
            current = min(GUI_SCALES, key=lambda value: abs(value - draft.gui_scale))
            index = GUI_SCALES.index(current)
            draft.gui_scale = GUI_SCALES[max(0, min(len(GUI_SCALES) - 1,
                                                   index + direction))]
        elif key == "game_volume":
            draft.game_volume = max(0.0, min(1.0,
                                             round(draft.game_volume + direction * 0.05, 2)))
        elif key == "muted":
            draft.muted = not draft.muted

    def _apply_settings_draft(self):
        previous = replace(self.settings)
        requested = replace(self.settings_draft)
        display_changed = (
            previous.display_mode, previous.display_index, previous.resolution
        ) != (
            requested.display_mode, requested.display_index, requested.resolution
        )
        self.settings = requested
        if not self._apply_display_settings():
            self.settings = previous
            self._apply_display_settings(initial=True)
            return
        self.settings_draft = replace(self.settings)
        if display_changed:
            self._settings_confirmation = {
                "previous": previous,
                "deadline": pygame.time.get_ticks() + 10_000,
            }
        else:
            save_settings(self.settings)

    def _keep_display_settings(self):
        save_settings(self.settings)
        self.settings_draft = replace(self.settings)
        self._settings_confirmation = None

    def _revert_display_settings(self):
        confirmation = self._settings_confirmation
        if confirmation is None:
            return
        self.settings = replace(confirmation["previous"])
        self._settings_confirmation = None
        self._apply_display_settings(initial=True)
        self.settings_draft = replace(self.settings)

    def _update_settings_confirmation(self):
        confirmation = self._settings_confirmation
        if confirmation and pygame.time.get_ticks() >= confirmation["deadline"]:
            self._revert_display_settings()

    def handle_settings(self, events):
        for event in events:
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue
            if self._settings_confirmation:
                if self._settings_keep_btn and self._settings_keep_btn.collidepoint(event.pos):
                    self._keep_display_settings()
                elif self._settings_revert_btn and self._settings_revert_btn.collidepoint(event.pos):
                    self._revert_display_settings()
                continue
            for key, (minus, plus) in self._settings_controls.items():
                if minus.collidepoint(event.pos):
                    self._cycle_setting(key, -1)
                    break
                if plus.collidepoint(event.pos):
                    self._cycle_setting(key, 1)
                    break
            else:
                if self._settings_apply_btn.collidepoint(event.pos):
                    self._apply_settings_draft()
                elif self._settings_reset_btn.collidepoint(event.pos):
                    self.settings_draft = AppSettings()
                elif self._settings_back_btn.collidepoint(event.pos):
                    self.settings_draft = replace(self.settings)
                    self.state = "menu"

    def draw_settings(self):
        self.screen.blit(self._get_menu_bg(), (0, 0))
        panel = pygame.Rect(120, 55, SCREEN_W - 240, 690)
        draw_panel(self.screen, CARDBOARD_LITE, panel, 16, 4, MARKER)
        draw_text(self.screen, "SETTINGS", self.f_header, MARKER_BROWN,
                  panel.centerx, 92)

        desktops = self._desktop_sizes()
        draft = self.settings_draft
        resolution = ("Desktop / Auto" if draft.resolution is None else
                      f"{draft.resolution[0]} × {draft.resolution[1]}")
        mode_names = {
            "borderless": "Borderless Desktop",
            "windowed": "Resizable Window",
            "fullscreen": "Exclusive Fullscreen",
        }
        rows = [
            ("display_index", "Monitor", f"Monitor {draft.display_index + 1}  "
             f"({desktops[min(draft.display_index, len(desktops) - 1)][0]} × "
             f"{desktops[min(draft.display_index, len(desktops) - 1)][1]})"),
            ("display_mode", "Display mode", mode_names[draft.display_mode]),
            ("resolution", "Resolution",
             "Desktop / Auto" if draft.display_mode == "borderless" else resolution),
            ("gui_scale", "GUI scale", f"{round(draft.gui_scale * 100)}%"),
            ("game_volume", "Game audio", f"{round(draft.game_volume * 100)}%"),
            ("muted", "Mute", "ON" if draft.muted else "OFF"),
        ]
        self._settings_controls = {}
        for index, (key, label, value) in enumerate(rows):
            y = 150 + index * 76
            draw_text(self.screen, label, self.f_label, MARKER_BROWN, 250, y,
                      align="left")
            minus = pygame.Rect(690, y - 25, 56, 50)
            plus = pygame.Rect(1034, y - 25, 56, 50)
            disabled = key == "resolution" and draft.display_mode == "borderless"
            button_color = (145, 130, 105) if disabled else CARDBOARD_DARK
            draw_button(self.screen, minus, "-", self.f_header, button_color,
                        WHITE, MARKER, 8, 2)
            draw_button(self.screen, plus, "+", self.f_header, button_color,
                        WHITE, MARKER, 8, 2)
            draw_text(self.screen, value, self.f_body, MARKER, 890, y)
            if not disabled:
                self._settings_controls[key] = (minus, plus)

        self._settings_apply_btn = pygame.Rect(285, 655, 210, 55)
        self._settings_reset_btn = pygame.Rect(535, 655, 210, 55)
        self._settings_back_btn = pygame.Rect(785, 655, 210, 55)
        draw_button(self.screen, self._settings_apply_btn, "Apply", self.f_label,
                    (80, 170, 80), WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._settings_reset_btn, "Reset Defaults", self.f_body,
                    CARDBOARD_DARK, WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._settings_back_btn, "Back", self.f_body,
                    CARDBOARD_DARK, WHITE, MARKER, 10, 3)
        if self.settings_error:
            draw_text(self.screen, self.settings_error[:100], self.f_small, RED,
                      panel.centerx, 730)

        if self._settings_confirmation:
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 165))
            self.screen.blit(shade, (0, 0))
            remaining = max(0, (self._settings_confirmation["deadline"] -
                                pygame.time.get_ticks() + 999) // 1000)
            title = "Keep these display settings?"
            detail = f"Reverting automatically in {remaining}s"
            content_w = max(self.f_header.size(title)[0], self.f_body.size(detail)[0], 440)
            confirm = centered_popup(content_w + 80,
                                     self.f_header.get_height() +
                                     self.f_body.get_height() + 150)
            draw_panel(self.screen, CARDBOARD_LITE, confirm, 16, 4, MARKER)
            draw_text(self.screen, "Keep these display settings?", self.f_header,
                      MARKER_BROWN, confirm.centerx, confirm.y + 58)
            draw_text(self.screen, detail, self.f_body, MARKER,
                      confirm.centerx, confirm.y + 110)
            button_w = (confirm.w - 120) // 2
            button_y = confirm.bottom - 78
            self._settings_keep_btn = pygame.Rect(confirm.x + 40, button_y, button_w, 58)
            self._settings_revert_btn = pygame.Rect(confirm.right - 40 - button_w,
                                                     button_y, button_w, 58)
            draw_button(self.screen, self._settings_keep_btn, "Keep", self.f_label,
                        (80, 170, 80), WHITE, MARKER, 10, 3)
            draw_button(self.screen, self._settings_revert_btn, "Revert", self.f_label,
                        (150, 70, 60), WHITE, MARKER, 10, 3)

    def _get_menu_bg(self) -> pygame.Surface:
        if not hasattr(self, "_menu_bg"):
            self._menu_bg = _new_native_surface((SCREEN_W, SCREEN_H))
            draw_textured_rect(self._menu_bg, _BACKGROUND_TEXTURE,
                               (0, 0, SCREEN_W, SCREEN_H), 0)
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
        self._sync_lobby_setup()
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self._back_btn.collidepoint(e.pos):
                    self.state = "menu"
                    return
                if self._start_btn.collidepoint(e.pos):
                    if self.lan_server.lobby.public_state()["can_start"]:
                        self.lan_server.lobby.start()
                        self._start_game()
                    return
                if self.boards and hasattr(self, "_board_left_btn"):
                    if self._board_left_btn.collidepoint(e.pos):
                        self.selected_board_idx = (self.selected_board_idx - 1) % len(self.boards)
                        return
                    if self._board_right_btn.collidepoint(e.pos):
                        self.selected_board_idx = (self.selected_board_idx + 1) % len(self.boards)
                        return
                for btn, player_id in self._setup_remove_btns:
                    if btn.collidepoint(e.pos):
                        self.lan_server.remove_lobby_player(player_id)
                        self._sync_lobby_setup()
                        return

    def _two_col(self) -> bool:
        """Use two-column layout when more than 7 players."""
        return len(self.lobby_setup_players) > 7

    def _sync_lobby_setup(self):
        """Mirror authoritative phone joins into the existing setup view."""
        lobby_players = self.lan_server.lobby.public_state()["players"]
        self.lobby_setup_players = lobby_players

    def _setup_row_rects(self, i):
        """Return the roster card and remove-button rect for a joined player."""
        if self._two_col():
            col      = i % 2           # fill both columns row by row
            row      = i // 2
            col_x    = 36 if col == 0 else 646
            y        = 250 + row * 48
            card_r   = pygame.Rect(col_x, y, 598, 42)
        else:
            y        = 250 + i * 52
            card_r   = pygame.Rect(250, y, 780, 46)
        remove_r = pygame.Rect(card_r.right - 104, card_r.y + 5, 92, card_r.h - 10)
        return card_r, remove_r

    def draw_setup(self):
        self._sync_lobby_setup()
        self.screen.blit(self._get_menu_bg(), (0, 0))

        draw_outlined_text(self.screen, "PLAYER SETUP",
                           self.f_header, YELLOW, MARKER_BROWN,
                           SCREEN_W // 2, 38)

        # Large board selector
        if self.boards:
            brd = self.boards[self.selected_board_idx]
            bl_r = pygame.Rect(42, 78, 64, 92)
            br_r = pygame.Rect(814, 78, 64, 92)
            bn_r = pygame.Rect(116, 78, 688, 92)
            self._board_left_btn  = bl_r
            self._board_right_btn = br_r
            draw_button(self.screen, bl_r, "<", self.f_header,
                        CARDBOARD_DARK, WHITE, MARKER, 10, 3)
            draw_button(self.screen, br_r, ">", self.f_header,
                        CARDBOARD_DARK, WHITE, MARKER, 10, 3)
            draw_panel(self.screen, CARDBOARD_LITE, bn_r, 10, 3, MARKER)
            draw_text(self.screen, "CHOOSE BOARD", self.f_tiny, MARKER_BROWN,
                      bn_r.centerx, bn_r.y + 15)
            draw_text(self.screen, brd["name"][:42], self.f_label, MARKER,
                      bn_r.centerx, bn_r.y + 43)
            draw_text(self.screen, brd["description"][:76], self.f_small, MARKER_BROWN,
                      bn_r.centerx, bn_r.y + 68)
            draw_text(self.screen, f"{self.selected_board_idx + 1} of {len(self.boards)}",
                      self.f_tiny, MARKER_BROWN, bn_r.right - 42, bn_r.y + 15)
        if self.board_warnings:
            warning = f"Board warning: {self.board_warnings[0]}"
            draw_text(self.screen, warning[:92], self.f_tiny, RED,
                      460, 188)
        if self.lan_error:
            draw_text(self.screen, self.lan_error[:110], self.f_tiny, RED,
                      460, 208)
        elif self.lan_join_url:
            # draw_text(self.screen, "SCAN TO JOIN", self.f_label, MARKER,
            #           1064, 70)
            if self.lan_qr:
                qr_rect = self.lan_qr.get_rect(center=(1064, 132))
                self.screen.blit(self.lan_qr, qr_rect)
                # draw_text(self.screen, self.lan_server.identity.code, self.f_label,
                #           MARKER, qr_rect.centerx, qr_rect.bottom + 13)
            # draw_text(self.screen, self.lan_join_url[:58], self.f_tiny,
            #           MARKER_BROWN, 1064, 212)

        two_col     = self._two_col()
        count = len(self.lobby_setup_players)
        draw_text(self.screen, f"PHONE PLAYERS ({count}/{MAX_PLAYERS})", self.f_label,
                  MARKER, SCREEN_W // 2, 226)
        self._setup_remove_btns = []
        if not self.lobby_setup_players:
            draw_text(self.screen, "No players yet — scan the QR code with a phone to join.",
                      self.f_body, MARKER_BROWN, SCREEN_W // 2, 330)
        for i, player in enumerate(self.lobby_setup_players):
            card_r, remove_r = self._setup_row_rects(i)
            draw_panel(self.screen, CARDBOARD_LITE, card_r, 8, 2, MARKER_BROWN)
            token_size = 32 if two_col else 36
            token = self.token_surfs.get(player["token_name"])
            if token:
                token = pygame.transform.smoothscale(token, (token_size, token_size))
                self.screen.blit(token, (card_r.x + 10, card_r.centery - token_size // 2))
            pygame.draw.circle(self.screen, GREEN if player["connected"] else RED,
                               (card_r.x + 58, card_r.centery), 6)
            name_font = self.f_small if two_col else self.f_body
            draw_text(self.screen, player["name"], name_font, MARKER,
                      card_r.x + 74, card_r.centery - (7 if not two_col else 0), align="left")
            if not two_col:
                draw_text(self.screen, player["token_name"], self.f_tiny, MARKER_BROWN,
                          card_r.x + 74, card_r.centery + 12, align="left")
            draw_button(self.screen, remove_r, "Remove", self.f_tiny,
                        (150, 70, 60), WHITE, MARKER, 7, 2)
            self._setup_remove_btns.append((remove_r, player["player_id"]))

        # Bottom buttons
        back_r  = pygame.Rect(80,  SCREEN_H - 68, 150, 48)
        start_r = pygame.Rect(SCREEN_W // 2 - 155, SCREEN_H - 68, 310, 48)
        self._back_btn  = back_r
        self._start_btn = start_r

        draw_button(self.screen, back_r, "< Back", self.f_body,
                    CARDBOARD_DARK, WHITE, MARKER, 10, 3)
        draw_button(self.screen, start_r, "START GAME!", self.f_header,
                    (80, 170, 80) if self.lan_server.lobby.public_state()["can_start"] else (115, 105, 90),
                    WHITE, MARKER, 12, 4)

    # ------------------------------------------------------------------
    # Game startup
    # ------------------------------------------------------------------

    def _randomize_board_layout(self) -> None:
        """Give the active board a fresh variable-length world layout."""
        positions = make_world_positions(len(self.board_spaces))
        for space, position in zip(self.board_spaces, positions):
            space["pos"] = position
        self.world_width = world_width(positions)
        self.camera = HorizontalCamera(BOARD_W, self.world_width)
        self.camera.snap(positions[0][0])
        self._board_camera_x = None

    def _start_game(self):
        self.players = []
        for lobby_player in self.lan_server.lobby.players:
            img = self.token_surfs.get(lobby_player.token_name, list(self.token_surfs.values())[0])
            player = Player(lobby_player.name, lobby_player.token_name, img)
            player.player_id = lobby_player.player_id
            player.connected = lobby_player.connected
            self.players.append(player)

        # Load selected board from JSON (falls back to built-in if no boards found)
        if self.boards:
            brd = self.boards[self.selected_board_idx]
            self.board_spaces, self.finish_index, self.board_name = load_board(brd["path"])
        else:
            self.board_spaces = BOARD_SPACES
            self.finish_index = FINISH_INDEX
            self.board_name   = "Classic Pizza Box"

        self.rules         = RulesEngine(self.players, self.finish_index)
        self.mates         = self.rules.mates
        self.current_idx   = 0
        self.phase         = "wait_roll"
        self.messages      = []
        self.winner        = None
        self.display_die   = 1
        self.last_effect   = None
        self.pending_interactive = None
        self.house_rules   = []
        self.rule_announcement = None
        self.rule_announcement_remaining_ms = 0
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
        self.correcting_drinks = False
        self.removing_player = False
        self._randomize_board_layout()
        self._last_turn_broadcast = None
        self._last_game_broadcast = None
        self._disconnect_pause_player_id = None
        self.turn_id        = 1
        self.action_guard.reset()
        self.current_prompt = None
        self._last_prompt_broadcast = None
        self.hot_seat = None
        self._hot_seat_sent_prompts = set()
        self._last_hot_seat_broadcast = None
        self.song_event = None
        self.jfk_event = None
        self.chug_speak = None
        self.lap_event = None
        self.board_surf    = self._render_board()
        self.add_message("Roll to start! Good luck!")
        self.state         = "game"

    # ------------------------------------------------------------------
    # GAME — update
    # ------------------------------------------------------------------

    def update_game(self):
        now = pygame.time.get_ticks()

        self.camera.update(self.clock.get_time() / 1000.0, paused=self.paused)
        self._sync_player_connections()
        self._consume_controller_actions()
        self._broadcast_turn_state()
        self._broadcast_game_state()
        self._broadcast_phone_prompt()
        self._broadcast_hot_seat()
        if self.paused:
            return

        if self.phase == "rule_announcement":
            self._update_rule_announcement(self.clock.get_time())
            return

        if self.phase in ("song_countdown", "song_playing"):
            self._update_song_event(now)
            return

        if self.phase == "jfk_countdown":
            self._update_jfk_event(self.clock.get_time())
            return

        if self.phase == "rolling":
            self.display_die = random.randint(1, 6)
            if now - self.roll_start >= self.roll_duration:
                self.die_value   = random.randint(1, 6)
                self.display_die = self.die_value
                self.lan_server.publish({
                    "type": "roll_result", "turn_id": self.turn_id,
                    "player_id": getattr(self.players[self.current_idx], "player_id", None),
                    "value": self.die_value,
                })
                current = self.players[self.current_idx]
                if current.whirlpool_position is not None:
                    self._resolve_whirlpool_roll(current, self.die_value, now)
                else:
                    self._start_move(current, self.die_value)

        elif self.phase == "moving":
            if now - self.anim_step_start >= self.anim_step_dur and self.camera.settled:
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
                    self.camera.focus(self.board_spaces[self.anim_to_pos]["pos"][0])

                else:
                    # Final hop done — resolve the space
                    landed_player = self.anim_player
                    # A normal landing must leave movement. Forced movement
                    # effects explicitly put the game back into this phase.
                    self.anim_player = None
                    self.phase = "resolving"
                    msg = self._resolve_space(landed_player, self.die_value)
                    self.add_message(msg)
                    if landed_player.finished:
                        self.winner = landed_player
                    if self.phase != "moving":
                        self.resolve_start = now

        elif self.phase == "resolving":
            if now - self.resolve_start >= self.resolve_duration:
                if self.pending_interactive:
                    self.phase = self.pending_interactive
                    self.pending_interactive = None
                elif self.winner:
                    self.state = "end"
                    self.lan_server.publish({
                        "type": "game_end",
                        "winner": getattr(self.winner, "player_id", None),
                        "message": f"{self.winner.name} reached Finish and won!",
                    })
                else:
                    self._advance_turn()

    def _update_rule_announcement(self, elapsed_ms):
        """Count only visible, unpaused frame time toward the rule announcement."""
        self.rule_announcement_remaining_ms = max(
            0, self.rule_announcement_remaining_ms - max(0, elapsed_ms)
        )
        if self.rule_announcement_remaining_ms == 0:
            self.rule_announcement = None
            self._advance_turn()

    def _update_jfk_event(self, elapsed_ms):
        """Run JFK for ten visible seconds, without exposing a countdown."""
        if not self.jfk_event:
            return
        self.jfk_event["remaining_ms"] = max(
            0, self.jfk_event["remaining_ms"] - max(0, elapsed_ms)
        )
        if self.jfk_event["remaining_ms"]:
            return

        player = self.players[self.current_idx]
        eligible = [p for p in players_in_join_order(self.players) if p is not player]
        if not eligible:
            self.jfk_event = None
            self.phase = "resolving"
            self.resolve_start = pygame.time.get_ticks()
            return
        choices = [{"value": "random", "label": "Random"}]
        choices.extend(
            {"value": getattr(choice, "player_id", ""), "label": choice.name}
            for choice in eligible
        )
        self._set_phone_prompt(
            player,
            kind="player",
            text="Choose who was last to answer FDR.",
            resolution="jfk",
            choices=choices,
        )
        self.pending_interactive = None
        self.phase = "phone_prompt"

    def _consume_controller_actions(self):
        """Apply phone actions only after validating authoritative host state."""
        while not self.lan_server.incoming.empty():
            payload = self.lan_server.incoming.get_nowait()
            if payload.get("type") in ("join", "reconnect"):
                self._last_turn_broadcast = None
                self._last_prompt_broadcast = None
                self._hot_seat_sent_prompts.clear()
                self._last_hot_seat_broadcast = None
            if payload.get("type") == "connection_state":
                self._handle_connection_state(payload)
                continue
            if payload.get("type") == "event_response":
                self._consume_event_response(payload)
                continue
            if payload.get("type") != "roll" or not self.players:
                continue
            current = self.players[self.current_idx]
            valid = self.action_guard.accept_roll(
                player_id=payload.get("_player_id"),
                active_player_id=getattr(current, "player_id", None),
                submitted_turn=payload.get("turn_id"),
                current_turn=self.turn_id,
                can_roll=self.phase == "wait_roll" and self.camera.settled and not self.paused,
            )
            if valid:
                self.phase = "rolling"
                self.roll_start = pygame.time.get_ticks()

    def _set_phone_prompt(self, player, *, kind, text, resolution, choices=None,
                          **details):
        prompt_id = f"{self.turn_id}:{player.position}:{resolution}"
        self.current_prompt = {
            "prompt_id": prompt_id,
            "player_id": getattr(player, "player_id", None),
            "kind": kind,
            "text": text,
            "choices": choices or [],
            "resolution": resolution,
        }
        self.current_prompt.update(details)
        if kind == "text":
            self.current_prompt["max_length"] = 100
        self.pending_interactive = "phone_prompt"
        self._last_prompt_broadcast = None

    def _other_players(self, player):
        """Return selectable non-self players in stable public display order."""
        return [candidate for candidate in players_in_join_order(self.players)
                if candidate is not player]

    def _other_player_prompt_choices(self, player):
        choices = [{"value": "random", "label": "Random"}]
        choices.extend(
            {"value": getattr(candidate, "player_id", ""), "label": candidate.name}
            for candidate in self._other_players(player)
        )
        return choices

    def _resolve_other_player_choice(self, player, response):
        eligible = self._other_players(player)
        if str(response) == "random":
            return random.choice(eligible) if eligible else None
        return next(
            (candidate for candidate in eligible
             if getattr(candidate, "player_id", None) == str(response)),
            None,
        )

    def _broadcast_phone_prompt(self):
        if self.phase != "phone_prompt" or not self.current_prompt:
            return
        prompt = {key: value for key, value in self.current_prompt.items()
                  if key != "resolution"}
        signature = repr(prompt)
        if signature != self._last_prompt_broadcast:
            self._last_prompt_broadcast = signature
            self.lan_server.publish({"type": "event_prompt", **prompt})

    def _consume_event_response(self, payload):
        if self.phase == "hot_seat" and self.hot_seat:
            self._consume_hot_seat_response(payload)
            return
        prompt = self.current_prompt
        if self.phase != "phone_prompt" or not prompt:
            return
        response = payload.get("response")
        if prompt["kind"] in ("option", "player"):
            allowed = {str(choice["value"]) for choice in prompt["choices"]}
            if str(response) not in allowed:
                return
        elif prompt["kind"] == "confirmation" and response != "confirmed":
            return
        elif (prompt["kind"] == "timer"
              and response != prompt.get("timer_action")):
            return
        elif prompt["kind"] == "link" and response != "activated":
            return
        elif prompt["kind"] == "text" and len(str(response).strip()) > 100:
            return
        if not self.action_guard.accept_prompt(
                player_id=payload.get("_player_id"), owner_id=prompt["player_id"],
                submitted_turn=payload.get("turn_id"), current_turn=self.turn_id,
                prompt_id=payload.get("prompt_id"), current_prompt_id=prompt["prompt_id"]):
            return
        self._resolve_phone_prompt(prompt["resolution"], response)
        self.lan_server.publish({"type": "event_resolved", "turn_id": self.turn_id,
                                 "prompt_id": prompt["prompt_id"]})
        if self.current_prompt is prompt:
            self.current_prompt = None
            self._last_prompt_broadcast = None
            if self.phase != "rule_announcement":
                self.phase = "resolving"
                self.resolve_start = pygame.time.get_ticks()
        else:
            # A multi-stage event replaced the accepted prompt with its next
            # authoritative step. Keep that new prompt active for reconnects.
            self.pending_interactive = None
            self.phase = "phone_prompt"
            self._last_prompt_broadcast = None

    def _resolve_phone_prompt(self, resolution, response):
        player = self.players[self.current_idx]
        if resolution == "chicks_dicks":
            opposite_group = "guys" if str(response) == "girl" else "girls"
            self.add_message(
                f"Chicks / Dicks: {player.name} chose for themselves; "
                f"all {opposite_group} drink."
            )
        elif resolution == "androids_iphones":
            opposite_group = "Android users" if str(response) == "iphone" else "iPhone users"
            self.add_message(
                f"Droids / iPhones: {player.name} chose their own phone type; "
                f"all {opposite_group} drink."
            )
        elif resolution == "shotgun":
            self._give_shot(player)
        elif resolution == "karaoke":
            self._give_shot(player)
        elif resolution in ("thunderstruck", "rattlin_bog"):
            self.rules.give_group_shots()
        elif resolution == "double_or_single_shot":
            count = 2 if str(response) == "double" else 1
            for _ in range(count):
                self._give_shot(player)
            self.add_message(f"{player.name} chose {'Double' if count == 2 else 'Single'} Shot.")
        elif resolution in ("mate", "drunk_driving", "jfk"):
            selected = self._resolve_other_player_choice(player, response)
            if selected is None:
                return
            if resolution == "mate":
                self.rules.pair_mates(player, selected)
                self.add_message(f"{player.name} and {selected.name} are now Mates.")
            elif resolution == "drunk_driving":
                self._give_shot(selected, _propagate=False)
                self.add_message(f"Drunk Driving: {selected.name} takes the shot.")
            else:
                self._give_sips(selected, 1)
                self.add_message(f"JFK: {selected.name} was last to answer FDR and takes 1 sip.")
                self.jfk_event = None
        elif resolution == "gay_chicken_select":
            selected = self._resolve_other_player_choice(player, response)
            if selected is None:
                return
            pairing = f"GAY CHICKEN! {player.name} faces {selected.name}."
            self.last_effect = "custom"
            self.last_effect_msg = pairing
            self.add_message(pairing)
            self._set_phone_prompt(
                player,
                kind="confirmation",
                text=(f"Complete Gay Chicken with {selected.name}, then confirm "
                      "when the challenge is finished."),
                resolution="gay_chicken_complete",
            )
        elif resolution == "gay_chicken_complete":
            self.last_effect = "custom"
            self.add_message(f"Gay Chicken complete: {player.name} finished the challenge.")
        elif resolution in ("swap_pants_select", "serenade_select"):
            selected = self._resolve_other_player_choice(player, response)
            if selected is None:
                return
            if resolution == "swap_pants_select":
                title = "SWAP PANTS"
                instruction = f"Swap pants with {selected.name}, then confirm when finished."
                completion = "swap_pants_complete"
                confirm_label = "Pants Swapped"
            else:
                title = "SERENADE"
                instruction = f"Serenade {selected.name}, then confirm when finished."
                completion = "serenade_complete"
                confirm_label = "Serenade Complete"
            pairing = f"{title}! {player.name} is paired with {selected.name}."
            self.last_effect = "custom"
            self.last_effect_msg = pairing
            self.add_message(pairing)
            self._set_phone_prompt(
                player,
                kind="confirmation",
                text=instruction,
                resolution=completion,
                confirm_label=confirm_label,
            )
        elif resolution in ("swap_pants_complete", "serenade_complete"):
            event_name = "Swap Pants" if resolution == "swap_pants_complete" else "Serenade"
            self.last_effect = "custom"
            self.add_message(f"{event_name} complete: {player.name} finished the challenge.")
        elif resolution == "jig_dance":
            self.last_effect = "custom"
            self.add_message(f"Do a Jig / Dance complete: {player.name} finished.")
        elif resolution == "lap_start":
            started_at_ms = pygame.time.get_ticks()
            started_at_epoch_ms = int(time.time() * 1000)
            self.lap_event = {
                "player_id": getattr(player, "player_id", None),
                "started_at_ms": started_at_ms,
                "started_at_epoch_ms": started_at_epoch_ms,
            }
            self.last_effect = "custom"
            self.last_effect_msg = f"LAP! {player.name} is running; the stopwatch is live."
            self.add_message(self.last_effect_msg)
            self._set_phone_prompt(
                player,
                kind="timer",
                text="Stop the timer when you finish your lap.",
                resolution="lap_stop",
                timer_action="stopped",
                timer_label="Stop Lap Timer",
                timer_started_at_epoch_ms=started_at_epoch_ms,
            )
        elif resolution == "lap_stop":
            state = self.lap_event
            if not state or state["player_id"] != getattr(player, "player_id", None):
                return
            elapsed_ms = max(0, pygame.time.get_ticks() - state["started_at_ms"])
            elapsed_seconds = round(elapsed_ms / 1000, 2)
            state["elapsed_seconds"] = elapsed_seconds
            self.last_effect = "custom"
            self.last_effect_val = elapsed_seconds
            self.last_effect_msg = (
                f"LAP COMPLETE! {player.name} finished in {elapsed_seconds:.2f} seconds."
            )
            self.add_message(self.last_effect_msg)
            self._set_phone_prompt(
                player,
                kind="confirmation",
                text=(f"Your lap time is {elapsed_seconds:.2f} seconds. "
                      "Confirm to finish the event."),
                resolution="lap_complete",
                confirm_label="Confirm Lap",
            )
        elif resolution == "lap_complete":
            self.last_effect = "custom"
            self.add_message(f"Lap confirmed: {player.name}'s turn is complete.")
            self.lap_event = None
        elif resolution == "chug_speak_start":
            started_at_ms = pygame.time.get_ticks()
            started_at_epoch_ms = int(time.time() * 1000)
            self.chug_speak = {
                "player_id": getattr(player, "player_id", None),
                "started_at_ms": started_at_ms,
                "started_at_epoch_ms": started_at_epoch_ms,
            }
            self.last_effect = "custom"
            self.last_effect_msg = f"CHUG SPEAK! {player.name}'s chug timer is running."
            self.add_message(self.last_effect_msg)
            self._set_phone_prompt(
                player,
                kind="timer",
                text="Stop the timer the instant your chug is complete.",
                resolution="chug_speak_stop",
                timer_action="stopped",
                timer_label="Stop Chug Timer",
                timer_started_at_epoch_ms=started_at_epoch_ms,
            )
        elif resolution == "chug_speak_stop":
            state = self.chug_speak
            if not state or state["player_id"] != getattr(player, "player_id", None):
                return
            elapsed_ms = max(0, pygame.time.get_ticks() - state["started_at_ms"])
            elapsed_seconds = round(elapsed_ms / 1000, 2)
            self.last_effect = "custom"
            self.last_effect_val = elapsed_seconds
            self.last_effect_msg = (
                f"CHUG SPEAK! {player.name} chugged for {elapsed_seconds:.2f} seconds "
                f"and must speak for {elapsed_seconds:.2f} minutes."
            )
            self.add_message(self.last_effect_msg)
            self.chug_speak = None
        elif resolution == "email_professor":
            self.last_effect = "custom"
            self.add_message(f"Email a Professor complete: {player.name} confirmed it.")
        elif resolution == "call_parent":
            self.last_effect = "custom"
            self.add_message(f"Call a Parent complete: {player.name} confirmed it.")
        elif resolution == "pikmin":
            self.last_effect = "custom"
            self.add_message(f"Pikmin opened: {player.name} activated the video link.")
        elif resolution == "specialty_shot":
            self._give_shot(player)
            self.last_effect = "custom"
            self.add_message(f"Specialty Shot complete: {player.name} takes 1 shot.")
        elif resolution == "new_rule":
            rule = str(response).strip()[:100]
            if rule:
                self.house_rules.append(rule)
                self.add_message(f"New Rule added: {rule}")
                self.last_effect = None
                self.rule_announcement = {"author": player.name, "text": rule}
                self.rule_announcement_remaining_ms = 5000
                self.phase = "rule_announcement"

    def _start_hot_seat(self, player):
        pending = {
            getattr(other, "player_id", None): other.name
            for other in self.players
            if other is not player and getattr(other, "player_id", None)
        }
        self.hot_seat = {
            "active_player_id": getattr(player, "player_id", None),
            "active_player_name": player.name,
            "stage": "collecting",
            "pending": pending,
            "questions": [],
            "question_index": 0,
        }
        self.pending_interactive = "hot_seat"
        self._hot_seat_sent_prompts.clear()
        self._last_hot_seat_broadcast = None

    def _hot_seat_prompt(self, owner_id, action, index=None):
        suffix = owner_id if index is None else str(index)
        return f"{self.turn_id}:hot-seat:{action}:{suffix}"

    def _publish_hot_seat_prompt(self, payload):
        prompt_id = payload["prompt_id"]
        if prompt_id not in self._hot_seat_sent_prompts:
            self._hot_seat_sent_prompts.add(prompt_id)
            self.lan_server.publish({"type": "event_prompt", **payload})

    def _broadcast_hot_seat(self):
        state = getattr(self, "hot_seat", None)
        if self.phase != "hot_seat" or not state:
            return
        if state["stage"] == "collecting":
            for owner_id, name in state["pending"].items():
                self._publish_hot_seat_prompt({
                    "prompt_id": self._hot_seat_prompt(owner_id, "ask"),
                    "player_id": owner_id,
                    "kind": "text",
                    "text": f"Write one Hot Seat question for {state['active_player_name']}.",
                    "max_length": 200,
                })
        elif state["stage"] == "answering":
            index = state["question_index"]
            question = state["questions"][index]
            self._publish_hot_seat_prompt({
                "prompt_id": self._hot_seat_prompt(state["active_player_id"], "answered", index),
                "player_id": state["active_player_id"],
                "kind": "confirmation",
                "text": f"{question['author']} asks: {question['text']}",
                "confirm_label": "Question Answered",
            })
        elif state["stage"] == "finish":
            self._publish_hot_seat_prompt({
                "prompt_id": self._hot_seat_prompt(state["active_player_id"], "finish"),
                "player_id": state["active_player_id"],
                "kind": "confirmation",
                "text": "Every Hot Seat question is answered.",
                "confirm_label": "Finish Hot Seat",
            })
        current = None
        if state["stage"] == "answering":
            current = state["questions"][state["question_index"]]
        public = {
            "type": "hot_seat_state", "turn_id": self.turn_id,
            "stage": state["stage"], "active_player_id": state["active_player_id"],
            "active_player_name": state["active_player_name"],
            "pending": list(state["pending"].values()),
            "pending_player_ids": list(state["pending"]),
            "received": len(state["questions"]), "current_question": current,
        }
        signature = repr(public)
        if signature != self._last_hot_seat_broadcast:
            self._last_hot_seat_broadcast = signature
            self.lan_server.publish(public)

    def _begin_hot_seat_questions(self):
        if not self.hot_seat:
            return
        for player_id in tuple(self.hot_seat["pending"]):
            self.lan_server.publish({
                "type": "event_resolved", "turn_id": self.turn_id,
                "prompt_id": self._hot_seat_prompt(player_id, "ask"),
                "player_id": player_id,
            })
        self.hot_seat["stage"] = "answering" if self.hot_seat["questions"] else "finish"
        self.hot_seat["pending"].clear()
        self._last_hot_seat_broadcast = None

    def _consume_hot_seat_response(self, payload):
        state = self.hot_seat
        player_id = payload.get("_player_id")
        prompt_id = str(payload.get("prompt_id", ""))
        response = payload.get("response")
        if state["stage"] == "collecting" and player_id in state["pending"]:
            expected = self._hot_seat_prompt(player_id, "ask")
            question = str(response).strip()
            if prompt_id != expected or not question or len(question) > 200:
                return
            if not self.action_guard.accept_prompt(
                    player_id=player_id, owner_id=player_id,
                    submitted_turn=payload.get("turn_id"), current_turn=self.turn_id,
                    prompt_id=prompt_id, current_prompt_id=expected):
                return
            author = state["pending"].pop(player_id)
            state["questions"].append({"author": author, "text": question})
            self.lan_server.publish({"type": "event_resolved", "turn_id": self.turn_id,
                                     "prompt_id": prompt_id, "player_id": player_id})
            if not state["pending"]:
                self._begin_hot_seat_questions()
        elif state["stage"] == "answering" and player_id == state["active_player_id"]:
            index = state["question_index"]
            expected = self._hot_seat_prompt(player_id, "answered", index)
            if prompt_id != expected or response != "confirmed":
                return
            if not self.action_guard.accept_prompt(
                    player_id=player_id, owner_id=player_id,
                    submitted_turn=payload.get("turn_id"), current_turn=self.turn_id,
                    prompt_id=prompt_id, current_prompt_id=expected):
                return
            self.lan_server.publish({"type": "event_resolved", "turn_id": self.turn_id,
                                     "prompt_id": prompt_id, "player_id": player_id})
            state["question_index"] += 1
            if state["question_index"] >= len(state["questions"]):
                state["stage"] = "finish"
        elif state["stage"] == "finish" and player_id == state["active_player_id"]:
            expected = self._hot_seat_prompt(player_id, "finish")
            if prompt_id != expected or response != "confirmed":
                return
            if not self.action_guard.accept_prompt(
                    player_id=player_id, owner_id=player_id,
                    submitted_turn=payload.get("turn_id"), current_turn=self.turn_id,
                    prompt_id=prompt_id, current_prompt_id=expected):
                return
            self.lan_server.publish({"type": "event_resolved", "turn_id": self.turn_id,
                                     "prompt_id": prompt_id, "player_id": player_id})
            self.hot_seat = None
            self.last_effect = None
            self.phase = "resolving"
            self.resolve_start = pygame.time.get_ticks()
        self._last_hot_seat_broadcast = None

    def _start_song_event(self, effect):
        songs = {
            "thunderstruck": ("THUNDERSTRUCK!", "Thunderstruck.mp3"),
            "rattlin_bog": ("RATTLIN' BOG!", "RattlinBog.mp3"),
        }
        title, filename = songs[effect]
        self.song_event = {
            "effect": effect, "title": title,
            "path": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "assets", "audio", filename),
            "countdown_start": None, "started_at": None,
            "duration_ms": 0, "result_applied": False,
            "cue_times_ms": [
                round(seconds * 1000)
                for seconds in (THUNDERSTRUCK_CUE_SECONDS
                                if effect == "thunderstruck"
                                else RATTLIN_BOG_CUE_SECONDS)
            ],
            "cue_label": "THUNDER" if effect == "thunderstruck" else "DRINK!",
            "next_cue_index": 0, "cue_animation_started_at": None,
        }
        self.pending_interactive = "song_countdown"
        if hasattr(self, "media_pauser"):
            if not self.media_pauser.available:
                self.add_message("Windows media control unavailable; pause Spotify manually.")
            self.media_pauser.pause_async()

    def _update_song_event(self, now):
        event = getattr(self, "song_event", None)
        if not event:
            return
        if self.phase == "song_countdown":
            if event["countdown_start"] is None:
                event["countdown_start"] = now
            if now - event["countdown_start"] >= 5000:
                try:
                    sound = pygame.mixer.Sound(event["path"])
                    sound.set_volume(self._effective_volume())
                    self.song_channel = sound.play()
                    if self.song_channel is None:
                        raise pygame.error("No audio channel is available")
                    self.song_channel.set_volume(self._effective_volume())
                    event["duration_ms"] = max(1, int(sound.get_length() * 1000))
                    event["started_at"] = now
                    self.phase = "song_playing"
                except (pygame.error, OSError) as exc:
                    self.add_message(f"Could not play {event['title']}: {exc}")
                    self._finish_song_event()
        elif self.phase == "song_playing":
            if self.song_channel is None or not self.song_channel.get_busy():
                self._finish_song_event()
                return
            elapsed = max(0, now - event["started_at"])
            cue_times = event["cue_times_ms"]
            animation_started = event["cue_animation_started_at"]
            if (animation_started is not None
                    and now - animation_started >= SONG_CUE_ANIMATION_MS):
                event["cue_animation_started_at"] = None
            # Start at most one cue animation per frame. If rendering stalls,
            # overdue cues remain queued and each still gets its own animation.
            if (event["cue_animation_started_at"] is None
                    and event["next_cue_index"] < len(cue_times)
                    and elapsed >= cue_times[event["next_cue_index"]]):
                event["cue_animation_started_at"] = now
                event["next_cue_index"] += 1

    def _stop_song_audio(self, resume_media=False):
        if getattr(self, "song_channel", None) is not None:
            self.song_channel.stop()
            self.song_channel = None
        if resume_media and hasattr(self, "media_pauser"):
            self.media_pauser.resume_async()

    def _finish_song_event(self):
        event = self.song_event
        if not event:
            return
        self._stop_song_audio(resume_media=True)
        if not event["result_applied"]:
            event["result_applied"] = True
            self.rules.give_group_shots()
            self.add_message(f"{event['title']} complete — everyone takes 1 shot!")
        self.song_event = None
        self.last_effect = None
        self.phase = "resolving"
        self.resolve_start = pygame.time.get_ticks()

    def _handle_connection_state(self, payload):
        """Pause an owned turn/prompt and restore it after reconnection."""
        player_id = payload.get("_player_id")
        player = next((p for p in self.players
                       if getattr(p, "player_id", None) == player_id), None)
        if player is None:
            return
        player.connected = bool(payload.get("connected"))
        self._last_game_broadcast = None
        current = self.players[self.current_idx] if self.players else None
        if not player.connected and player is current:
            if not self.paused:
                self.paused = True
                self._disconnect_pause_player_id = player_id
                self.add_message(f"Paused: {player.name} disconnected.")
                self.lan_server.publish({
                    "type": "pause",
                    "message": f"Waiting for {player.name} to reconnect.",
                })
        elif (player.connected and player_id == self._disconnect_pause_player_id):
            self.paused = False
            self._disconnect_pause_player_id = None
            self.add_message(f"{player.name} reconnected. Turn restored.")
            self._last_turn_broadcast = None

    def _broadcast_game_state(self):
        """Broadcast authoritative movement, drinks, and connection state."""
        players = [{
            "player_id": getattr(player, "player_id", None),
            "name": player.name,
            "token_name": player.token_name,
            "position": player.position,
            "shots": player.shots,
            "sips": player.sips,
            "connected": getattr(player, "connected", True),
            "finished": player.finished,
            "whirlpool_position": player.whirlpool_position,
            "is_beer_bitch": player.is_beer_bitch,
        } for player in players_in_join_order(self.players)]
        signature = tuple(tuple(sorted(item.items())) for item in players)
        if signature != self._last_game_broadcast:
            self._last_game_broadcast = signature
            self.lan_server.publish({"type": "room_state", "started": True,
                                     "players": players})

    def _broadcast_turn_state(self):
        if not self.players:
            return
        current = self.players[self.current_idx]
        payload = {
            "type": "turn_state",
            "active_player_id": getattr(current, "player_id", None),
            "turn_id": self.turn_id,
            "camera_settled": self.camera.settled,
            "can_roll": self.phase == "wait_roll" and self.camera.settled and not self.paused,
            "paused": self.paused,
        }
        signature = tuple(payload.items())
        if signature != self._last_turn_broadcast:
            self._last_turn_broadcast = signature
            self.lan_server.publish(payload)

    def _sync_player_connections(self):
        connected = {
            player["player_id"]: player["connected"]
            for player in self.lan_server.lobby.public_state()["players"]
        }
        for player in self.players:
            player.connected = connected.get(getattr(player, "player_id", None), True)

    def _start_move(self, player: Player, roll: int):
        """Kick off the one-space-at-a-time hop animation."""
        start = player.position
        steps = self.rules.movement_steps(player, roll)
        player.distance_traveled += len(steps)
        player.turns_taken += 1

        if not steps:
            self.phase = "resolving"
            self.resolve_start = pygame.time.get_ticks()
            return

        self.anim_player     = player
        self.anim_from_pos   = start
        self.anim_to_pos     = steps[0]
        self.anim_remaining  = steps[1:]
        self.anim_step_start = pygame.time.get_ticks()
        self.camera.focus(self.board_spaces[self.anim_to_pos]["pos"][0])
        self.phase = "moving"

    def _resolve_whirlpool_roll(self, player: Player, roll: int, now: int):
        """Apply a trapped player's normal-turn roll on the shared mini-board."""
        outcomes = {
            1: ("sips", 1),
            2: ("sips", 2),
            3: ("shots", 1),
            4: ("shots", 2),
            5: ("shots", 3),
        }
        self.last_effect = "custom"
        self.last_effect_val = roll
        if roll == 6:
            player.whirlpool_position = None
            self.last_effect_msg = f"WHIRLPOOL! {player.name} rolled 6 and escaped!"
        else:
            player.whirlpool_position = (player.whirlpool_position + roll) % 6
            drink_type, count = outcomes[roll]
            if drink_type == "sips":
                self._give_sips(player, count)
                unit = "sip" if count == 1 else "sips"
            else:
                for _ in range(count):
                    self._give_shot(player)
                unit = "shot" if count == 1 else "shots"
            self.last_effect_msg = (
                f"WHIRLPOOL! {player.name} rolled {roll} and takes {count} {unit}."
            )
        self.add_message(self.last_effect_msg)
        self.phase = "resolving"
        self.resolve_start = now

    def _start_forced_move(self, player: Player, target: int) -> None:
        """Animate any board-directed move through the normal hop/camera path."""
        steps = self.rules.movement_to(player, target)
        if not steps:
            self.phase = "resolving"
            return
        if target > player.position:
            player.distance_traveled += len(steps)
        else:
            player.backward_steps += len(steps)
        self.anim_player = player
        self.anim_from_pos = player.position
        self.anim_to_pos = steps[0]
        self.anim_remaining = steps[1:]
        self.anim_step_start = pygame.time.get_ticks()
        self.camera.focus(self.board_spaces[self.anim_to_pos]["pos"][0])
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
        if space.get("type") == "event" or effect not in ("none", "start", "finish", "sip", "shot", "everyone_sip", "back", "forward", "ladder"):
            player.events_landed += 1

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
            suffix = "s" if value > 1 else ""
            target = max(0, player.position - value)
            landed_label = self.board_spaces[target]["label"]
            self._start_forced_move(player, target)
            return intro + f"Landed on {label}. Slides back {value} space{suffix} to {landed_label}."

        if effect == "forward":
            target = min(self.finish_index, player.position + value)
            self._start_forced_move(player, target)
            return intro + f"Landed on {label}. Zooms forward {value}!"

        if effect == "ladder":
            target = space["target"]
            self._start_forced_move(player, target)
            return intro + f"Landed on {label}. Follow the ladder to {self.board_spaces[target]['label']}!"

        if effect == "skip":
            self.rules.add_skipped_turns(player, value)
            suffix = "s" if value != 1 else ""
            return intro + f"Landed on {label}. Skip {value} turn{suffix}!"

        if effect == "finish":
            player.finished  = True
            self.last_effect = "win"
            return intro + f"WINS at {label}!"

        # ------------------------------------------------------------------
        # PARTY EVENT COMPONENT EFFECTS
        # ------------------------------------------------------------------

        if effect == "longest_road":
            shot_count = random.randint(1, 5)
            for _ in range(shot_count):
                self._give_shot(player)
            suffix = "s" if shot_count != 1 else ""
            self.last_effect = "custom"
            self.last_effect_val = shot_count
            self.last_effect_msg = (
                f"LONGEST ROAD! {player.name} rolled {shot_count} and takes "
                f"{shot_count} shot{suffix}!"
            )
            return self.last_effect_msg

        if effect == "whirlpool":
            player.whirlpool_position = 0
            self.last_effect = "custom"
            self.last_effect_msg = (
                f"WHIRLPOOL! {player.name} is trapped until they roll a 6."
            )
            return self.last_effect_msg

        if effect == "beer_bitch":
            for candidate in self.players:
                candidate.is_beer_bitch = candidate is player
            self._last_game_broadcast = None
            self.last_effect = "custom"
            self.last_effect_msg = f"BEER BITCH! {player.name} now holds the role."
            return self.last_effect_msg

        if effect == "specialty_shot":
            eligible = self._other_players(player)
            if not eligible:
                self.last_effect = None
                return intro + "Specialty Shot needs another player, so the event was skipped."
            maker = random.choice(eligible)
            self._set_phone_prompt(
                player,
                kind="confirmation",
                text=(f"{maker.name} prepares your specialty shot. Confirm after "
                      "you take it."),
                resolution=effect,
                confirm_label="Shot Taken",
            )
            self.last_effect = "custom"
            self.last_effect_msg = (
                f"SPECIALTY SHOT! {maker.name} pours for {player.name}."
            )
            return self.last_effect_msg

        if effect in ("east_west", "younger_older"):
            if effect == "east_west":
                title = "EAST / WEST"
                result = random.choice(("East", "West"))
            else:
                title = "YOUNGER / OLDER"
                result = random.choice(("Younger", "Older"))
            self.last_effect = "custom"
            self.last_effect_msg = f"{title}! {result}"
            return self.last_effect_msg

        if effect == "jfk":
            eligible = [other for other in self.players if other is not player]
            if not eligible:
                self.last_effect = None
                return intro + "JFK needs another player, so the event was skipped."
            self.jfk_event = {
                "active_player_id": getattr(player, "player_id", None),
                "remaining_ms": 10000,
            }
            self.pending_interactive = "jfk_countdown"
            self.last_effect = "custom"
            self.last_effect_msg = "JFK! Everyone answer FDR — remember who answers last."
            return self.last_effect_msg

        if effect == "gay_chicken":
            if not self._other_players(player):
                self.last_effect = None
                return intro + "Gay Chicken needs another player, so the event was skipped."
            self._set_phone_prompt(
                player,
                kind="player",
                text="Choose your Gay Chicken opponent.",
                resolution="gay_chicken_select",
                choices=self._other_player_prompt_choices(player),
            )
            self.last_effect = "custom"
            self.last_effect_msg = (
                f"GAY CHICKEN! {player.name} is choosing an opponent."
            )
            return self.last_effect_msg

        if effect == "chug_speak":
            self.chug_speak = None
            self._set_phone_prompt(
                player,
                kind="timer",
                text="Start the timer when you begin chugging.",
                resolution="chug_speak_start",
                timer_action="started",
                timer_label="Start Chug Timer",
            )
            self.last_effect = "custom"
            self.last_effect_msg = (
                f"CHUG SPEAK! {player.name} is getting ready to time their chug."
            )
            return self.last_effect_msg

        if effect in ("email_professor", "call_parent"):
            if effect == "email_professor":
                public_instruction = f"EMAIL A PROFESSOR! {player.name} must send the email."
                private_instruction = (
                    "Email a professor yourself, then confirm after the email is sent."
                )
                confirm_label = "Email Sent"
            else:
                public_instruction = f"CALL A PARENT! {player.name} must make the call."
                private_instruction = (
                    "Call a parent yourself, then confirm after the call is complete."
                )
                confirm_label = "Call Complete"
            self._set_phone_prompt(
                player,
                kind="confirmation",
                text=private_instruction,
                resolution=effect,
                confirm_label=confirm_label,
            )
            self.last_effect = "custom"
            self.last_effect_msg = public_instruction
            return self.last_effect_msg

        if effect == "pikmin":
            self._set_phone_prompt(
                player,
                kind="link",
                text="Open the Pikmin video to complete this event.",
                resolution=effect,
                url="https://youtu.be/uEXP0iXGwRU",
                link_label="Open Pikmin Video",
            )
            self.last_effect = "custom"
            self.last_effect_msg = f"PIKMIN! {player.name} must open the video on their phone."
            return self.last_effect_msg

        if effect in ("swap_pants", "serenade"):
            if not self._other_players(player):
                self.last_effect = None
                label = "Swap Pants" if effect == "swap_pants" else "Serenade"
                return intro + f"{label} needs another player, so the event was skipped."
            if effect == "swap_pants":
                text = "Choose who will swap pants with you."
                public_title = "SWAP PANTS"
            else:
                text = "Choose who you will serenade."
                public_title = "SERENADE"
            self._set_phone_prompt(
                player,
                kind="player",
                text=text,
                resolution=f"{effect}_select",
                choices=self._other_player_prompt_choices(player),
            )
            self.last_effect = "custom"
            self.last_effect_msg = f"{public_title}! {player.name} is choosing someone."
            return self.last_effect_msg

        if effect == "jig_dance":
            variation = random.choice(("Do a Jig", "Dance"))
            self._set_phone_prompt(
                player,
                kind="confirmation",
                text=f"{variation}, then confirm when you are finished.",
                resolution=effect,
                confirm_label=f"{variation} Complete",
            )
            self.last_effect = "custom"
            self.last_effect_msg = f"{variation.upper()}! {player.name} must perform."
            return self.last_effect_msg

        if effect == "lap":
            self.lap_event = None
            self._set_phone_prompt(
                player,
                kind="timer",
                text="Start the stopwatch when you begin your lap.",
                resolution="lap_start",
                timer_action="started",
                timer_label="Start Lap Timer",
            )
            self.last_effect = "custom"
            self.last_effect_msg = f"LAP! {player.name} is preparing to run."
            return self.last_effect_msg

        if effect == "chicks_dicks":
            self._set_phone_prompt(
                player,
                kind="option",
                text=("Choose for yourself: are you a girl or a guy? "
                      "The opposite group will drink."),
                resolution=effect,
                choices=[
                    {"value": "girl", "label": "I'm a girl"},
                    {"value": "guy", "label": "I'm a guy"},
                ],
            )
            self.last_effect = "custom"
            self.last_effect_msg = (
                f"CHICKS / DICKS! {player.name} is privately choosing for themselves."
            )
            return intro + self.last_effect_msg

        if effect == "androids_iphones":
            self._set_phone_prompt(
                player,
                kind="option",
                text=("Choose for yourself: do you personally have an iPhone or "
                      "an Android? The opposite phone group will drink."),
                resolution=effect,
                choices=[
                    {"value": "iphone", "label": "I have an iPhone"},
                    {"value": "android", "label": "I have an Android"},
                ],
            )
            self.last_effect = "custom"
            self.last_effect_msg = (
                f"DROIDS / iPHONES! {player.name} is privately choosing their own phone type."
            )
            return intro + self.last_effect_msg

        if effect == "shotgun":
            self._set_phone_prompt(player, kind="confirmation",
                                   text="Confirm when your shotgun is complete.", resolution=effect)
            self.last_effect = "custom"
            self.last_effect_msg = f"SHOTGUN! {player.name} shotguns a drink."
            return self.last_effect_msg

        if effect == "double_or_single_shot":
            self._set_phone_prompt(player, kind="option",
                                   text="Choose Single Shot or Double Shot.", resolution=effect,
                                   choices=[{"value": "single", "label": "Single Shot"},
                                            {"value": "double", "label": "Double Shot"}])
            self.last_effect     = "custom"
            self.last_effect_msg = f"{player.name} must choose: Single or Double Shot!"
            return self.last_effect_msg

        if effect == "karaoke":
            self._set_phone_prompt(player, kind="confirmation",
                                   text="Sing a verse, then confirm when complete.", resolution=effect)
            self.last_effect = "custom"
            self.last_effect_msg = (
                f"KARAOKE! {player.name} must sing a verse of any song. "
                "Counts as 1 shot!"
            )
            return self.last_effect_msg

        if effect in ("thunderstruck", "rattlin_bog"):
            song = "Thunderstruck — AC/DC" if effect == "thunderstruck" else "Rattlin' Bog"
            self._start_song_event(effect)
            self.last_effect = "custom"
            self.last_effect_msg = (
                f"{song}! Get ready — the song starts after the countdown. "
                "EVERYONE takes 1 shot when it ends!"
            )
            return self.last_effect_msg

        if effect == "mate":
            choices = self._other_players(player)
            if not choices:
                self.last_effect = None
                return intro + "No available player to pair as Mate."
            self._set_phone_prompt(player, kind="player", text="Choose your Mate.",
                                   resolution=effect,
                                   choices=self._other_player_prompt_choices(player))
            self.last_effect     = "custom"
            self.last_effect_msg = (
                f"MATE! {player.name} picks someone to link with. "
                "Whenever either drinks, BOTH drink for the rest of the game!"
            )
            return self.last_effect_msg

        if effect == "hot_seat":
            self._start_hot_seat(player)
            self.last_effect     = "custom"
            self.last_effect_msg = (
                f"{player.name} is in the HOT SEAT! "
                "No drinks — the group gets to ask anything they want."
            )
            return self.last_effect_msg

        if effect == "drunk_driving":
            choices = self._other_players(player)
            if not choices:
                self.last_effect = None
                return intro + "No available player can lose Drunk Driving."
            self._set_phone_prompt(player, kind="player",
                                   text="Choose who lost Drunk Driving.", resolution=effect,
                                   choices=self._other_player_prompt_choices(player))
            self.last_effect     = "custom"
            self.last_effect_msg = (
                "DRUNK DRIVING! The group picks one player. "
                "They take 1 shot."
            )
            return self.last_effect_msg

        if effect == "new_rule":
            self._set_phone_prompt(player, kind="text",
                                   text="Write a new house rule (100 characters maximum).",
                                   resolution=effect)
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
            self._set_phone_prompt(player, kind="confirmation", text=full_msg,
                                   resolution="custom")
            self.last_effect_msg = full_msg
            return full_msg

        # ------------------------------------------------------------------
        # NONE / NORMAL — nothing happens
        # ------------------------------------------------------------------

        self.last_effect = None
        return intro + f"Landed on {label}."

    def _advance_turn(self):
        self.current_idx, skipped = self.rules.advance_turn(self.current_idx)
        self.turn_id += 1
        for player in skipped:
            self.add_message(f"{player.name} skips this turn.")
        self.phase = "wait_roll"
        self.camera.focus(self.board_spaces[self.players[self.current_idx].position]["pos"][0])

    # ------------------------------------------------------------------
    # GAME — input
    # ------------------------------------------------------------------

    def handle_game(self, events):
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.paused:
                    if self.show_rules:
                        self.show_rules = False
                        return
                    if self.correcting_drinks:
                        for btn, action in self._correction_btns:
                            if btn.collidepoint(e.pos):
                                self._apply_drink_correction(action)
                                return
                        return
                    if self.removing_player:
                        for btn, player in self._removal_btns:
                            if btn.collidepoint(e.pos):
                                if player is None:
                                    self.removing_player = False
                                else:
                                    self._remove_player(player)
                                return
                        return
                    if self._pause_resume_btn and self._pause_resume_btn.collidepoint(e.pos):
                        current = self.players[self.current_idx]
                        if getattr(current, "connected", True):
                            self.paused = False
                            self._disconnect_pause_player_id = None
                        return
                    if self._pause_rules_btn and self._pause_rules_btn.collidepoint(e.pos):
                        self.show_rules = True
                        return
                    if self._pause_quit_btn and self._pause_quit_btn.collidepoint(e.pos):
                        self._end_game_early()
                        return
                    if self._pause_skip_btn and self._pause_skip_btn.collidepoint(e.pos):
                        self._skip_disconnected_player()
                        return
                    if self._pause_remove_btn and self._pause_remove_btn.collidepoint(e.pos):
                        if len(self.players) > 2:
                            self.removing_player = True
                        return
                    if self._pause_correct_btn and self._pause_correct_btn.collidepoint(e.pos):
                        self.correcting_drinks = True
                        self.correction_player_idx = min(self.current_idx, len(self.players) - 1)
                        return
                    if self._pause_menu_btn and self._pause_menu_btn.collidepoint(e.pos):
                        self._return_to_main_menu()
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

                if self.phase == "hot_seat":
                    for btn, action in self._hot_seat_host_btns:
                        if btn.collidepoint(e.pos):
                            self._handle_hot_seat_host_action(action)
                            return

                if (self.phase in ("song_countdown", "song_playing")
                        and self._song_skip_btn and self._song_skip_btn.collidepoint(e.pos)):
                    self._finish_song_event()
                    return

                if (self.phase == "wait_roll"
                        and not self.paused
                        and self.camera.settled
                        and self.roll_btn.collidepoint(e.pos)):
                    self._skip_current_player()

    def _skip_current_player(self):
        """Host recovery action; the shared display never submits die rolls."""
        if not self.players or self.phase != "wait_roll":
            return
        current = self.players[self.current_idx]
        self.add_message(f"Host skipped {current.name}.")
        self._advance_turn()

    def _skip_disconnected_player(self):
        current = self.players[self.current_idx]
        if getattr(current, "connected", True):
            return
        self.add_message(f"Host skipped disconnected player {current.name}.")
        self._disconnect_pause_player_id = None
        self.current_prompt = None
        self._last_prompt_broadcast = None
        self.hot_seat = None
        self._hot_seat_sent_prompts.clear()
        self._stop_song_audio(resume_media=True)
        self.song_event = None
        self.jfk_event = None
        self.chug_speak = None
        self.lap_event = None
        self.pending_interactive = None
        self.paused = False
        self._advance_turn()

    def _remove_player(self, player):
        if player not in self.players or len(self.players) <= 2:
            return
        removed_name = player.name
        player_id = getattr(player, "player_id", None)
        self.current_idx = self.rules.remove_player(player, self.current_idx)
        if player_id:
            try:
                self.lan_server.lobby.remove(player_id, during_game=True)
            except Exception:
                pass
            self.lan_server.publish({
                "type": "player_removed",
                "player_id": player_id,
                "message": "The host removed you from the game.",
            })
        self.pick_choices = [p for p in self.pick_choices if p is not player]
        self.pick_source = None if self.pick_source is player else self.pick_source
        self.option_source = None if self.option_source is player else self.option_source
        self.anim_player = None
        self.anim_remaining = []
        self.pending_interactive = None
        self.current_prompt = None
        self._last_prompt_broadcast = None
        self.hot_seat = None
        self._hot_seat_sent_prompts.clear()
        self._stop_song_audio(resume_media=True)
        self.song_event = None
        self.jfk_event = None
        self.chug_speak = None
        self.lap_event = None
        self.removing_player = False
        self._disconnect_pause_player_id = None
        self.turn_id += 1
        self.phase = "wait_roll"
        self.camera.focus(self.board_spaces[self.players[self.current_idx].position]["pos"][0])
        self.add_message(f"Host removed player {removed_name}.")
        self._last_game_broadcast = None
        self._last_turn_broadcast = None
        self.lan_server.publish(self.lan_server.lobby.public_state())

    def _apply_drink_correction(self, action):
        if action == "close":
            self.correcting_drinks = False
            return
        if action == "previous":
            self.correction_player_idx = (self.correction_player_idx - 1) % len(self.players)
            return
        if action == "next":
            self.correction_player_idx = (self.correction_player_idx + 1) % len(self.players)
            return
        player = self.players[self.correction_player_idx]
        field, delta = action
        old_value = getattr(player, field)
        new_value = max(0, old_value + delta)
        if new_value != old_value:
            setattr(player, field, new_value)
            self.add_message(f"Host corrected {player.name}'s {field}: {old_value} -> {new_value}.")
            self._last_game_broadcast = None

    def _end_game_early(self):
        self._stop_song_audio(resume_media=True)
        self.song_event = None
        self.jfk_event = None
        self.chug_speak = None
        self.lap_event = None
        self.hot_seat = None
        self.winner = None
        self.current_prompt = None
        self._last_prompt_broadcast = None
        self.paused = False
        self.state = "end"
        self.lan_server.publish({"type": "game_end", "winner": None,
                                 "message": "The host ended the game early. No winner was declared."})

    def _return_to_main_menu(self):
        self._stop_song_audio(resume_media=True)
        self.song_event = None
        self.jfk_event = None
        self.chug_speak = None
        self.lap_event = None
        self.hot_seat = None
        self.winner = None
        self.paused = False
        self.show_rules = False
        self.correcting_drinks = False
        self.removing_player = False
        self._disconnect_pause_player_id = None
        self.current_prompt = None
        self._last_prompt_broadcast = None
        self.lan_server.lobby.return_to_lobby()
        self.lan_server.publish(self.lan_server.lobby.public_state())
        self.state = "menu"

    def _resolve_player_pick(self, choice: Player):
        if self.pick_effect == "mate":
            source = self.pick_source
            self.rules.pair_mates(source, choice)
            msg = f"{source.name} & {choice.name} are now Mates! They drink together for the rest of the game."
            self.add_message(msg)
            self.last_effect     = "custom"
            self.last_effect_msg = msg

        elif self.pick_effect == "drunk_driving":
            self._give_shot(choice, _propagate=False)
            msg = f"DRUNK DRIVING! {choice.name} takes the shot."
            self.add_message(msg)
            self.last_effect     = "custom"
            self.last_effect_msg = msg

        self.pick_title   = ""
        self.pick_choices = []
        self.pick_effect  = None
        self.pick_source  = None
        self._pick_btns   = []
        self.phase        = "resolving"
        self.resolve_start = pygame.time.get_ticks()

    def _handle_hot_seat_host_action(self, action):
        if not self.hot_seat:
            return
        if action == "begin":
            self._begin_hot_seat_questions()
        elif action == "skip_question" and self.hot_seat["stage"] == "answering":
            self.hot_seat["question_index"] += 1
            if self.hot_seat["question_index"] >= len(self.hot_seat["questions"]):
                self.hot_seat["stage"] = "finish"
        elif isinstance(action, tuple) and action[0] == "skip_player":
            player_id = action[1]
            if player_id in self.hot_seat["pending"]:
                self.lan_server.publish({
                    "type": "event_resolved", "turn_id": self.turn_id,
                    "prompt_id": self._hot_seat_prompt(player_id, "ask"),
                    "player_id": player_id,
                })
            self.hot_seat["pending"].pop(player_id, None)
            if not self.hot_seat["pending"]:
                self._begin_hot_seat_questions()
        self._last_hot_seat_broadcast = None

    def _resolve_option_pick(self, choice: str):
        player = self.option_source
        effect = self.option_effect

        if player is not None and effect == "double_or_single_shot":
            if "Double" in choice:
                self._give_shot(player)
                self._give_shot(player)
                self.last_effect_msg = (
                    f"{player.name} goes for it — DOUBLE SHOT!"
                )
            else:
                self._give_shot(player)
                self.last_effect_msg = (
                    f"{player.name} chooses a SINGLE SHOT."
                )
            self.last_effect = "custom"
            self.add_message(self.last_effect_msg)

        self.option_title   = ""
        self.option_choices = []
        self.option_effect  = None
        self.option_source  = None
        self._option_btns   = []
        self.phase        = "resolving"
        self.resolve_start = pygame.time.get_ticks()

    # ------------------------------------------------------------------
    # GAME — draw
    # ------------------------------------------------------------------

    def draw_game(self):
        camera_x = int(round(self.camera.position))
        if self.board_surf is None or self._board_camera_x != camera_x:
            self._render_board(camera_x)
        self.screen.blit(self.board_surf, (0, 0))
        current = self.players[self.current_idx] if self.players else None
        if current is None or current.whirlpool_position is None:
            self._draw_tokens()
        else:
            self._draw_whirlpool_board()
        if self.phase in ("resolving", "phone_prompt") and self.last_effect:
            self._draw_event_banner()
        self._draw_sidebar()
        if self.phase == "pick_player":
            self._draw_player_picker()
        if self.phase == "pick_option":
            self._draw_option_picker()
        if self.phase == "rule_announcement":
            self._draw_rule_announcement()
        if self.phase == "hot_seat":
            self._draw_hot_seat_overlay()
        if self.phase in ("song_countdown", "song_playing"):
            self._draw_song_overlay()
        if self.phase == "jfk_countdown":
            self._draw_jfk_overlay()
        if self.paused:
            self._draw_pause_overlay()

    def _draw_whirlpool_board(self):
        """Render the shared circular six-space board and every trapped token."""
        shade = pygame.Surface((BOARD_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((8, 38, 72, 232))
        self.screen.blit(shade, (0, 0))
        center_x, center_y, radius = BOARD_W // 2, SCREEN_H // 2, 225
        draw_outlined_text(self.screen, "WHIRLPOOL", self.f_title,
                           (90, 210, 255), (5, 24, 48), center_x, 72)
        labels = ("1 SIP", "2 SIPS", "1 SHOT", "2 SHOTS", "3 SHOTS", "6 EXIT")
        points = []
        for index, label in enumerate(labels):
            angle = -math.pi / 2 + index * math.tau / 6
            point = (round(center_x + math.cos(angle) * radius),
                     round(center_y + math.sin(angle) * radius))
            points.append(point)
        pygame.draw.lines(self.screen, (90, 210, 255), True, points, 7)
        for point, label in zip(points, labels):
            pygame.draw.circle(self.screen, MARKER, point, 57)
            pygame.draw.circle(self.screen, CARDBOARD_LITE, point, 53)
            draw_text(self.screen, label, self.f_small, MARKER, point[0], point[1])

        trapped = [player for player in self.players
                   if player.whirlpool_position is not None]
        groups = {}
        for player in trapped:
            groups.setdefault(player.whirlpool_position, []).append(player)
        for position, occupants in groups.items():
            point = points[position]
            total_width = len(occupants) * 44
            for offset, player in enumerate(occupants):
                token = self.token_surfs.get(player.token_name)
                if token:
                    image = pygame.transform.smoothscale(token, (40, 40))
                    x = point[0] - total_width // 2 + offset * 44 + 2
                    self.screen.blit(image, (x, point[1] - 50))
        draw_text(self.screen, "Roll on your normal turn. A 6 escapes.",
                  self.f_label, WHITE, center_x, SCREEN_H - 52)

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
            bw = min(BOARD_W - 60, max(280, self.f_title.size(headline)[0] + 70))
            bh = self.f_title.get_height() + 36
            bx, by = (BOARD_W - bw) // 2, (SCREEN_H - bh) // 2
            draw_panel(self.screen, CARDBOARD_DARK,
                       pygame.Rect(bx, by, bw, bh), 14, 4, color)
            draw_outlined_text(self.screen, headline, self.f_title,
                               color, MARKER, bx + bw // 2, by + bh // 2)

        elif self.last_effect == "custom":
            # Custom spaces: word-wrapped message in a taller banner
            color = ORANGE
            desired_w = self.f_label.size(self.last_effect_msg)[0] + 64
            bw = min(BOARD_W - 60, max(300, desired_w))
            bx = (BOARD_W - bw) // 2
            lines = wrap_text(self.last_effect_msg, self.f_label, bw - 40)

            line_h = self.f_label.get_height() + 4
            bh     = min(SCREEN_H - 80, max(90, len(lines) * line_h + 36))
            by     = (SCREEN_H - bh) // 2

            draw_panel(self.screen, CARDBOARD_DARK,
                       pygame.Rect(bx, by, bw, bh), 14, 4, color)

            text_y = by + (bh - len(lines) * line_h) // 2 + line_h // 2
            for text_line in lines:
                draw_text(self.screen, text_line, self.f_label,
                          MARKER, bx + bw // 2, text_y)
                text_y += line_h

    def _draw_hot_seat_overlay(self):
        state = self.hot_seat
        if not state:
            return
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((24, 5, 9, 238))
        self.screen.blit(shade, (0, 0))
        self._hot_seat_host_btns = []
        draw_outlined_text(self.screen, "HOT SEAT!", self.f_title,
                           (255, 92, 92), (65, 8, 18), SCREEN_W // 2, 75)
        draw_text(self.screen, state["active_player_name"], self.f_header,
                  (255, 225, 140), SCREEN_W // 2, 132)

        if state["stage"] == "collecting":
            pending = list(state["pending"].items())
            draw_text(self.screen,
                      f"Questions received: {len(state['questions'])}   Waiting for: {len(pending)}",
                      self.f_label, WHITE, SCREEN_W // 2, 184)
            cols = 2
            bw, bh, gap = 300, 38, 12
            start_x = SCREEN_W // 2 - (cols * bw + gap) // 2
            for index, (player_id, name) in enumerate(pending):
                x = start_x + (index % cols) * (bw + gap)
                y = 220 + (index // cols) * 47
                btn = pygame.Rect(x, y, bw, bh)
                draw_button(self.screen, btn, f"Skip {name}", self.f_body,
                            CARDBOARD_DARK, WHITE, (255, 92, 92), 8, 2)
                self._hot_seat_host_btns.append((btn, ("skip_player", player_id)))
            begin = pygame.Rect(SCREEN_W // 2 - 190, SCREEN_H - 78, 380, 52)
            draw_button(self.screen, begin, "Begin With Received Questions",
                        self.f_body, (65, 145, 82), WHITE, MARKER, 10, 3)
            self._hot_seat_host_btns.append((begin, "begin"))
        elif state["stage"] == "answering":
            question = state["questions"][state["question_index"]]
            draw_text(self.screen,
                      f"Question {state['question_index'] + 1} of {len(state['questions'])} — {question['author']} asks:",
                      self.f_label, (255, 225, 140), SCREEN_W // 2, 190)
            words, lines, line = question["text"].split(), [], ""
            for word in words:
                candidate = (line + " " + word).strip()
                if self.f_header.size(candidate)[0] < SCREEN_W - 160:
                    line = candidate
                else:
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)
            y = 275
            for value in lines:
                draw_text(self.screen, value, self.f_header, WHITE, SCREEN_W // 2, y)
                y += 48
            skip = pygame.Rect(SCREEN_W // 2 - 130, SCREEN_H - 78, 260, 52)
            draw_button(self.screen, skip, "Host: Skip Question", self.f_body,
                        CARDBOARD_DARK, WHITE, (255, 92, 92), 10, 3)
            self._hot_seat_host_btns.append((skip, "skip_question"))
        else:
            draw_text(self.screen, "Every question has been answered!", self.f_header,
                      WHITE, SCREEN_W // 2, SCREEN_H // 2 - 25)
            draw_text(self.screen, "Finish Hot Seat on the active player's phone.",
                      self.f_label, (255, 225, 140), SCREEN_W // 2, SCREEN_H // 2 + 35)

    def _draw_song_overlay(self):
        event = self.song_event
        if not event:
            return
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((10, 7, 28, 244))
        self.screen.blit(shade, (0, 0))
        pulse = 8 + int(5 * math.sin(pygame.time.get_ticks() / 120.0))
        title_color = (255, 214, 42) if event["effect"] == "thunderstruck" else (90, 230, 135)
        draw_outlined_text(self.screen, event["title"], self.f_title, title_color,
                           (40, 10, 55), SCREEN_W // 2, 150 + pulse)
        if self.phase == "song_countdown":
            started = event["countdown_start"]
            remaining = 5 if started is None else max(1, 5 - (pygame.time.get_ticks() - started) // 1000)
            draw_text(self.screen, "GET READY!", self.f_header, WHITE, SCREEN_W // 2, 255)
            countdown_font = self._font("impact", 150)
            draw_outlined_text(self.screen, str(remaining), countdown_font, title_color,
                               (40, 10, 55), SCREEN_W // 2, 390)
        else:
            elapsed = max(0, pygame.time.get_ticks() - event["started_at"])
            duration = max(1, event["duration_ms"])
            progress = min(1.0, elapsed / duration)
            bar = pygame.Rect(150, 310, SCREEN_W - 300, 34)
            pygame.draw.rect(self.screen, (55, 45, 75), bar, border_radius=17)
            fill = pygame.Rect(bar.x, bar.y, int(bar.w * progress), bar.h)
            pygame.draw.rect(self.screen, title_color, fill, border_radius=17)
            pygame.draw.rect(self.screen, WHITE, bar, 3, border_radius=17)
            def clock_text(ms):
                seconds = max(0, ms // 1000)
                return f"{seconds // 60}:{seconds % 60:02d}"
            draw_text(self.screen, f"{clock_text(elapsed)} / {clock_text(duration)}",
                      self.f_label, WHITE, SCREEN_W // 2, 375)
            animation_started = event.get("cue_animation_started_at")
            if animation_started is not None:
                animation_elapsed = pygame.time.get_ticks() - animation_started
                if 0 <= animation_elapsed < SONG_CUE_ANIMATION_MS:
                    animation_progress = animation_elapsed / SONG_CUE_ANIMATION_MS
                    cue_size = 90 + round(70 * math.sin(math.pi * animation_progress))
                    cue_color = (
                        255,
                        max(80, round(230 - 120 * animation_progress)),
                        max(30, round(90 - 60 * animation_progress)),
                    )
                    draw_outlined_text(
                        self.screen, event["cue_label"], self._font("impact", cue_size),
                        cue_color, (40, 10, 55), SCREEN_W // 2, 245,
                    )
        self._song_skip_btn = pygame.Rect(SCREEN_W // 2 - 120, SCREEN_H - 86, 240, 54)
        draw_button(self.screen, self._song_skip_btn, "Host: Skip Song", self.f_body,
                    CARDBOARD_DARK, WHITE, title_color, 10, 3)

    def _draw_player_picker(self):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        self.screen.blit(ov, (0, 0))

        title = self.pick_title or "Choose a player"
        widest = max([self.f_label.size(title)[0]] +
                     [self.f_body.size(p.name)[0] for p in self.pick_choices])
        panel = centered_popup(max(360, widest + 80),
                               82 + len(self.pick_choices) * 44)
        x, y, w = panel.x, panel.y, panel.w
        draw_panel(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
        draw_text(self.screen, title, self.f_label, MARKER,
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

        title = self.option_title or "Choose an option"
        widest = max([self.f_label.size(title)[0]] +
                     [self.f_body.size(opt)[0] for opt in self.option_choices])
        panel = centered_popup(max(360, widest + 80),
                               82 + len(self.option_choices) * 44)
        x, y, w = panel.x, panel.y, panel.w
        draw_panel(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
        draw_text(self.screen, title, self.f_label, MARKER,
                  panel.centerx, y + 28)

        self._option_btns = []
        by = y + 56
        for opt in self.option_choices:
            btn = pygame.Rect(x + 20, by, w - 40, 38)
            draw_button(self.screen, btn, opt, self.f_body, CARDBOARD_DARK, WHITE, MARKER, 8, 2)
            self._option_btns.append((btn, opt))
            by += 44

    def _draw_rule_announcement(self):
        announcement = self.rule_announcement
        if not announcement:
            return
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((18, 8, 4, 242))
        self.screen.blit(shade, (0, 0))

        title = "NEW HOUSE RULE!"
        author = f"Added by {announcement['author']}"
        desired_w = max(self.f_title.size(title)[0] + 100,
                        self.f_label.size(author)[0] + 80,
                        self.f_header.size(announcement["text"])[0] + 110)
        panel_w = min(SCREEN_W - 80, max(520, desired_w))
        lines = wrap_text(announcement["text"], self.f_header, panel_w - 110)
        line_h = self.f_header.get_height() + 12
        panel = centered_popup(panel_w,
                               205 + len(lines) * line_h, 40)
        draw_panel(self.screen, CARDBOARD_LITE, panel, 18, 6, ORANGE)
        draw_outlined_text(self.screen, title, self.f_title,
                           YELLOW, MARKER_BROWN, panel.centerx, panel.y + 72)
        draw_text(self.screen, author, self.f_label,
                  MARKER_BROWN, panel.centerx, panel.y + 125)
        start_y = panel.y + 170
        for index, value in enumerate(lines):
            draw_text(self.screen, value, self.f_header, MARKER,
                      panel.centerx, start_y + index * line_h)
        seconds = max(1, math.ceil(self.rule_announcement_remaining_ms / 1000))
        draw_text(self.screen, f"Next turn in {seconds}…", self.f_small,
                  MARKER_BROWN, panel.centerx, panel.bottom - 38)

    def _draw_jfk_overlay(self):
        """Fill the shared display with JFK; intentionally show no timer."""
        self.screen.fill((16, 32, 68))
        draw_outlined_text(
            self.screen, "JFK", self.f_title, WHITE, (5, 10, 24),
            SCREEN_W // 2, SCREEN_H // 2,
        )

    def _draw_pause_overlay(self):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))

        if self.removing_player:
            displayed_players = players_in_join_order(self.players)
            labels = [p.name + (" (current)" if p is self.players[self.current_idx] else "")
                      for p in displayed_players]
            widest = max([self.f_header.size("REMOVE PLAYER")[0]] +
                         [self.f_small.size(label)[0] for label in labels])
            panel = centered_popup(max(360, widest + 100),
                                   115 + len(self.players) * 41)
            x, y, w = panel.x, panel.y, panel.w
            draw_panel(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
            draw_text(self.screen, "REMOVE PLAYER", self.f_header, MARKER_BROWN,
                      panel.centerx, y + 32)
            self._removal_btns = []
            by = y + 62
            for player in displayed_players:
                btn = pygame.Rect(x + 35, by, w - 70, 36)
                suffix = " (current)" if player is self.players[self.current_idx] else ""
                draw_button(self.screen, btn, player.name + suffix, self.f_small,
                            (150, 70, 60), WHITE, MARKER, 8, 2)
                self._removal_btns.append((btn, player))
                by += 41
            back = pygame.Rect(x + 160, by + 4, 240, 38)
            draw_button(self.screen, back, "Cancel", self.f_small,
                        CARDBOARD_DARK, WHITE, MARKER, 8, 2)
            self._removal_btns.append((back, None))
            return

        if self.correcting_drinks:
            control_labels = ["Previous", "- Shot", "+ Shot", "- Sip", "+ Sip", "Next"]
            control_widths = [max(75, self.f_small.size(label)[0] + 24)
                              for label in control_labels]
            content_w = sum(control_widths) + 10 * (len(control_widths) - 1)
            panel = centered_popup(max(content_w + 60,
                                       self.f_header.size("CORRECT DRINK TOTALS")[0] + 80),
                                   292)
            x, y, w = panel.x, panel.y, panel.w
            draw_panel(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
            player = self.players[self.correction_player_idx]
            draw_text(self.screen, "CORRECT DRINK TOTALS", self.f_header, MARKER_BROWN,
                      panel.centerx, y + 35)
            draw_text(self.screen, player.name, self.f_label, MARKER, panel.centerx, y + 78)
            draw_text(self.screen, f"Shots: {player.shots}     Sips: {player.sips}",
                      self.f_body, MARKER, panel.centerx, y + 112)
            actions = ["previous", ("shots", -1), ("shots", 1),
                       ("sips", -1), ("sips", 1), "next"]
            specs = []
            control_x = x + (w - content_w) // 2
            for label, width, action in zip(control_labels, control_widths, actions):
                specs.append((pygame.Rect(control_x, y + 145, width, 42), label, action))
                control_x += width + 10
            specs.append((pygame.Rect(panel.centerx - 120, panel.bottom - 66, 240, 46),
                          "Back", "close"))
            self._correction_btns = [(rect, action) for rect, _, action in specs]
            for rect, label, _ in specs:
                draw_button(self.screen, rect, label, self.f_small,
                            CARDBOARD_DARK, WHITE, MARKER, 8, 2)
            return

        if self.show_rules:
            seen = set()
            mate_pairs = []
            for a, b in self.mates.items():
                key = tuple(sorted((id(a), id(b))))
                if key not in seen:
                    seen.add(key)
                    mate_pairs.append((a.name, b.name))
            rule_labels = ([f"{i + 1}. {rule}" for i, rule in enumerate(self.house_rules)]
                           or ["No house rules yet."])
            mate_labels = ([f"{i + 1}. {a_name} <-> {b_name}"
                            for i, (a_name, b_name) in enumerate(mate_pairs)]
                           or ["No active mates."])
            left_w = max([self.f_label.size("House Rules")[0]] +
                         [self.f_small.size(value)[0] for value in rule_labels])
            right_w = max([self.f_label.size("Mates")[0]] +
                          [self.f_small.size(value)[0] for value in mate_labels])
            desired_w = max(620, left_w + right_w + 100)
            available_w = min(desired_w, SCREEN_W - 80)
            col_w = (available_w - 76) // 2
            rule_lines = [line for value in rule_labels
                          for line in wrap_text(value, self.f_small, col_w)]
            mate_lines = [line for value in mate_labels
                          for line in wrap_text(value, self.f_small, col_w)]
            desired_h = 145 + max(len(rule_lines), len(mate_lines)) * 24
            panel = centered_popup(available_w, max(220, desired_h), 40)
            x, y, w, h = panel.x, panel.y, panel.w, panel.h
            draw_panel(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
            draw_text(self.screen, "RULES", self.f_header, MARKER_BROWN, panel.centerx, y + 30)
            draw_text(self.screen, "House Rules", self.f_label, MARKER, x + 26, y + 72, align="left")
            draw_text(self.screen, "Mates", self.f_label, MARKER, x + w // 2 + 16, y + 72, align="left")
            max_rows = max(1, (panel.bottom - (y + 104) - 42) // 24)
            for index, value in enumerate(rule_lines[:max_rows]):
                draw_text(self.screen, value, self.f_small, MARKER,
                          x + 26, y + 104 + index * 24, align="left")
            for index, value in enumerate(mate_lines[:max_rows]):
                draw_text(self.screen, value, self.f_small, MARKER,
                          x + w // 2 + 16, y + 104 + index * 24, align="left")
            draw_text(self.screen, "Click anywhere or press ESC to go back", self.f_tiny, MARKER_BROWN,
                      panel.centerx, y + h - 24)
            return

        pause_labels = ["Resume", "Rules", "Skip Disconnected Player", "Remove Player",
                        "Correct Drink Totals", "End Game Early", "Main Menu"]
        widest = max(self.f_body.size(label)[0] for label in pause_labels)
        panel = centered_popup(max(340, widest + 140), 70 + len(pause_labels) * 56 + 34)
        x, y, w = panel.x, panel.y, panel.w
        draw_panel(self.screen, CARDBOARD_LITE, panel, 12, 3, MARKER)
        draw_text(self.screen, "PAUSED", self.f_header, MARKER_BROWN, panel.centerx, y + 36)

        bx, bw, bh = x + 40, w - 80, 48
        self._pause_resume_btn = pygame.Rect(bx, y + 70, bw, bh)
        self._pause_rules_btn = pygame.Rect(bx, y + 126, bw, bh)
        self._pause_skip_btn = pygame.Rect(bx, y + 182, bw, bh)
        self._pause_remove_btn = pygame.Rect(bx, y + 238, bw, bh)
        self._pause_correct_btn = pygame.Rect(bx, y + 294, bw, bh)
        self._pause_quit_btn = pygame.Rect(bx, y + 350, bw, bh)
        self._pause_menu_btn = pygame.Rect(bx, y + 406, bw, bh)

        disconnected = not getattr(self.players[self.current_idx], "connected", True)

        draw_button(self.screen, self._pause_resume_btn, "Resume", self.f_body,
                    (80, 170, 80), WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._pause_rules_btn, "Rules", self.f_body,
                    CARDBOARD_DARK, WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._pause_skip_btn, "Skip Disconnected Player", self.f_body,
                    CARDBOARD_DARK if disconnected else (115, 105, 90), WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._pause_remove_btn, "Remove Player", self.f_body,
                    CARDBOARD_DARK if len(self.players) > 2 else (115, 105, 90),
                    WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._pause_correct_btn, "Correct Drink Totals", self.f_body,
                    CARDBOARD_DARK, WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._pause_quit_btn, "End Game Early", self.f_body,
                    (150, 70, 60), WHITE, MARKER, 10, 3)
        draw_button(self.screen, self._pause_menu_btn, "Main Menu", self.f_body,
                    (120, 80, 65), WHITE, MARKER, 10, 3)

    def _draw_tokens(self):
        # The scrolling world intentionally shows only the active player's token.
        active = self.players[self.current_idx]
        if active is not self.anim_player:
            cx, cy = self.camera.world_to_screen(self.board_spaces[active.position]["pos"])
            img = self.token_board.get(active.token_name)
            if img and -40 <= cx <= BOARD_W + 40:
                self.screen.blit(img, (cx - 19, cy - 19))

        # Draw the animating player with a parabolic hop arc
        if self.anim_player is not None and self.phase == "moving":
            elapsed = pygame.time.get_ticks() - self.anim_step_start
            t = min(1.0, elapsed / max(1, self.anim_step_dur))

            fx, fy = self.camera.world_to_screen(self.board_spaces[self.anim_from_pos]["pos"])
            tx, ty = self.camera.world_to_screen(self.board_spaces[self.anim_to_pos]["pos"])

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
        draw_panel(self.screen, SIDEBAR_BG, sb, 0, 4, MARKER_BROWN)
        pygame.draw.line(self.screen, MARKER, (SIDEBAR_X, 0), (SIDEBAR_X, SCREEN_H), 4)

        current = self.players[self.current_idx]

        # --- Current player banner ---
        banner = pygame.Rect(SIDEBAR_X + 8, 8, SIDEBAR_W - 16, 75)
        draw_panel(self.screen, CARDBOARD_DARK, banner, 10, 3, MARKER)
        tok = self.token_lead.get(current.token_name)
        if tok:
            self.screen.blit(tok, (SIDEBAR_X + 14, 17))
        turn_x = SIDEBAR_X + 62
        turn_status = "IT'S YOUR TURN," if self.camera.settled else "MOVING CAMERA TO"
        draw_text(self.screen, turn_status, self.f_small,
                  MARKER_BROWN, turn_x, 28, align="left")
        name_display = current.name[:10] + ("…" if len(current.name) > 10 else "")
        if current.is_beer_bitch:
            name_display = "BEER BITCH " + name_display
        draw_text(self.screen, name_display.upper() + "!", self.f_label,
                  PINK if current.is_beer_bitch else MARKER,
                  turn_x, 52, align="left")

        # --- Die display ---
        die_cx = SIDEBAR_X + SIDEBAR_W // 2
        draw_die_face(self.screen, die_cx, 148, self.display_die, 72)
        die_label = "ROLLING..." if self.phase == "rolling" else f"Rolled: {self.die_value}"
        draw_text(self.screen, die_label, self.f_small, MARKER,
                  die_cx, 195)

        # --- Host recovery button (die rolls are phone-only) ---
        can_skip = self.phase == "wait_roll" and self.camera.settled and not self.paused
        btn_color = (175, 105, 55) if can_skip else (130, 130, 120)
        draw_button(self.screen, self.roll_btn, "SKIP PLAYER", self.f_label,
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

        # --- Player status ---
        lb_y = 400
        pygame.draw.line(self.screen, MARKER_BROWN,
                         (SIDEBAR_X + 10, lb_y - 8), (SIDEBAR_X + SIDEBAR_W - 10, lb_y - 8), 2)
        draw_text(self.screen, "PLAYERS", self.f_small, MARKER_BROWN,
                  SIDEBAR_X + SIDEBAR_W // 2, lb_y)
        lb_y += 18

        n_players   = len(self.players)
        row_h       = sidebar_row_height(n_players, SCREEN_H - lb_y - 8)
        compact     = row_h < 52   # tight layout when many players

        for player_num, p in enumerate(players_in_join_order(self.players), start=1):
            ry   = lb_y + (player_num - 1) * row_h
            card = pygame.Rect(SIDEBAR_X + 4, ry + 2, SIDEBAR_W - 8, row_h - 4)
            bg   = (205, 175, 95) if p is current else CARDBOARD_DARK
            draw_panel(self.screen, bg, card, 7, 2, MARKER_BROWN)

            mid = ry + row_h // 2

            # Current board-progress rank.
            pygame.draw.circle(self.screen, CARDBOARD_LITE, (SIDEBAR_X + 18, mid), 10)
            draw_text(self.screen, str(player_num), self.f_tiny, MARKER,
                      SIDEBAR_X + 18, mid)

            # Token (fits in row height minus padding)
            tok_sz  = min(row_h - 8, 36)
            tok     = self.token_surfs.get(p.token_name)
            if tok:
                ts = pygame.transform.smoothscale(tok, (tok_sz, tok_sz))
                self.screen.blit(ts, (SIDEBAR_X + 32, mid - tok_sz // 2))

            tx = SIDEBAR_X + 32 + tok_sz + 4

            connected = getattr(p, "connected", True)
            pygame.draw.circle(self.screen, GREEN if connected else RED,
                               (card.right - 8, card.top + 8), 4)

            if compact:
                # Compact single-line player summary
                short = p.name[:7] + ("…" if len(p.name) > 7 else "")
                if p.is_beer_bitch:
                    short = "Beer Bitch " + short
                draw_text(self.screen, short, self.f_tiny,
                          PINK if p.is_beer_bitch else MARKER,
                          tx, mid, align="left")
                stat_str = f"#{p.position}  {p.shots}sh {p.sips}si"
                draw_text(self.screen, stat_str, self.f_tiny, MARKER_BROWN,
                          card.right - 14, mid, align="right")
            else:
                # Two lines: name on top, stats on bottom
                short = p.name[:15] + ("…" if len(p.name) > 15 else "")
                if p.is_beer_bitch:
                    short = "Beer Bitch " + short
                draw_text(self.screen, short, self.f_small,
                          PINK if p.is_beer_bitch else MARKER,
                          tx, mid - 9, align="left")
                position_text = "FINISHED" if p.finished else f"Space {p.position}"
                draw_text(self.screen, position_text, self.f_tiny, YELLOW,
                          card.right - 5, mid - 9, align="right")
                # Shots and sips with coloured labels
                shot_str = f"{p.shots} shots"
                sip_str  = f"{p.sips} sips"
                draw_text(self.screen, shot_str, self.f_tiny, (255, 130, 130),
                          tx, mid + 8, align="left")
                draw_text(self.screen, "•", self.f_tiny, MARKER_BROWN,
                          tx + 58, mid + 8)
                draw_text(self.screen, sip_str, self.f_tiny, (130, 180, 255),
                          tx + 68, mid + 8, align="left")

    # ------------------------------------------------------------------
    # Board viewport rendering
    # ------------------------------------------------------------------

    def _render_board(self, camera_x=None) -> pygame.Surface:
        """Render only the visible world, avoiding a multi-hundred-MB 4K surface."""
        camera_x = int(round(self.camera.position if camera_x is None else camera_x))
        if self._board_bg is None:
            self._board_bg = _new_native_surface((BOARD_W, SCREEN_H))
            draw_textured_rect(self._board_bg, _BACKGROUND_TEXTURE,
                               (0, 0, BOARD_W, SCREEN_H), 0)
            for t in range(4):
                pygame.draw.rect(self._board_bg, MARKER_BROWN,
                                 (t, t, BOARD_W - t * 2, SCREEN_H - t * 2), 1)
            pygame.draw.rect(self._board_bg, MARKER,
                             (6, 6, BOARD_W - 12, SCREEN_H - 12), 3)
        if not isinstance(self.board_surf, NativeSurface) or self.board_surf.logical_width != BOARD_W:
            self.board_surf = _new_native_surface((BOARD_W, SCREEN_H))
        surf = self.board_surf
        _RAW_BLIT(surf, self._board_bg, (0, 0))
        visible_pad = SPACE_RADIUS + 24

        def screen_point(point):
            return point[0] - camera_x, point[1]

        def segment_visible(a, b):
            return not (max(a[0], b[0]) < -visible_pad or
                        min(a[0], b[0]) > BOARD_W + visible_pad)

        # Board title (uses the loaded board's name)
        title_font = self._font("impact", 26)
        draw_text(surf, self.board_name.upper(), title_font, MARKER_BROWN,
                  self.world_width // 2 - camera_x, 24)

        # Path lines between consecutive spaces
        for i in range(len(self.board_spaces) - 1):
            a = screen_point(self.board_spaces[i]["pos"])
            b = screen_point(self.board_spaces[i + 1]["pos"])
            if segment_visible(a, b):
                pygame.draw.line(surf, MARKER_BROWN, a, b, 7)
                pygame.draw.line(surf, CARDBOARD_DARK, a, b, 4)

        # Back arrows (orange marker on the space itself)
        for sp in self.board_spaces:
            if sp["type"] == "back":
                v = sp.get("value", 1)
                prev_pos = max(0, sp["id"] - v)
                start = screen_point(sp["pos"])
                target = screen_point(self.board_spaces[prev_pos]["pos"])
                if segment_visible(start, target):
                    draw_arrow(surf, (210, 100, 30), start, target, width=4, head=12)

        # Space circles
        sp_font  = self.f_space
        num_font = self.f_spnum
        for sp in self.board_spaces:
            cx, cy = screen_point(sp["pos"])
            if not -visible_pad <= cx <= BOARD_W + visible_pad:
                continue
            stype  = sp["type"]
            color  = sp.get("color", SPACE_COLORS.get(stype, CARDBOARD_LITE))

            # Outer ring (marker outline)
            pygame.draw.circle(surf, MARKER, (cx, cy), SPACE_RADIUS + 3)
            # Cardboard fill with the space type's color tint.
            draw_textured_circle(surf, _BUTTON_TEXTURE, (cx, cy), SPACE_RADIUS, color)
            # Inner ring
            pygame.draw.circle(surf, MARKER, (cx, cy), SPACE_RADIUS, 3)

            # Type icon
            icon = TYPE_ICONS.get(stype, "")
            if icon:
                draw_text(surf, icon, sp_font, MARKER, cx, cy)

            # Space number (below circle)
            draw_text(surf, str(sp["id"]), num_font, MARKER_BROWN, cx, cy + SPACE_RADIUS + 8)

        # Finish star decoration
        fx, fy = screen_point(self.board_spaces[self.finish_index]["pos"])
        if -visible_pad <= fx <= BOARD_W + visible_pad:
            self._draw_small_star(surf, fx, fy - SPACE_RADIUS - 16, 14, GOLD)
            self._draw_small_star(surf, fx - 20, fy - SPACE_RADIUS - 12, 10, YELLOW)
            self._draw_small_star(surf, fx + 20, fy - SPACE_RADIUS - 12, 10, YELLOW)

        # Start label
        sx, sy = screen_point(self.board_spaces[0]["pos"])
        if -visible_pad <= sx <= BOARD_W + visible_pad:
            draw_text(surf, "START", self._font("arial", 11, bold=True),
                      MARKER, sx, sy + SPACE_RADIUS + 20)

        self._board_camera_x = camera_x
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
                    self.turn_id       = 1
                    self.action_guard.reset()
                    self.current_prompt = None
                    self._last_prompt_broadcast = None
                    self.hot_seat = None
                    self._hot_seat_sent_prompts.clear()
                    self._last_hot_seat_broadcast = None
                    self._stop_song_audio(resume_media=True)
                    self.song_event = None
                    self.jfk_event = None
                    self.chug_speak = None
                    self.lap_event = None
                    self.phase         = "wait_roll"
                    self.messages      = []
                    self.winner        = None
                    self.display_die   = 1
                    self.last_effect   = None
                    self.pending_interactive = None
                    self.rules.reset(self.players)
                    self.mates         = self.rules.mates
                    self.house_rules   = []
                    self.rule_announcement = None
                    self.rule_announcement_remaining_ms = 0
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
                    self.correcting_drinks = False
                    self.removing_player = False
                    self._disconnect_pause_player_id = None
                    self._last_game_broadcast = None
                    self._last_turn_broadcast = None
                    self._randomize_board_layout()
                    self.board_surf    = self._render_board()
                    self.add_message("Roll to start again!")
                    self.state         = "game"
                    self.lan_server.publish(self.lan_server.lobby.public_state())
                elif self._menu_btn.collidepoint(e.pos):
                    self._return_to_main_menu()

    def draw_end(self):
        # Background
        self.screen.blit(self._get_menu_bg(), (0, 0))

        # Winner or early-results banner
        title = "GAME OVER!" if self.winner else "GAME ENDED EARLY"
        draw_outlined_text(self.screen, title, self.f_title,
                           YELLOW, MARKER_BROWN, SCREEN_W // 2, 90)
        if self.winner:
            tok = self.token_surfs.get(self.winner.token_name)
            if tok:
                big_tok = pygame.transform.smoothscale(tok, (88, 88))
                self.screen.blit(big_tok, (SCREEN_W // 2 - 44, 140))
            draw_outlined_text(self.screen, f"{self.winner.name} WINS!",
                               self.f_header, (80, 220, 80), MARKER,
                               SCREEN_W // 2, 250)
        else:
            draw_text(self.screen, "No winner was declared.", self.f_header,
                      MARKER_BROWN, SCREEN_W // 2, 210)

        # Neutral player recap in stable turn/join order.
        player_titles = calculate_player_titles(self.players, winner=self.winner)
        headers = ["Player", "Award / Title", "Position", "Shots", "Sips"]
        col_x   = [160, 410, 680, 870, 1020]
        th_y = 295
        for hdr, cx in zip(headers, col_x):
            draw_text(self.screen, hdr, self.f_label, MARKER_BROWN, cx, th_y)

        available_h = SCREEN_H - 405
        row_h = min(52, max(25, available_h // max(1, len(self.players))))
        for player_num, p in enumerate(players_in_join_order(self.players), start=1):
            ry = 320 + (player_num - 1) * row_h
            row_bg = pygame.Rect(80, ry - 10, SCREEN_W - 160, row_h - 2)
            bg_col = (230, 200, 120) if p is self.winner else CARDBOARD_LITE
            draw_panel(self.screen, bg_col, row_bg, 8, 2, MARKER_BROWN)

            tok_sm = self.token_lead.get(p.token_name)
            if tok_sm:
                tok_size = min(36, row_h - 6)
                token = pygame.transform.smoothscale(tok_sm, (tok_size, tok_size))
                self.screen.blit(token, (col_x[0] - 55, ry + row_h // 2 - tok_size // 2 - 10))
            draw_text(self.screen, player_display_name(p), self.f_body,
                      PINK if p.is_beer_bitch else MARKER,
                      col_x[0], ry + row_h // 2 - 10, align="left")
            p_title = player_titles.get(p, "Pub Regular")
            draw_text(self.screen, p_title, self.f_body, (140, 70, 20),
                      col_x[1], ry + row_h // 2 - 10)
            position_text = "Finish" if p.finished else f"Space {p.position}"
            draw_text(self.screen, position_text, self.f_body, MARKER,
                      col_x[2], ry + row_h // 2 - 10)
            draw_text(self.screen, str(p.shots), self.f_body, RED,
                      col_x[3], ry + row_h // 2 - 10)
            draw_text(self.screen, str(p.sips), self.f_body, BLUE,
                      col_x[4], ry + row_h // 2 - 10)

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
