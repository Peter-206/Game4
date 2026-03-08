"""
game_data.py — All data, constants, and board configuration.

=======================================================================
  HOW TO EDIT THE BOARD
=======================================================================

Every space is its own clearly-labelled block below in BOARD_SPACES.
Change whatever you want inside each block. The fields are:

  "label"   — The name displayed on screen and in messages.

  "type"    — Controls the COLOR of the circle on the board.
              Pick one of:
                start | finish | normal | sip | shot |
                back | everyone_sip | forward | event

  "effect"  — What actually HAPPENS when someone lands here.
              Built-in effects:
                "sip"          → player drinks. Set "value" = number of sips.
                "shot"         → player takes a shot.
                "everyone_sip" → ALL players take 1 sip.
                "back"         → player moves back. Set "value" = spaces.
                "forward"      → player moves forward. Set "value" = spaces.
                "none"         → nothing happens (boring space).
                "finish"       → end of the game.

              Custom / party effects:
                "custom"       → shows your "msg" text on screen as a big
                                 event banner. Players read it and do whatever
                                 it says. No automatic drinks — you control it.
                                 Use {name} in "msg" to insert the player's name.
                                 Use {label} for the space name.

  "value"   — Number used by sip / back / forward effects.
  "msg"     — Text shown for "custom" effect. Use {name} and {label}.

=======================================================================
  ADDING A NEW CUSTOM SPACE
=======================================================================

  1. Find a "normal" space you want to replace.
  2. Change its "label" to whatever you want.
  3. Change "type" to "event" (gives it an orange color).
  4. Change "effect" to "custom".
  5. Write your rule in "msg". Example:

        "msg": "{name} must do their best impression of a pigeon, or take 2 sips!"

  That's it. Save the file and restart the game.

=======================================================================
"""

import os
import json
import glob

# ---------------------------------------------------------------------------
# Screen constants
# ---------------------------------------------------------------------------
SCREEN_W  = 1280
SCREEN_H  = 800
BOARD_W   = 865
SIDEBAR_X = 870
SIDEBAR_W = SCREEN_W - SIDEBAR_X
FPS       = 60

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
CARDBOARD       = (210, 175, 112)
CARDBOARD_DARK  = (175, 140,  80)
CARDBOARD_LITE  = (232, 205, 158)
MARKER          = ( 22,  16,   8)
MARKER_BROWN    = ( 90,  55,  20)
WHITE           = (255, 255, 255)
BLACK           = ( 10,  10,  10)
YELLOW          = (255, 220,  50)
RED             = (215,  60,  60)
GREEN           = ( 60, 195,  90)
BLUE            = ( 75, 145, 220)
ORANGE          = (230, 118,  40)
PURPLE          = (170,  90, 215)
TEAL            = ( 70, 200, 178)
SIDEBAR_BG      = (188, 152,  90)
SIDEBAR_DARK    = (158, 122,  60)
GOLD            = (255, 205,  30)
SILVER          = (195, 195, 205)
BRONZE          = (195, 145,  80)

SPACE_COLORS = {
    "start":        (255, 215,  50),
    "finish":       (255, 200,  25),
    "normal":       (228, 198, 148),
    "sip":          ( 88, 148, 218),
    "shot":         (212,  60,  60),
    "back":         (225, 112,  42),
    "everyone_sip": ( 72, 185, 212),
    "forward":      ( 72, 208, 172),
    "event":        (212, 172,  72),
}

TYPE_ICONS = {
    "start":        "GO!",
    "finish":       "WIN!",
    "normal":       "",
    "sip":          "SIP",
    "shot":         "SHOT",
    "back":         "BACK",
    "everyone_sip": "ALL",
    "forward":      "FWD",
    "event":        "!",
}


# ---------------------------------------------------------------------------
# Reusable party event square components (party_board_events.md).
# Boards can reference these with: {"id": X, "component": "component_name"}
# ---------------------------------------------------------------------------
PARTY_SQUARE_COMPONENTS = {
    "chicks_dicks": {
        "label":  "Chicks / Dicks",
        "type":   "event",
        "effect": "chicks_dicks",
        "color":  (235, 122, 152),
    },
    "androids_iphones": {
        "label":  "Androids / iPhones",
        "type":   "event",
        "effect": "androids_iphones",
        "color":  (120, 170, 235),
    },
    "shotgun": {
        "label":  "Shotgun",
        "type":   "event",
        "effect": "shotgun",
        "color":  (230, 92, 82),
    },
    "double_or_single_shot": {
        "label":  "Double Shot / Single Shot",
        "type":   "event",
        "effect": "double_or_single_shot",
        "color":  (230, 138, 72),
    },
    "karaoke": {
        "label":  "Karaoke",
        "type":   "event",
        "effect": "karaoke",
        "color":  (175, 115, 225),
    },
    "thunderstruck": {
        "label":  "Thunderstruck",
        "type":   "event",
        "effect": "thunderstruck",
        "color":  (245, 198, 62),
    },
    "rattlin_bog": {
        "label":  "Rattlin Bog",
        "type":   "event",
        "effect": "rattlin_bog",
        "color":  (92, 172, 122),
    },
    "mate": {
        "label":  "Mate",
        "type":   "event",
        "effect": "mate",
        "color":  (235, 152, 102),
    },
    "hot_seat": {
        "label":  "Hot Seat",
        "type":   "event",
        "effect": "hot_seat",
        "color":  (230, 108, 62),
    },
    "drunk_driving": {
        "label":  "Drunk Driving",
        "type":   "event",
        "effect": "drunk_driving",
        "color":  (212, 82, 82),
    },
    "new_rule": {
        "label":  "New Rule",
        "type":   "event",
        "effect": "new_rule",
        "color":  (92, 188, 198),
    },
}

# ---------------------------------------------------------------------------
# Board space positions — snake path, auto-computed.
# You generally don't need to touch this.
# ---------------------------------------------------------------------------
def _make_positions():
    x_ltr = [58, 203, 348, 493, 638, 803]
    x_rtl = list(reversed(x_ltr))
    rows_y = [728, 608, 488, 368, 248, 128]
    positions = []
    for row, y in enumerate(rows_y):
        xs = x_ltr if row % 2 == 0 else x_rtl
        for x in xs:
            positions.append((x, y))
    return positions

_POS = _make_positions()

# ---------------------------------------------------------------------------
#
#  THE BOARD — Edit each space block below.
#
#  Spaces are numbered 0 (start) → 35 (finish).
#  The position on screen is set automatically by _POS[id].
#
# ---------------------------------------------------------------------------

BOARD_SPACES = [

    # =========================================================
    # SPACE 0 — STARTING LINE
    # =========================================================
    {
        "id":     0,
        "label":  "Pizza Box Start",
        "type":   "start",
        "effect": "none",
        "pos":    _POS[0],
    },

    # =========================================================
    # SPACE 1 — SIP SPACE
    # Change "value" to set how many sips the player takes.
    # =========================================================
    {
        "id":     1,
        "label":  "Crust Corner",
        "type":   "sip",
        "effect": "sip",
        "value":  1,
        "pos":    _POS[1],
    },

    # =========================================================
    # SPACE 2 — CUSTOM CHALLENGE: TRIVIA TIME
    # Player answers a trivia question from the group,
    # or takes 2 sips. Edit "msg" to change the rule.
    # =========================================================
    {
        "id":     2,
        "label":  "Trivia Time",
        "type":   "event",
        "effect": "custom",
        "msg":    "{name} landed on Trivia Time! The group asks a trivia question. Answer wrong (or refuse) — take 2 sips!",
        "pos":    _POS[2],
    },

    # =========================================================
    # SPACE 3 — SIP SPACE
    # =========================================================
    {
        "id":     3,
        "label":  "Sauce Splash",
        "type":   "sip",
        "effect": "sip",
        "value":  1,
        "pos":    _POS[3],
    },

    # =========================================================
    # SPACE 4 — MOVE BACK
    # Player slides back "value" spaces.
    # =========================================================
    {
        "id":     4,
        "label":  "Grease Pit",
        "type":   "back",
        "effect": "back",
        "value":  2,
        "pos":    _POS[4],
    },

    # =========================================================
    # SPACE 5 — NORMAL (nothing happens)
    # =========================================================
    {
        "id":     5,
        "label":  "Topping Trail",
        "type":   "normal",
        "effect": "none",
        "pos":    _POS[5],
    },

    # =========================================================
    # SPACE 6 — NORMAL
    # =========================================================
    {
        "id":     6,
        "label":  "Cheese Lift",
        "type":   "normal",
        "effect": "none",
        "pos":    _POS[6],
    },

    # =========================================================
    # SPACE 7 — SIP SPACE (2 sips)
    # =========================================================
    {
        "id":     7,
        "label":  "Nacho Notch",
        "type":   "sip",
        "effect": "sip",
        "value":  2,
        "pos":    _POS[7],
    },

    # =========================================================
    # SPACE 8 — NORMAL
    # =========================================================
    {
        "id":     8,
        "label":  "Pepperoni Path",
        "type":   "normal",
        "effect": "none",
        "pos":    _POS[8],
    },

    # =========================================================
    # SPACE 9 — SIP SPACE
    # =========================================================
    {
        "id":     9,
        "label":  "Anchovy Alley",
        "type":   "sip",
        "effect": "sip",
        "value":  1,
        "pos":    _POS[9],
    },

    # =========================================================
    # SPACE 10 — NORMAL
    # =========================================================
    {
        "id":     10,
        "label":  "Flat Soda Swamp",
        "type":   "normal",
        "effect": "none",
        "pos":    _POS[10],
    },

    # =========================================================
    # SPACE 11 — NORMAL
    # =========================================================
    {
        "id":     11,
        "label":  "Crust Crest",
        "type":   "normal",
        "effect": "none",
        "pos":    _POS[11],
    },

    # =========================================================
    # SPACE 12 — SHOT SPACE
    # Player takes a full shot.
    # =========================================================
    {
        "id":     12,
        "label":  "Keg Keep",
        "type":   "shot",
        "effect": "shot",
        "pos":    _POS[12],
    },

    # =========================================================
    # SPACE 13 — CUSTOM CHALLENGE: TRUTH BOMB
    # Player must answer a truth question from the group,
    # or take 2 sips. Edit "msg" to change the rule.
    # =========================================================
    {
        "id":     13,
        "label":  "Truth Bomb",
        "type":   "event",
        "effect": "custom",
        "msg":    "{name} hit the Truth Bomb! Answer an honest question from the group — or take 2 sips!",
        "pos":    _POS[13],
    },

    # =========================================================
    # SPACE 14 — SIP SPACE (2 sips)
    # =========================================================
    {
        "id":     14,
        "label":  "Foam Falls",
        "type":   "sip",
        "effect": "sip",
        "value":  2,
        "pos":    _POS[14],
    },

    # =========================================================
    # SPACE 15 — MOVE BACK (3 spaces)
    # =========================================================
    {
        "id":     15,
        "label":  "Sauce Slide",
        "type":   "back",
        "effect": "back",
        "value":  3,
        "pos":    _POS[15],
    },

    # =========================================================
    # SPACE 16 — NORMAL
    # =========================================================
    {
        "id":     16,
        "label":  "Olive Oil Oasis",
        "type":   "normal",
        "effect": "none",
        "pos":    _POS[16],
    },

    # =========================================================
    # SPACE 17 — SIP SPACE
    # =========================================================
    {
        "id":     17,
        "label":  "Basil Bend",
        "type":   "sip",
        "effect": "sip",
        "value":  1,
        "pos":    _POS[17],
    },

    # =========================================================
    # SPACE 18 — NORMAL
    # =========================================================
    {
        "id":     18,
        "label":  "Yeast Boost",
        "type":   "normal",
        "effect": "none",
        "pos":    _POS[18],
    },

    # =========================================================
    # SPACE 19 — CUSTOM CHALLENGE: KARAOKE CORNER
    # Player must sing a verse of any song, or drink.
    # Edit "msg" to change the rule.
    # =========================================================
    {
        "id":     19,
        "label":  "Karaoke Corner",
        "type":   "event",
        "effect": "custom",
        "msg":    "{name} is on Karaoke Corner! Sing a full verse of any song — or take 3 sips!",
        "pos":    _POS[19],
    },

    # =========================================================
    # SPACE 20 — EVERYONE SIPS
    # All players take 1 sip.
    # =========================================================
    {
        "id":     20,
        "label":  "Party Pit Stop",
        "type":   "everyone_sip",
        "effect": "everyone_sip",
        "pos":    _POS[20],
    },

    # =========================================================
    # SPACE 21 — SIP SPACE (2 sips)
    # =========================================================
    {
        "id":     21,
        "label":  "Buffalo Wing Way",
        "type":   "sip",
        "effect": "sip",
        "value":  2,
        "pos":    _POS[21],
    },

    # =========================================================
    # SPACE 22 — MOVE BACK (2 spaces)
    # =========================================================
    {
        "id":     22,
        "label":  "Anchovy Avalanche",
        "type":   "back",
        "effect": "back",
        "value":  2,
        "pos":    _POS[22],
    },

    # =========================================================
    # SPACE 23 — SHOT SPACE
    # =========================================================
    {
        "id":     23,
        "label":  "Double Shot Dunes",
        "type":   "shot",
        "effect": "shot",
        "pos":    _POS[23],
    },

    # =========================================================
    # SPACE 24 — NORMAL
    # =========================================================
    {
        "id":     24,
        "label":  "Garlic Bread Gateway",
        "type":   "normal",
        "effect": "none",
        "pos":    _POS[24],
    },

    # =========================================================
    # SPACE 25 — SIP SPACE
    # =========================================================
    {
        "id":     25,
        "label":  "Marinara Mile",
        "type":   "sip",
        "effect": "sip",
        "value":  1,
        "pos":    _POS[25],
    },

    # =========================================================
    # SPACE 26 — NORMAL
    # =========================================================
    {
        "id":     26,
        "label":  "Pineapple Pause",
        "type":   "normal",
        "effect": "none",
        "pos":    _POS[26],
    },

    # =========================================================
    # SPACE 27 — NORMAL
    # =========================================================
    {
        "id":     27,
        "label":  "Jalapeno Jump",
        "type":   "normal",
        "effect": "none",
        "pos":    _POS[27],
    },

    # =========================================================
    # SPACE 28 — SIP SPACE (2 sips)
    # =========================================================
    {
        "id":     28,
        "label":  "Ranch Ridge",
        "type":   "sip",
        "effect": "sip",
        "value":  2,
        "pos":    _POS[28],
    },

    # =========================================================
    # SPACE 29 — CUSTOM CHALLENGE: TWO TRUTHS ONE LIE
    # Player says two truths and one lie. Group guesses.
    # Losers drink. Edit "msg" to change the rule.
    # =========================================================
    {
        "id":     29,
        "label":  "Two Truths One Lie",
        "type":   "event",
        "effect": "custom",
        "msg":    "{name} plays Two Truths One Lie! Anyone who guesses wrong takes a sip — and so does {name} if everyone gets it right!",
        "pos":    _POS[29],
    },

    # =========================================================
    # SPACE 30 — SHOT SPACE
    # =========================================================
    {
        "id":     30,
        "label":  "Last Call Ledge",
        "type":   "shot",
        "effect": "shot",
        "pos":    _POS[30],
    },

    # =========================================================
    # SPACE 31 — MOVE BACK (2 spaces)
    # =========================================================
    {
        "id":     31,
        "label":  "Dough Drop",
        "type":   "back",
        "effect": "back",
        "value":  2,
        "pos":    _POS[31],
    },

    # =========================================================
    # SPACE 32 — CUSTOM CHALLENGE: VOTE TO DRINK
    # Group votes — someone has to drink. Or use this
    # for one of your friend's custom mini-games.
    # Edit "msg" to change the rule.
    # =========================================================
    {
        "id":     32,
        "label":  "Democracy Dip",
        "type":   "event",
        "effect": "custom",
        "msg":    "{name} landed on Democracy Dip! The group votes on who takes 2 sips. Majority rules — no arguing!",
        "pos":    _POS[32],
    },

    # =========================================================
    # SPACE 33 — SIP SPACE
    # =========================================================
    {
        "id":     33,
        "label":  "Summit Sip",
        "type":   "sip",
        "effect": "sip",
        "value":  1,
        "pos":    _POS[33],
    },

    # =========================================================
    # SPACE 34 — EVERYONE SIPS
    # =========================================================
    {
        "id":     34,
        "label":  "Celebration Circle",
        "type":   "everyone_sip",
        "effect": "everyone_sip",
        "pos":    _POS[34],
    },

    # =========================================================
    # SPACE 35 — FINISH LINE
    # First player to land here wins.
    # =========================================================
    {
        "id":     35,
        "label":  "Last Slice Summit",
        "type":   "finish",
        "effect": "finish",
        "pos":    _POS[35],
    },

]

# ---------------------------------------------------------------------------
# Derived constants
# ---------------------------------------------------------------------------
FINISH_INDEX = len(BOARD_SPACES) - 1   # = 35
SPACE_RADIUS = 32

# ---------------------------------------------------------------------------
# Token image paths
# Add custom friend images to assets/tokens/custom/ and list them below.
# ---------------------------------------------------------------------------
_BASE = os.path.dirname(os.path.abspath(__file__))
TOKENS_DIR = os.path.join(_BASE, "assets", "tokens")

DEFAULT_TOKENS = {
    "pizza":  os.path.join(TOKENS_DIR, "default", "pizza.png"),
    "beer":   os.path.join(TOKENS_DIR, "default", "beer.png"),
    "dice":   os.path.join(TOKENS_DIR, "default", "dice.png"),
    "cup":    os.path.join(TOKENS_DIR, "default", "cup.png"),
    "star":   os.path.join(TOKENS_DIR, "default", "star.png"),
    "nerf":   os.path.join(TOKENS_DIR, "default", "nerf.png"),
    "lion":   os.path.join(TOKENS_DIR, "default", "lion.png"),
    "ducky":  os.path.join(TOKENS_DIR, "default", "ducky.png"),
    "plane":  os.path.join(TOKENS_DIR, "default", "plane.png"),
    "spoon":  os.path.join(TOKENS_DIR, "default", "spoon.png"),
    "cactus": os.path.join(TOKENS_DIR, "default", "cactus.png"),
    "crown":  os.path.join(TOKENS_DIR, "default", "crown.png"),
    "taco":   os.path.join(TOKENS_DIR, "default", "taco.png"),
}

# ---------------------------------------------------------------------------
# Add your friends' custom tokens here.
# Drop the image file in assets/tokens/custom/ then add a line like:
#   "alex": os.path.join(TOKENS_DIR, "custom", "alex.png"),
# ---------------------------------------------------------------------------
CUSTOM_TOKENS = {
    # "alex": os.path.join(TOKENS_DIR, "custom", "alex.png"),
}

ALL_TOKENS  = {**DEFAULT_TOKENS, **CUSTOM_TOKENS}
TOKEN_NAMES = list(ALL_TOKENS.keys())

# ---------------------------------------------------------------------------
# Player limits
# ---------------------------------------------------------------------------
MIN_PLAYERS = 2
MAX_PLAYERS = 15

# ---------------------------------------------------------------------------
# Flavor titles shown on leaderboard
# ---------------------------------------------------------------------------
FLAVOR_TITLES = [
    (400, "The Shot Caller"),
    (280, "Grease Wizard"),
    (160, "Sip Goblin"),
    (80,  "Crust Climber"),
    (20,  "Pizza Wanderer"),
    (0,   "Dough Novice"),
]

def get_flavor_title(score: int) -> str:
    for threshold, title in FLAVOR_TITLES:
        if score >= threshold:
            return title
    return "Dough Novice"

# ---------------------------------------------------------------------------
# Menu flavor text — shows randomly on the main menu
# ---------------------------------------------------------------------------
MENU_SUBTITLES = [
    "Warning: may cause hiccups.",
    "Not responsible for morning regrets.",
    "Made on a real pizza box. Probably.",
    "For 2-15 players and questionable decisions.",
    "The board game your mom would hate.",
    "All sips are mandatory. No exceptions.",
]

# ---------------------------------------------------------------------------
# Token offsets — for when multiple players share one space
# ---------------------------------------------------------------------------
SHARED_OFFSETS = {
    1: [(0, 0)],
    2: [(-14, 0),   (14, 0)],
    3: [(-14, -8),  (14, -8),  (0, 10)],
    4: [(-14, -9),  (14, -9),  (-14, 9),  (14, 9)],
    5: [(-18, -9),  (0, -9),   (18, -9),  (-10, 9),  (10, 9)],
    6: [(-18, -9),  (0, -9),   (18, -9),  (-18, 9),  (0, 9),   (18, 9)],
    7: [(-18, -12), (0, -12),  (18, -12), (-18, 2),  (0, 2),   (18, 2),  (0, 14)],
    8: [(-18, -12), (0, -12),  (18, -12), (-18, 2),  (0, 2),   (18, 2),  (-10, 14), (10, 14)],
}

# ---------------------------------------------------------------------------
# Board JSON loading — game_boards/*.json
# ---------------------------------------------------------------------------

BOARDS_DIR = os.path.join(_BASE, "game_boards")


def list_boards() -> list:
    """Return list of dicts: {path, name, description} for every board JSON found."""
    paths = sorted(glob.glob(os.path.join(BOARDS_DIR, "*.json")))
    result = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result.append({
                "path":        path,
                "name":        data.get("name", os.path.basename(path)),
                "description": data.get("description", ""),
            })
        except Exception:
            pass
    return result


def load_board(path: str):
    """Load a board JSON and return (spaces_list, finish_index).

    Injects the on-screen 'pos' from _POS[id] for each space so the
    rest of the game code works exactly as before.
    Supports reusable components via:
      {"id": 2, "component": "karaoke"}
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    spaces = []
    for sp in data["spaces"]:
        sp = dict(sp)           # copy so we don't mutate the parsed dict
        comp_name = sp.get("component")
        if comp_name:
            base = PARTY_SQUARE_COMPONENTS.get(comp_name)
            if base:
                merged = dict(base)
                for k, v in sp.items():
                    if k != "component":
                        merged[k] = v
                sp = merged
        sp["pos"] = _POS[sp["id"]]
        spaces.append(sp)
    finish_index = len(spaces) - 1
    board_name   = data.get("name", os.path.basename(path))
    return spaces, finish_index, board_name


def get_token_offsets(n: int) -> list:
    if n in SHARED_OFFSETS:
        return SHARED_OFFSETS[n]
    offsets = []
    cols = 5
    for i in range(n):
        ox = (i % cols - cols // 2) * 12
        oy = (i // cols - 1) * 12
        offsets.append((ox, oy))
    return offsets
