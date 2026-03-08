# Pygame Party Board Game Prompt

## Project Goal

Build a **single-device local party board game in Python using Pygame**.

The game should feel like a mix of:
- **Candy Land** movement and board progression
- **Snakes and Ladders / Chutes and Ladders** style jumps and setbacks
- a **drinking game scoreboard** based on shots and sips
- a **homemade pizza-box cardboard board game aesthetic**

This is **not** a networked or multi-device game. Everything happens on **one screen on one computer**. The only real player input during gameplay should be:
- entering player names before the game starts
- picking a player icon/token before the game starts
- clicking a **Roll Die** button during the game

There should be **very little gameplay interaction beyond rolling**. The game flow should be simple, readable, and party-friendly.

---

## Core Design Requirements

### High-level concept

Make a local Pygame board game where players:
1. start at a main menu
2. choose or confirm the number of players
3. enter names
4. pick token icons/images
5. start the game
6. take turns rolling a die
7. move across a hard-coded board
8. trigger space effects like sips, shots, ladders, setbacks, and special events
9. accumulate score automatically
10. finish at an end screen with rankings

### Important design constraints

- The board should be **hard coded**, not procedurally generated.
- The board data should be **very easy to edit manually in code**.
- Token pieces should be **image-based**, not just colored circles.
- There should be **built-in default token choices**, but the code should also make it easy to add custom images manually.
- The interface should be **clean and readable**, not overloaded with controls.
- The leaderboard should be **compact and stylized**, with personality, but should not take over the screen.
- The board should visually feel like it was drawn on a **pizza box / cardboard game board**.

---

## Technical Requirements

### Language and framework
- Python 3
- Pygame

### Recommended architecture
Structure the project cleanly. Keep the data easy to edit.

Suggested file structure:

```text
project/
├─ main.py
├─ game_data.py
├─ models.py
├─ ui.py
├─ assets/
│  ├─ board/
│  ├─ tokens/
│  │  ├─ default/
│  │  └─ custom/
│  ├─ fonts/
│  └─ icons/
```

A simplified version is also acceptable if the code stays readable.

---

## Required Game States / Screens

Implement the game using clear screen states.

### 1. Main Menu
This should be the first screen.

Requirements:
- title/logo area
- buttons for:
  - Play
  - Quit
- optional subtitle or flavor text
- visual theme already reflects the cardboard / pizza box aesthetic

### 2. Player Setup Screen
This is where players configure the game.

Requirements:
- allow choosing number of players using a simple method
  - support at least 2–8 players
- for each active player slot:
  - editable name input field
  - token/icon picker
  - visible token preview
- if a name is left blank, assign default names like:
  - Player 1
  - Player 2
  - etc.
- Start Game button
- Back button to return to menu

Gameplay should require **minimal input later**, so this setup screen is where most customization happens.

### 3. Main Game Screen
This is the primary play screen.

Requirements:
- large visible board
- player tokens placed on current board spaces
- clear indication of whose turn it is
- Roll Die button
- display for latest die roll
- short event/message banner describing what happened
- compact leaderboard
- optional subtle decorative elements

### 4. End Screen
Shown when someone wins.

Requirements:
- winner banner
- final rankings
- show score plus sip/shot totals
- buttons for:
  - Play Again
  - Main Menu

---

## Gameplay Rules

### Turn flow
Each turn should be as simple as possible:
1. show current player
2. player clicks Roll Die
3. die result is generated randomly from 1 to 6
4. current player moves forward
5. landing space effect resolves automatically
6. score and stats update automatically
7. turn passes to next player

### Minimal input requirement
Once the game starts, the only user input during turns should effectively be:
- click/tap Roll Die
- optional click on simple buttons like Continue if needed, but avoid unnecessary interaction

Do **not** design the game around complicated player choices during turns.

---

## Board Requirements

### Hard-coded editable board
The board should be defined as a **manually editable list of spaces** in one obvious place, such as `game_data.py`.

Each space should be easy to edit by changing:
- label/name
- type
- position on screen
- effect values
- target spaces for ladders or setbacks

Recommended structure:

```python
BOARD_SPACES = [
    {"id": 0, "label": "Pizza Box Start", "type": "start", "pos": (100, 600)},
    {"id": 1, "label": "Crust Corner", "type": "sip", "value": 1, "pos": (180, 580)},
    {"id": 2, "label": "Grease Pit", "type": "back", "value": 2, "pos": (260, 550)},
    {"id": 3, "label": "Cheese Lift", "type": "ladder", "target": 8, "pos": (330, 510)},
]
```

### Board movement model
The board should function like a path of ordered spaces.

Movement logic:
- players move forward by the die result
- landing on special spaces triggers effects
- board spaces are indexed in order
- last space is the finish/win condition

### Recommended space types
Support at least these:
- `start`
- `normal`
- `sip`
- `shot`
- `ladder`
- `back`
- `skip`
- `finish`

Optional fun space types:
- `forward`
- `everyone_sip`
- `double_roll`
- `swap`
- `event`

---

## Scoring System

Track actual drinking stats and derive score from them.

### Scoring rules
- each **shot** = 100 points
- each **sip** = 20 points

Each player should store:
- shots count
- sips count
- score property calculated from those values

Recommended structure:

```python
class Player:
    def __init__(self, name, token_name, token_image):
        self.name = name
        self.token_name = token_name
        self.token_image = token_image
        self.position = 0
        self.skip_turns = 0
        self.shots = 0
        self.sips = 0

    @property
    def score(self):
        return self.shots * 100 + self.sips * 20
```

### Important note
Do not just add arbitrary points directly when possible. Prefer updating `shots` and `sips`, then calculate score from those.

---

## Leaderboard Requirements

The leaderboard should be:
- visible during gameplay
- compact
- stylish and funny
- not too large
- easy to read at a glance

### Recommended leaderboard contents per row
- token image thumbnail
- player name
- score
- tiny stat line showing shots and sips
- optional funny title

Example compact row concept:
- token | Alex | 240
- small text underneath: `2 shots • 2 sips`
- optional title: `Shot Caller`

### Leaderboard behavior
- sort players by score descending
- update every turn
- place it in a sidebar or narrow area
- do not let it consume too much screen space

### Characterized title system
Give each player a short flavor title based on their stats or game position.

Examples:
- Shot Caller
- Sip Goblin
- Crust Climber
- Pizza Wanderer
- Grease Wizard
- Ladder Rat

This should add personality without needing much extra UI space.

---

## Token / Piece Requirements

### Image-based pieces
Tokens should be images, not plain shapes.

### Built-in token selection
Provide around 5 default token choices stored in assets.
Examples could be:
- pizza slice
- soda cup
- beer mug
- dice
- little mascot

### Easy custom image support
The code should also make it easy to add custom token images manually.

Recommended design:
- `assets/tokens/default/` for built-in choices
- `assets/tokens/custom/` for manually added friend images
- token choices defined in a clearly editable dictionary in `game_data.py`

Example:

```python
DEFAULT_TOKENS = {
    "pizza": "assets/tokens/default/pizza.png",
    "beer": "assets/tokens/default/beer.png",
    "dice": "assets/tokens/default/dice.png",
    "cup": "assets/tokens/default/cup.png",
    "slice": "assets/tokens/default/slice.png",
}

CUSTOM_TOKENS = {
    "alex": "assets/tokens/custom/alex.png",
    "sam": "assets/tokens/custom/sam.png",
}
```

### Token picker behavior
On the setup screen, each player should be able to:
- cycle left/right through available token options
- see the selected token preview
- avoid duplicate tokens if possible, unless duplicates are explicitly allowed

### Token rendering on the board
When multiple players occupy the same space:
- offset token draw positions slightly so they do not overlap perfectly
- keep token size reasonable and readable

---

## Board Visual Style Requirements

### Overall visual theme
The board should feel like a homemade board game drawn on a pizza box.

The look should be inspired by:
- cardboard texture
- pizza box brown/tan color palette
- marker-drawn outlines
- uneven hand-made shapes
- casual doodles
- slightly crooked labels
- taped-on or scribbled decoration

### Style goals
The board should look:
- playful
- homemade
- party-friendly
- intentional, not sloppy

### Important visual constraint
Avoid making it look like a polished fantasy board or a sleek digital UI. It should specifically evoke **cardboard land / pizza box game night energy**.

### Suggested visual elements
- cardboard background texture
- thick black marker path outlines
- colored spaces that look hand-filled
- rough arrows for ladders / jumps
- hand-drawn stars, grease marks, pizza doodles, cups, arrows, cheese drips
- title text like it was written with marker

### Suggested board location names
Use silly themed names such as:
- Pizza Box Start
- Crust Corner
- Grease Pit
- Sauce Slide
- Cheese Lift
- Keg Keep
- Flat Soda Swamp
- Topping Trail
- Last Slice Summit

These should be editable directly in the board data.

---

## UI / UX Requirements

### Input philosophy
This should be a **low-friction couch / party game**. Keep controls simple.

### During active gameplay, avoid:
- deep menus
- multiple actions per turn
- too many popups
- complicated choices
- requiring keyboard input after the setup screen

### During gameplay, prefer:
- one obvious Roll Die button
- readable turn banner
- quick auto-resolution of space effects
- short event text
- compact leaderboard

### Setup usability
The player setup screen should be very obvious and fast to use.

Each player row should ideally contain:
- player label
- name input box
- token preview
- left/right arrows or simple selector for token choice

---

## Logic Requirements

### Skip turns
Support a `skip_turns` counter for players.
If a player has `skip_turns > 0`:
- decrement it on their turn
- show a message indicating they lost a turn
- pass to next player automatically

### Win condition
A player wins when they reach the final board space.
You may allow exact landing or allow any roll that passes the end to clamp to the final tile.
Keep the logic simple and party-friendly.

### Space resolution examples
Suggested behaviors:
- `sip`: add sip count
- `shot`: add shot count
- `ladder`: move player to target
- `back`: move player backward by value
- `skip`: increase `skip_turns`
- `normal`: no special effect

### Message system
Maintain a short text message describing the last event.
Examples:
- `Alex rolled a 4 and landed on Grease Pit.`
- `Sam takes 2 sips.`
- `Chris climbed Cheese Lift to space 12!`

This message should be visible in the game UI without taking too much space.

---

## Recommended Implementation Details

### State management
Use clear game states, for example:

```python
MENU = "menu"
SETUP = "setup"
GAME = "game"
END = "end"
```

### Main loop idea
Use one main loop and branch behavior by state.
Each state should have separate functions/methods for:
- handling events
- updating
- drawing

### Data separation
Keep **content/config data** separate from gameplay logic.

Content/data examples:
- board space definitions
- token file paths
- default player limits
- screen constants
- colors

Logic examples:
- turn advancement
- rolling die
- resolving spaces
- drawing screens

This separation is important because the board must be easy to modify later.

---

## Optional Polish Features

These are nice extras if implementation stays manageable:
- die roll animation
- subtle token movement animation between spaces
- highlighted current player row on leaderboard
- simple sound effects
- fake masking tape corner graphics
- paper/cardboard drop shadows
- tiny doodle icons for shots and sips
- random flavor text on menu screen

These are optional. Do not let polish overcomplicate the core game.

---

## Non-Goals / Things to Avoid

Do **not** build this as:
- an online multiplayer game
- a mobile controller game
- a heavy strategy game
- a complex minigame collection
- a cluttered UI with too many actions

Do **not** require much gameplay input beyond:
- setup names/icons
- clicking Roll Die

Keep it straightforward and fun.

---

## Deliverable Expectations

Generate code for a Pygame project that includes:
- a main menu
- a player setup screen with name input and token selection
- a hard-coded editable board
- image-based tokens
- turn-based die rolling
- automatic space resolution
- score based on 100 per shot and 20 per sip
- compact stylized leaderboard
- cardboard/pizza-box inspired board visuals
- end screen with winner and rankings

The code should be organized and readable enough that I can easily:
- edit the board layout
- add/remove token images
- change player limits
- rename spaces
- change tile effects
- restyle the theme later

---

## Final Instruction to the Coding Assistant

Build this as a **single-device Pygame party board game** with strong emphasis on:
- low-friction local play
- highly editable hard-coded content
- image-based player tokens
- compact, flavorful UI
- pizza-box cardboard board aesthetics
- minimal gameplay input beyond setup + rolling the die

Favor clarity, structure, and editability over unnecessary complexity.

