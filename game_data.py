import os
import json
import glob
from board_view import make_world_positions

# ---------------------------------------------------------------------------
# Window & Display
# ---------------------------------------------------------------------------
SCREEN_W  = 1280
SCREEN_H  = 800
BOARD_W   = 870
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
PINK            = (255,  40, 180)
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
    "whirlpool": {
        "label":  "Whirlpool",
        "type":   "event",
        "effect": "whirlpool",
        "color":  (72, 185, 212),
    },
    "longest_road": {
        "label":  "Longest Road",
        "type":   "event",
        "effect": "longest_road",
        "color":  (230, 138, 72),
    },
    "beer_bitch": {
        "label":  "Beer Bitch",
        "type":   "event",
        "effect": "beer_bitch",
        "color":  (255, 105, 180),
    },
    "specialty_shot": {
        "label":  "Specialty Shot",
        "type":   "event",
        "effect": "specialty_shot",
        "color":  (230, 92, 82),
    },
    "east_west": {
        "label":  "East / West",
        "type":   "event",
        "effect": "east_west",
        "color":  (120, 170, 235),
    },
    "younger_older": {
        "label":  "Younger / Older",
        "type":   "event",
        "effect": "younger_older",
        "color":  (235, 152, 102),
    },
    "jfk": {
        "label":  "JFK",
        "type":   "event",
        "effect": "jfk",
        "color":  (212, 82, 82),
    },
    "gay_chicken": {
        "label":  "Gay Chicken",
        "type":   "event",
        "effect": "gay_chicken",
        "color":  (235, 122, 152),
    },
    "chug_speak": {
        "label":  "Chug Speak",
        "type":   "event",
        "effect": "chug_speak",
        "color":  (212, 82, 82),
    },
    "email_professor": {
        "label":  "Email a Professor",
        "type":   "event",
        "effect": "email_professor",
        "color":  (120, 170, 235),
    },
    "call_parent": {
        "label":  "Call a Parent",
        "type":   "event",
        "effect": "call_parent",
        "color":  (92, 188, 198),
    },
    "pikmin": {
        "label":  "Pikmin",
        "type":   "event",
        "effect": "pikmin",
        "color":  (92, 172, 122),
    },
    "swap_pants": {
        "label":  "Swap Pants",
        "type":   "event",
        "effect": "swap_pants",
        "color":  (175, 115, 225),
    },
    "serenade": {
        "label":  "Serenade",
        "type":   "event",
        "effect": "serenade",
        "color":  (235, 122, 152),
    },
    "jig_dance": {
        "label":  "Do a Jig / Dance",
        "type":   "event",
        "effect": "jig_dance",
        "color":  (245, 198, 62),
    },
    "lap": {
        "label":  "Lap",
        "type":   "event",
        "effect": "lap",
        "color":  (72, 208, 172),
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


def resolve_token_path(token_name: str, custom: bool = False) -> str:
    """Resolve the token image path, preferring .ico with fallback to .png."""
    sub = "custom" if custom else "default"
    folder = os.path.join(TOKENS_DIR, sub)
    ico = os.path.join(folder, f"{token_name}.ico")
    if os.path.exists(ico):
        return ico
    png = os.path.join(folder, f"{token_name}.png")
    if os.path.exists(png):
        return png
    return ico


DEFAULT_TOKENS = {
    "pizza":  resolve_token_path("pizza"),
    "beer":   resolve_token_path("beer"),
    "dice":   resolve_token_path("dice"),
    "cup":    resolve_token_path("cup"),
    "star":   resolve_token_path("star"),
    "nerf":   resolve_token_path("nerf"),
    "lion":   resolve_token_path("lion"),
    "ducky":  resolve_token_path("ducky"),
    "plane":  resolve_token_path("plane"),
    "spoon":  resolve_token_path("spoon"),
    "cactus": resolve_token_path("cactus"),
    "crown":  resolve_token_path("crown"),
    "taco":   resolve_token_path("taco"),
}

# ---------------------------------------------------------------------------
# Add your friends' custom tokens here.
# Drop the image file in assets/tokens/custom/ then add a line like:
#   "alex": resolve_token_path("alex", custom=True),
# ---------------------------------------------------------------------------
CUSTOM_TOKENS = {
    # "alex": resolve_token_path("alex", custom=True),
}

ALL_TOKENS  = {**DEFAULT_TOKENS, **CUSTOM_TOKENS}
TOKEN_NAMES = list(ALL_TOKENS.keys())

# ---------------------------------------------------------------------------
# Player limits
# ---------------------------------------------------------------------------
MIN_PLAYERS = 2
MAX_PLAYERS = 15

# ---------------------------------------------------------------------------
# Mario Party-style End-of-Game Superlative Titles & Awards
# (Calculated from match accomplishments/endurance, not score thresholds)
# ---------------------------------------------------------------------------

def calculate_player_titles(players: list, winner=None) -> dict:
    """Assign fun Mario Party-style superlative titles based on game stats.

    Titles are based on accomplishments and endurance during the match:
      - Champion (winner / reached finish)
      - Beer Bitch (designated beer bitch)
      - Marathoner (most distance traveled)
      - Sip Goblin (most sips taken)
      - Shot Caller (most shots taken)
      - Moonwalker (most backward steps / setbacks)
      - Party Animal (most events landed on)
      - Iron Liver (0 drinks / fewest total drinks)
      - Benchwarmer (most skipped turns)
      - Pub Regular / Good Sport / Pizza Fiend (default party titles)
    """
    if not players:
        return {}

    titles = {}
    assigned_players = set()

    # 1. Winner / Champion
    if winner is not None and winner in players:
        titles[winner] = "Champion"
        assigned_players.add(winner)
    else:
        for p in players:
            if getattr(p, "finished", False):
                titles[p] = "Champion"
                assigned_players.add(p)
                break

    # 2. Beer Bitch (priority if active)
    for p in players:
        if p not in assigned_players and getattr(p, "is_beer_bitch", False):
            titles[p] = "Beer Bitch"
            assigned_players.add(p)
            break

    # 3. Whirlpool Victim (still trapped in whirlpool when game ends)
    for p in players:
        if p not in assigned_players and getattr(p, "whirlpool_position", None) is not None:
            titles[p] = "Still Spinning"
            assigned_players.add(p)

    # Helper to find strictly unique best among unassigned players
    def find_best(key_fn, min_val=1):
        candidates = [p for p in players if p not in assigned_players and key_fn(p) >= min_val]
        if not candidates:
            return None
        best_val = max(key_fn(p) for p in candidates)
        best_players = [p for p in candidates if key_fn(p) == best_val]
        if len(best_players) == 1:
            return best_players[0]
        return None

    # 3. Most Distance Traveled (Marathoner)
    dist_champ = find_best(lambda p: getattr(p, "distance_traveled", 0), min_val=2)
    if dist_champ:
        titles[dist_champ] = "Marathoner"
        assigned_players.add(dist_champ)

    # 4. Most Sips (Sip Goblin)
    sip_champ = find_best(lambda p: getattr(p, "sips", 0), min_val=2)
    if sip_champ:
        titles[sip_champ] = "Sip Goblin"
        assigned_players.add(sip_champ)

    # 5. Most Shots (Shot Caller)
    shot_champ = find_best(lambda p: getattr(p, "shots", 0), min_val=1)
    if shot_champ:
        titles[shot_champ] = "Shot Caller"
        assigned_players.add(shot_champ)

    # 6. Moonwalker (most backward steps)
    back_champ = find_best(lambda p: getattr(p, "backward_steps", 0), min_val=1)
    if back_champ:
        titles[back_champ] = "Moonwalker"
        assigned_players.add(back_champ)

    # 7. Party Animal (most events landed on)
    event_champ = find_best(lambda p: getattr(p, "events_landed", 0), min_val=1)
    if event_champ:
        titles[event_champ] = "Party Animal"
        assigned_players.add(event_champ)

    # 8. Iron Liver (0 drinks among drinkers)
    zero_drinkers = [p for p in players if p not in assigned_players and (getattr(p, "sips", 0) + getattr(p, "shots", 0)) == 0]
    if len(zero_drinkers) == 1:
        titles[zero_drinkers[0]] = "Iron Liver"
        assigned_players.add(zero_drinkers[0])

    # 9. Benchwarmer (most skipped turns)
    skip_champ = find_best(lambda p: getattr(p, "total_skips", 0) or getattr(p, "skip_turns", 0), min_val=1)
    if skip_champ:
        titles[skip_champ] = "Benchwarmer"
        assigned_players.add(skip_champ)

    # 10. Fallback titles for remaining players
    default_pool = ["Pub Regular", "Party Veteran", "Pizza Fiend", "Speedster", "Good Sport", "Dice Roller"]
    pool_idx = 0
    for p in players:
        if p not in titles:
            titles[p] = default_pool[pool_idx % len(default_pool)]
            pool_idx += 1

    return titles


def get_player_title(player, all_players: list | None = None, winner=None) -> str:
    """Return the Mario Party-style superlative title for a player."""
    if not all_players:
        if winner is player or getattr(player, "finished", False):
            return "Champion"
        if getattr(player, "is_beer_bitch", False):
            return "Beer Bitch"
        if getattr(player, "whirlpool_position", None) is not None:
            return "Still Spinning"
        return "Pub Regular"
    titles = calculate_player_titles(all_players, winner=winner)
    return titles.get(player, "Pub Regular")


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


class BoardValidationError(ValueError):
    """Raised when a board JSON schema or layout is invalid."""


def validate_board_data(data: dict, source: str = "") -> list[dict]:
    if not isinstance(data, dict) or "spaces" not in data:
        raise BoardValidationError("Board must be a dict containing 'spaces'")
    spaces = data["spaces"]
    if not isinstance(spaces, list) or len(spaces) < 2:
        raise BoardValidationError("Board must have at least 2 spaces")
    if spaces[0].get("type") != "start" or spaces[-1].get("type") != "finish":
        raise BoardValidationError("Board must have distinct start and finish spaces")
    for i, sp in enumerate(spaces):
        if sp.get("id") != i:
            raise BoardValidationError(f"Non-contiguous or invalid space id: {sp.get('id')} != {i}")
        comp = sp.get("component")
        if comp and comp not in PARTY_SQUARE_COMPONENTS:
            raise BoardValidationError(f"Unknown component: {comp}")
        effect = sp.get("effect")
        value = sp.get("value")
        if effect in ("skip", "forward", "back", "sip"):
            if value is not None and value <= 0:
                raise BoardValidationError(f"Invalid value {value} for effect {effect}")
        if effect == "ladder":
            target = sp.get("target")
            if target is None or target < 0 or target >= len(spaces) or target == i:
                raise BoardValidationError(f"Invalid ladder target {target}")
    return spaces


def list_boards() -> list:
    """Return list of dicts: {path, name, description} for every valid board JSON found."""
    boards, _ = scan_boards()
    return boards


def scan_boards() -> tuple[list[dict], list[str]]:
    """Scan game_boards directory and return (valid_boards, warning_messages)."""
    paths = sorted(glob.glob(os.path.join(BOARDS_DIR, "*.json")))
    boards = []
    warnings = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    warnings.append(f"Empty board file: {os.path.basename(path)}")
                    continue
                data = json.loads(content)
            validate_board_data(data, path)
            boards.append({
                "path":        path,
                "name":        data.get("name", os.path.basename(path)),
                "description": data.get("description", ""),
            })
        except Exception as e:
            warnings.append(f"Invalid board file {os.path.basename(path)}: {e}")
    return boards, warnings


def load_board(path: str):
    """Load a board JSON and return (spaces_list, finish_index, board_name)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    spaces_data = validate_board_data(data, path)
    positions = make_world_positions(len(spaces_data))
    spaces = []
    for i, sp in enumerate(spaces_data):
        sp = dict(sp)
        comp_name = sp.get("component")
        if comp_name:
            base = PARTY_SQUARE_COMPONENTS.get(comp_name)
            if base:
                merged = dict(base)
                for k, v in sp.items():
                    if k != "component":
                        merged[k] = v
                sp = merged
        sp["pos"] = positions[i]
        spaces.append(sp)
    finish_index = len(spaces) - 1
    board_name = data.get("name", os.path.basename(path))
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
