# Pizza Box Party — Pygame Host with LAN Phone Controllers

## Project Goal

Build a local-network party board game in Python with:

- a **Pygame host application** as the shared board and authoritative game server
- a small **local web server** running on the host computer
- private **browser controllers** that players open on their phones by scanning a QR code

The experience should feel like Candy Land movement mixed with Chutes and Ladders, neutral drink tracking, and a homemade pizza-box board. It should have the easy join-and-play rhythm of a Jackbox game without requiring cloud hosting, GitHub Pages, an App Store application, or port forwarding.

All devices must be connected to the same private Wi-Fi or LAN. GitHub may store the source code but is not involved while a game is running.

## Product Principles

- The Pygame host owns all authoritative state, including the room, players, turns, die results, movement, events, drink totals, and winner.
- Phones are private controllers, not independent game clients.
- Setup happens primarily on phones. The shared screen displays the lobby and joined players.
- During normal turns, only the current player's controller exposes the **Roll Die** button.
- Event choices and typed answers happen privately on the relevant phone and are revealed on the shared display only after submission.
- Keep interaction minimal: join, configure a player, roll, and respond only when an event requires it.
- The board remains hard-coded and easy to edit through data files.
- Preserve the cardboard pizza-box aesthetic and compact player-status panel.
- Shots and sips are neutral history counters. They never determine rank, turn order, labels, or the winner.
- Present the board as a wide, left-to-right scrolling world instead of showing the entire path at once.
- Show only the active player's token in the scrolling world; keep every player represented in the fixed sidebar.

## Required Architecture

### Host application

The host computer runs one application containing:

- the Pygame shared display
- the game-state and rules engine
- an HTTP server that serves the phone controller
- a WebSocket server for real-time messages
- QR-code generation for the active room URL

The server must listen on the host's LAN address rather than only `localhost`. On startup, detect a usable local IPv4 address and display both the join URL and its QR code. A typical URL is:

```text
http://192.168.1.42:8080/join?room=ABCD&token=<temporary-room-token>
```

The room token must be unpredictable and valid only for the current hosted session. Do not rely on the room code alone as authorization.

### Phone controller

The controller is a responsive HTML/CSS/JavaScript page served directly by the host. It must work in current iPhone Safari and common Android browsers without installation.

Controller states:

1. Connecting
2. Player setup
3. Lobby waiting
4. Waiting for another player
5. Active turn with Roll Die
6. Private event prompt or choice
7. Submitted/waiting
8. Host paused
9. Reconnecting
10. Game ended

The controller should display only information useful to that player. The scrolling board view and player-status panel remain on Pygame.

### State authority and synchronization

- Clients submit intentions such as `join`, `roll`, or `event_response`.
- The host validates every action, mutates state, and broadcasts the resulting state.
- The phone must never choose its own die result, calculate movement, change drink totals, or decide whether an action is legal.
- Reject out-of-turn rolls, duplicate responses, stale actions, invalid room tokens, and gameplay actions while paused.
- Give each joined player a private session token stored in the browser so a refresh or brief Wi-Fi interruption can reclaim the same player slot.
- Do not create a duplicate player during reconnection.

## Network Interface

The exact Python framework may be chosen during implementation, but the behavior below is required.

### HTTP responsibilities

- serve the controller page and its static assets
- expose a lightweight health/room-status endpoint
- serve the active room join route embedded in the QR code

### WebSocket message categories

Client to host:

- `join`: room token, display name, and selected token
- `reconnect`: room token and saved player session token
- `roll`: player session identity and current turn identifier
- `event_response`: prompt identifier and submitted text, option, player selection, or confirmation
- `leave`: voluntary departure from the lobby

Host to clients:

- `room_state`: lobby status and available tokens
- `player_joined` / `player_left`
- `game_started`
- `turn_state`: current player and turn identifier
- `roll_result`
- `event_prompt`: private prompt sent only to intended recipients
- `event_resolved`: public-safe result
- `drink_state`: neutral shot and sip totals in stable player order
- `paused` / `resumed`
- `game_ended`
- `error`

Every state-changing client message must identify the room, player session, and relevant turn or prompt. The server must make repeated submissions idempotent or reject them safely.

## Required Screens

### 1. Main Menu

- title/logo area
- Host Game button
- Quit button
- cardboard/pizza-box visual theme

### 2. Host Lobby

- dynamically generated QR code and readable LAN URL
- temporary room code for recognition and troubleshooting
- list of connected players with names, connection status, and token previews
- configured minimum and maximum player counts
- Start Game and Back buttons
- Start Game disabled until at least two players have joined
- host ability to remove a player before starting

Players configure themselves on their phones. The Pygame host should not require typing every player's name.

### 3. Main Game Screen

- horizontally scrolling board viewport showing only part of a wide virtual world
- active player's token centered when possible; other tokens remain hidden from the world view
- automatic camera movement with no manual scrolling controls
- clear current-player indicator
- latest die result and movement animation
- event/message banner
- fixed compact sidebar listing every player in stable turn order
- connection indicator for each player
- no ordinary host Roll Die button; rolling belongs to the current player's phone
- discreet host controls available through the pause menu

### 4. End Screen

- winner banner
- neutral player recap in join order
- sip and shot totals for each player
- Play Again and Main Menu buttons
- Play Again returns connected controllers to a fresh lobby or setup-ready state

## Host Safety Controls

Press Escape during gameplay to open a host-only pause menu with:

- Resume
- Rules
- Skip Disconnected Player
- Remove Player
- Correct Drink Totals
- End Game Early
- Main Menu

Normal gameplay pauses if the current player disconnects. Allow that player to reconnect using the saved session token. The host may then skip the turn or remove the player. Removing a player must safely repair turn order and persistent relationships such as Mate pairings.

Ending early must produce a clearly labeled early-results screen and must not falsely declare the first player as the winner.

## Player Setup on Phones

Each player:

1. scans the host QR code
2. enters a display name
3. selects an available image token
4. submits and waits in the lobby

Requirements:

- blank names become `Player 1`, `Player 2`, and so on
- names have a documented length limit and are escaped before display
- token choices show image previews
- claimed tokens become unavailable to other players
- the host may allow duplicates only when there are more players than available tokens
- the lobby supports at least 2–8 players; a higher tested limit may be configured if every screen remains usable

Built-in token images live in `assets/tokens/default/`. Custom images can be added to `assets/tokens/custom/` and registered in the content configuration.

## Turn Flow

1. The host identifies the current player and generates a unique turn identifier.
2. Pygame pans horizontally to that player's world position.
3. After the camera settles, that player's phone enables Roll Die; all other phones show a waiting state.
4. The player taps Roll Die once.
5. The host validates the request and generates a random result from 1 to 6.
6. Pygame animates the die, active token, and following camera movement.
7. The camera settles on the landing space and the host resolves its effect.
8. If interaction is required, the host sends a private prompt to the appropriate phone or phones and waits for valid responses.
9. Pygame reveals the resolved outcome and updates drink totals.
10. The host advances to the next connected player and begins the next camera pan.

Repeated taps or duplicate WebSocket messages must never produce multiple rolls. A roll that reaches or passes the final tile clamps to the finish.

## Board Data

Boards are ordered paths of two or more spaces and should remain manually editable in `game_boards/*.json`. Each game generates a fresh horizontal layout with constant X spacing and gently randomized Y positions based on the board's space count.

The virtual board must be wider than the viewport and progress consistently from left to right. The path may move modestly up and down for visual variety but must not reverse its overall horizontal progression. World coordinates remain separate from screen coordinates; the camera transform determines where visible spaces are drawn.

Example:

```json
{
  "id": 7,
  "label": "Nacho Notch",
  "type": "sip",
  "effect": "sip",
  "value": 2
}
```

Boards may reference reusable event components:

```json
{"id": 12, "component": "karaoke"}
```

Supported automatic effects should include:

- `start`
- `normal` / `none`
- `sip`
- `shot`
- `everyone_sip`
- `forward`
- `back`
- `skip`
- `ladder`
- `finish`

Interactive party events may request a confirmation, text response, option choice, or player selection. Their phone and shared-screen behavior is defined in `party_board_events.md`.

All non-self player pickers include `Random`. The host—not the controller—resolves that option from the eligible players, always excludes the landing player, and skips the event cleanly if no target remains. Song events are also host-authoritative: Thunderstruck plays the bundled 293-second recording with 35 synchronized word cues, and Rattlin' Bog plays the bundled 328-second Carlyle Fraser recording with 14 synchronized cumulative-verse drink cues. Rendering stalls queue overdue cues so each animation is still shown once in order.

Validate every board before offering it in the lobby. A valid board must contain an ordered, contiguous set of supported space IDs, exactly one start, exactly one finish, valid component names, valid effect data, and valid jump targets. Invalid or empty JSON files should produce a visible host warning rather than silently disappearing.

## Player Model and Scoring

Each player stores:

- stable player/session identifier
- display name
- token name and image
- connection status
- board position
- skip-turn count
- shots
- sips
- finished status

Drink totals are informational only and must not affect turn order, placement, labels, or the winner.

## Player Status Panel

The shared-screen player-status panel and neutral end recap must:

- preserve stable turn/join order regardless of drink totals
- show token, name, board position, shots, sips, and connection state
- highlight the current player
- remain readable for the configured maximum number of players
- avoid covering the board

The sidebar remains fixed while the board moves behind its viewport. It is the persistent overview for players whose tokens are not currently drawn in the world.

## Scrolling Camera

- Track a horizontal camera offset independently from game state and board-space coordinates.
- Smoothly ease toward the active player's current position instead of snapping.
- Follow each step of token movement while keeping the active token near the viewport center.
- Finish turn-change camera movement before enabling the next player's controller.
- Clamp at the world's left and right edges so Start and Finish receive intentional framing.
- Keep the active space, nearby path, and enough forward context visible whenever world boundaries allow.
- Draw only visible spaces, labels, path segments, and decorations.
- Keep the sidebar, die, messages, event prompts, and pause overlays in screen coordinates.
- Recalculate the viewport and camera bounds correctly for fullscreen scaling.

Phone controllers may show the player's own drink totals but do not need to reproduce the full player list.

## Visual Style

Keep the existing homemade pizza-box direction:

- cardboard brown and tan palette
- thick marker outlines
- uneven, hand-filled spaces
- casual doodles, grease marks, tape, cheese drips, cups, and pizza slices
- playful, slightly crooked labels
- clean enough to read across a room

Avoid a polished fantasy-board or sleek corporate-dashboard appearance.

## Security and LAN Constraints

- Bind only to appropriate local interfaces by default.
- Treat all browser input as untrusted and validate lengths, types, room membership, turn ownership, and prompt ownership.
- Escape player names and free-form rules before rendering them in HTML.
- Use unpredictable room and player session tokens.
- Do not expose filesystem paths or arbitrary file-serving routes.
- Do not require microphone, camera, location, or other privileged browser APIs. The Camera app is used only to scan the QR code.
- Clearly explain that guest Wi-Fi client isolation may prevent phones from reaching the host.
- Provide a helpful Windows Firewall/network troubleshooting message when the server cannot be reached.
- The game ends if the host application closes or the computer sleeps; clients should show a reconnecting state rather than freezing.

## Recommended Project Structure

```text
project/
├── main.py
├── game_data.py
├── models.py
├── game_engine.py
├── network_server.py
├── protocol.py
├── game_boards/
├── web/
│   ├── index.html
│   ├── controller.js
│   └── controller.css
├── assets/
│   └── tokens/
│       ├── default/
│       └── custom/
└── tests/
```

Keep Pygame drawing, game rules, network transport, and browser UI separate. The game engine should be testable without opening a Pygame window or starting a real network server.

## Acceptance Criteria

- A host can create a room and see a working QR code and LAN URL.
- At least two iPhones on the same Wi-Fi can join through Safari without installing an app.
- Each phone can set its own name and token.
- Only the current player can successfully roll.
- Pygame animates the server-generated result and remains authoritative.
- The shared display shows a smooth left-to-right camera view rather than the complete board.
- Only the active token appears in the world view, while the fixed sidebar continues to show all players.
- Turn controls remain disabled until the camera has centered on the active player.
- Camera movement follows token steps, clamps correctly at Start and Finish, and never exposes blank space beyond the world.
- Private event prompts appear only on intended controllers and reveal appropriate results on Pygame after submission.
- Refreshing a controller reconnects to the same player instead of duplicating it.
- A disconnected current player pauses the turn and can reconnect or be skipped/removed by the host.
- Shots, sips, movement, Mate propagation, and player status remain synchronized across all clients.
- Invalid or malicious client actions cannot alter game state.
- All configured screens remain readable at the supported player limit.
- The game requires no cloud service, GitHub Pages deployment, port forwarding, or phone application.

## Non-Goals

Do not build:

- public internet matchmaking
- cloud-hosted rooms
- GitHub Pages controller hosting
- native iOS or Android applications
- peer-to-peer authoritative phone clients
- heavy strategy or a large minigame collection
- gameplay that requires constant phone attention

## Final Instruction to the Coding Assistant

Build Pizza Box Party as a **Pygame shared host with LAN browser controllers**. The host computer serves the controller, owns all game state, and displays a horizontally scrolling board focused on the active player. Phones join through a dynamic QR code, provide private player input, and expose actions only when authorized by the host. Keep the all-player sidebar fixed while the camera moves through the board world. Favor reliability, clear state ownership, reconnection support, editable content, and low-friction party play over unnecessary complexity.
