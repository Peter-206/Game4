# Pizza Box Party Implementation Checklist

This checklist tracks the remaining work for the LAN phone-controller conversion, horizontal scrolling board, gameplay gaps, and verification. Check an item only after its behavior is implemented and tested.

## 1. Foundation and Project Structure

- [x] Separate authoritative game rules from Pygame drawing and input handling.
- [x] Isolate LAN transport and protocol handling from the game engine.
- [x] Add the browser controller as dedicated HTML, CSS, and JavaScript assets.
- [x] Add and document required Python dependencies.
- [x] Update the Windows launcher to start the host display and LAN server together.
- [x] Document normal startup, shutdown, and firewall setup.

Completion criteria: the rules engine can be exercised without opening a Pygame window or starting a network server, and one documented command launches the complete host.

## 2. Horizontal Scrolling World

- [x] Replace the six-by-six full-board positions with editable world coordinates that progress from left to right.
- [x] Keep existing 36-space JSON boards compatible while accepting variable-length ordered boards.
- [x] Create a virtual board substantially wider than the visible board viewport.
- [x] Build a winding path that varies vertically without reversing overall horizontal progress.
- [x] Render a seamless cardboard background across the virtual world.
- [x] Add world-to-screen coordinate conversion using a horizontal camera offset.
- [x] Cull spaces, labels, path segments, arrows, and decorations outside the viewport.
- [x] Draw only the current player's token in the scrolling world.
- [x] Keep the sidebar, die, banners, prompts, and overlays fixed in screen coordinates.
- [x] Clamp the camera at the left and right world boundaries.
- [x] Frame Start and Finish intentionally without showing empty space beyond the world.
- [x] Preserve correct presentation when the fullscreen window uses letterboxing or scaling.

Completion criteria: the complete path is never visible at once, progression reads left to right, only the active token appears on the board, and no blank area appears outside either world boundary.

## 3. Camera and Movement

- [x] Add explicit camera position, target, speed, and settled state.
- [x] Smoothly pan to the next player's saved board position when the turn changes.
- [x] Keep phone Roll controls disabled until the camera settles on the active player.
- [x] Follow the active token during each animated movement step.
- [x] Keep the token near the viewport center when world boundaries allow.
- [x] Settle on the landing tile before showing or resolving its event prompt.
- [x] Animate forward, backward, ladder, and other forced movement through the same camera system.
- [x] Prevent camera updates while the game is paused.
- [x] Ensure camera movement is automatic and expose no manual scrolling controls.

Completion criteria: turn transitions and token movement remain smooth, deterministic, correctly clamped, and synchronized with input availability and event resolution.

## 4. Fixed Player Sidebar

- [x] Keep every player listed in stable turn/join order.
- [x] Show token, name, board position, shots, sips, and connection state.
- [x] Clearly highlight the current player.
- [x] Show when the camera is moving to a player and when that player may roll.
- [x] Preserve readable compact and expanded layouts for 2–15 players.
- [x] Confirm drink totals never affect ordering or winner selection.

Completion criteria: the sidebar remains readable and fixed while the world scrolls, and it always provides an accurate overview of every player.

## 5. LAN Host and Lobby

- [x] Detect a usable private LAN IPv4 address.
- [x] Start an HTTP server accessible to devices on the same network.
- [x] Start the real-time WebSocket connection used by controllers.
- [x] Generate an unpredictable temporary room token and recognizable room code.
- [x] Display a QR code and readable join URL in the Pygame lobby.
- [x] Serve the controller and its assets directly from the host computer.
- [x] Accept player name and token selection from phones.
- [x] Prevent duplicate token claims while alternatives are available.
- [x] Show connected players and connection status in the host lobby.
- [x] Disable Start Game until at least two players join.
- [x] Let the host remove players before starting.
- [x] Show useful startup and Windows Firewall troubleshooting errors.

Completion criteria: at least two phones on the same private Wi-Fi can scan the QR code, join through Safari, configure themselves, and appear in the host lobby without a cloud service.

## 6. Phone Controller

- [x] Build responsive layouts for current iPhone Safari and common Android browsers.
- [x] Implement connecting, setup, lobby, waiting, active-turn, prompt, submitted, paused, reconnecting, and game-ended states.
- [x] Show Roll Die only to the active player after the host marks the camera settled.
- [x] Disable the Roll button immediately after one valid submission.
- [x] Support confirmation, text, option, and player-selection event prompts.
- [x] Keep private text and choices hidden from the shared display until submission.
- [x] Store the private player session token in browser storage.
- [x] Reclaim the same player after refresh or a brief connection loss.
- [x] Escape all player names, rules, and other free-form content before HTML rendering.

Completion criteria: each phone exposes only valid actions for its player, reconnects without creating duplicates, and never calculates authoritative game results locally.

## 7. Authoritative Synchronization

- [x] Define and validate join, reconnect, roll, event-response, leave, room-state, turn-state, roll-result, event-prompt, event-resolved, drink-state, pause, and game-end messages.
- [x] Include room, player session, turn, and prompt identity where required.
- [x] Generate die results only on the host.
- [x] Reject out-of-turn, stale, duplicate, malformed, and paused-state actions.
- [x] Make roll and event submissions idempotent.
- [x] Broadcast authoritative player, movement, drink, and connection updates.
- [x] Pause when the current player or required prompt owner disconnects.
- [x] Restore the current turn or prompt after reconnection.
- [x] Let the host skip or remove a disconnected player safely.
- [x] Repair turn indexes and Mate relationships after player removal.
- [x] Synchronize replay, early ending, and return-to-lobby behavior.

Completion criteria: duplicate or malicious client actions cannot change state, brief disconnects recover safely, and all connected displays converge on host state.

## 8. Gameplay Rules and Content

- [x] Implement the documented skip-turn counter and automatic skipped-turn flow.
- [x] Implement ladder/jump targets with animated forced movement.
- [x] Confirm forward and backward landing behavior, including chained effects.
- [x] Map every reusable party event to its required phone interaction.
- [x] Preserve Mate propagation for individual drinks without double-counting group drinks.
- [x] Keep shots and sips as neutral informational totals only.
- [x] Validate contiguous IDs, one Start, one Finish, effects, component names, values, and jump targets for every board.
- [x] Report invalid and empty board files visibly instead of silently omitting them.
- [x] Resolve or remove the empty `Plastered Party Pals.json` board.
- [x] track every point in thunderstruck where they say thunder so we can animate the word thunder
- [x] track the points on ratlin bog where they drink
Completion criteria: every selectable board loads safely, every documented space effect resolves once, and none of the rules depend on a point system.

## 9. Board Options Audit

Each option has three checkpoints: its rule is defined, its complete behavior is implemented, and its final behavior is verified. A checked implementation means the current behavior matches the rule below, not merely that a handler with the same name exists.

### Existing basic options

- [x] **Shot — Definition:** Use the existing generic shot effect.
- [x] **Shot — Implementation:** Record one shot using the existing authoritative drink tracking.
- [x] **Shot — Verification:** Covered by the existing drink and Mate-propagation tests.
- [x] **Drink — Definition:** Use the existing generic sip effect and the quantity written on the board space.
- [x] **Drink — Implementation:** Record the configured number of sips using the existing authoritative drink tracking.
- [x] **Drink — Verification:** Covered by the existing drink and Mate-propagation tests.
- [x] **Longest Road — Definition:** Randomly choose one through five shots for the landing player.
- [x] **Longest Road — Implementation:** Generate and apply the result authoritatively on the host.
- [x] **Longest Road — Verification:** Test the one-through-five random range and resulting shot total.
- [x] **Hot Seat — Definition:** Run the existing group-question Hot Seat flow without an automatic drink.
- [x] **Hot Seat — Implementation:** Collect questions from the other controllers and let the landing player complete the answers.
- [x] **Hot Seat — Verification:** Cover question collection, completion, and skipping a disconnected participant.
- [x] **New Rule — Definition:** Let the landing player submit a persistent house rule from their phone.
- [x] **New Rule — Implementation:** Validate, store, announce, and display accepted rules.
- [x] **New Rule — Verification:** Cover valid, empty, and announcement-duration behavior.
- [x] **Finish — Definition:** End with a winner only when a player reaches Finish.
- [x] **Finish — Implementation:** Clamp movement to Finish and enter the normal winner flow.
- [x] **Finish — Verification:** Cover finish clamping and normal-win results.

### Existing options requiring correction or completion

- [x] **Chicks — Definition:** Clearly ask the landing player whether they are a girl or a guy, emphasize that they are choosing for themselves, and make the opposite group drink.
- [x] **Chicks — Implementation:** Replace the combined everyone-drinks confirmation with the private self-category choice and opposite-group instruction.
- [x] **Chicks — Verification:** Test both choices, clear self-identification wording, and one-time resolution.
- [x] **Dicks — Definition:** Use the same private girl-or-guy self-identification flow and make the opposite group drink.
- [x] **Dicks — Implementation:** Replace the combined everyone-drinks confirmation with the private self-category choice and opposite-group instruction.
- [x] **Dicks — Verification:** Test both choices, clear self-identification wording, and one-time resolution.
- [x] **Droids — Definition:** Clearly ask whether the landing player personally has an iPhone or Android and make the opposite phone group drink.
- [x] **Droids — Implementation:** Replace the combined everyone-drinks confirmation with the private phone-category choice and opposite-group instruction.
- [x] **Droids — Verification:** Test both choices, self-identification wording, and one-time resolution.
- [x] **iPhones — Definition:** Use the same private iPhone-or-Android self-identification flow and make the opposite phone group drink.
- [x] **iPhones — Implementation:** Replace the combined everyone-drinks confirmation with the private phone-category choice and opposite-group instruction.
- [x] **iPhones — Verification:** Test both choices, self-identification wording, and one-time resolution.
- [x] **Drunk Driving — Definition:** Let the landing player identify the loser from all other players or choose Random; give the selected player one shot.
- [x] **Drunk Driving — Implementation:** Add Random, exclude self, and preserve authoritative selection and drink tracking.
- [x] **Drunk Driving — Verification:** Test explicit and random selection, self-exclusion, and one-time shot assignment.
- [x] **Thunderstruck — Definition:** Play the bundled song and animate every occurrence of the word “thunder” at synchronized cue points.
- [x] **Thunderstruck — Implementation:** Keep the working countdown/playback flow and animate the complete verified floating-point-seconds cue list for the bundled 293-second recording.
- [x] **Thunderstruck — Verification:** Verify every cue against the bundled MP3 and test ordered one-time animation progression, including queued recovery after a frame jump.
- [x] **Rattlin Bog — Definition:** Play the bundled song and animate every group-drink point at synchronized cue times.
- [x] **Rattlin Bog — Implementation:** Keep the working countdown/playback flow and animate all 14 verified cumulative-chain drink cues for the bundled 328-second recording.
- [x] **Rattlin Bog — Verification:** Verify every drink cue against the bundled MP3 and test ordered one-time animation progression, including queued recovery after a frame jump.
- [x] **Mate — Definition:** Let the landing player choose any other player or Random as their Mate.
- [x] **Mate — Implementation:** Add Random to the existing player picker while preserving bidirectional pairing and clean replacement of old pairs.
- [x] **Mate — Verification:** Test explicit and random pairing, self-exclusion, replacement, removal, and drink propagation.

### New options

- [x] **JFK — Definition:** Fill the host display with “JFK” for an invisible ten-second countdown, then ask the landing player to select which other player was last to answer “FDR”; that player takes one sip.
- [x] **JFK — Implementation:** Add the automatic ten-second host presentation, player/Random selection, and authoritative sip resolution.
- [x] **JFK — Verification:** Test exact duration, absence of a visible timer, automatic transition, valid selection, and one-time sip assignment.
- [x] **Gay Chicken — Definition:** Let the landing player choose another player or Random as their opponent, run the challenge socially, and wait for completion without tracking a loser or drink.
- [x] **Gay Chicken — Implementation:** Add opponent selection, public pairing, and landing-player completion confirmation.
- [x] **Gay Chicken — Verification:** Test explicit/random opponents, self-exclusion, confirmation, and no drink change.
- [x] **Chug Speak — Definition:** Time the landing player's chug on their controller; each elapsed second becomes one required minute of speaking, and the host tells everyone the resulting speech duration without timing the speech itself.
- [x] **Chug Speak — Implementation:** Add controller start/stop timing, authoritative elapsed-time handling, and the public seconds-to-minutes result.
- [x] **Chug Speak — Verification:** Test timer controls, duplicate submissions, conversion accuracy, display, and turn completion.
- [x] **Email a Professor — Definition:** Show the instruction and wait for the landing player to confirm completion; do not compose or send email for them.
- [x] **Email a Professor — Implementation:** Add the public instruction and private completion control.
- [x] **Email a Professor — Verification:** Test confirmation ownership, reconnect restoration, and one-time completion.
- [x] **Call a Parent — Definition:** Show the instruction and wait for the landing player to confirm completion; do not initiate the call.
- [x] **Call a Parent — Implementation:** Add the public instruction and private completion control.
- [x] **Call a Parent — Verification:** Test confirmation ownership, reconnect restoration, and one-time completion.
- [x] **Pikmin — Definition:** Give the landing player a hyperlink to `https://youtu.be/uEXP0iXGwRU` and resolve the event when the link is activated.
- [x] **Pikmin — Implementation:** Add a safe external-link controller action and non-blocking resolution after activation.
- [x] **Pikmin — Verification:** Test the exact URL, safe new-window behavior on supported phones, duplicate activation, and turn advancement.
- [x] **Swap Pants — Definition:** Let the landing player choose another player or Random, publicly show the pair, and wait for the landing player's completion confirmation.
- [x] **Swap Pants — Implementation:** Add player selection and completion stages.
- [x] **Swap Pants — Verification:** Test explicit/random partners, self-exclusion, reconnect behavior, and one-time completion.
- [x] **Serenade — Definition:** Let the landing player choose another player or Random to serenade, publicly show the pair, and wait for completion.
- [x] **Serenade — Implementation:** Add recipient selection and completion stages.
- [x] **Serenade — Verification:** Test explicit/random recipients, self-exclusion, reconnect behavior, and one-time completion.
- [x] **Do a Jig / Dance — Definition:** Randomly choose either “Do a Jig” or “Dance” when landed on, display the selected challenge, and wait for completion.
- [x] **Do a Jig / Dance — Implementation:** Add authoritative variation selection and landing-player confirmation.
- [x] **Do a Jig / Dance — Verification:** Test both possible variations, public display, and one-time completion.
- [x] **Lap — Definition:** Show a controller stopwatch like Chug Speak, have the landing player complete a lap, and require them to stop and confirm on their phone.
- [x] **Lap — Implementation:** Add stopwatch controls, public running/completed state, and landing-player confirmation.
- [x] **Lap — Verification:** Test timing, confirmation ownership, reconnect restoration, and turn advancement.
- [x] **Whirlpool — Definition:** Put the player on a shared circular six-space mini-board. On each of their normal turns, their roll applies `1 = 1 sip`, `2 = 2 sips`, `3 = 1 shot`, `4 = 2 shots`, `5 = 3 shots`, or `6 = exit`; multiple players may occupy the shared Whirlpool.
- [x] **Whirlpool — Implementation:** Add persistent trapped-player state, shared circular rendering, Whirlpool-only rolls on normal turns, authoritative drink results, exit behavior, and cleanup on replay/removal.
- [x] **Whirlpool — Verification:** Test every roll result, multiple trapped players, normal turn ordering, reconnects, Mate propagation, exit, removal, and replay reset.
- [x] **Beer Bitch — Definition:** The landing player becomes the only Beer Bitch; transfer the role from any previous holder and prefix the new holder's displayed name with bright, bold pink “Beer Bitch.”
- [x] **Beer Bitch — Implementation:** Add the single persistent role, transfer logic, styled host/controller name presentation, and cleanup on removal or replay.
- [x] **Beer Bitch — Verification:** Test initial assignment, transfer, one-holder invariant, display styling, removal, reconnect, and replay reset.
- [x] **Specialty Shot — Definition:** Randomly select a different player to prepare a specialty shot for the landing player, publicly display who is pouring for whom, wait for the landing player's confirmation, and record one shot for the landing player.
- [x] **Specialty Shot — Implementation:** Add authoritative non-self random selection, public pairing, recipient confirmation, and shot tracking.
- [x] **Specialty Shot — Verification:** Test self-exclusion, all eligible makers, visible pairing, confirmation ownership, Mate propagation, and one-time resolution.
- [x] **East/West — Definition:** Randomly pick East or West and display it on the screen.
- [x] **East/West — Implementation:** Add an authoritative host choice and immediate public result with no phone response or drink change.
- [x] **East/West — Verification:** Test both possible results, exact random choices, public display, and absence of a phone prompt.
- [x] **Younger/Older — Definition:** Randomly pick Younger or Older and display it on the screen.
- [x] **Younger/Older — Implementation:** Add an authoritative host choice and immediate public result with no phone response or drink change.
- [x] **Younger/Older — Verification:** Test both possible results, exact random choices, public display, and absence of a phone prompt.

### Shared player-selection requirement

- [x] Define Random as an option for every non-self player selection, including Mate, Drunk Driving, Gay Chicken, Swap Pants, Serenade, and future equivalent events.
- [x] Implement Random as an authoritative host choice that excludes the landing player and gracefully handles games with no eligible target.
- [x] Verify explicit selection, Random selection, self-exclusion, stale/duplicate responses, disconnects, and two-player behavior across every applicable event.

Completion criteria: all 27 supplied options have an agreed rule, matching authoritative host/controller behavior, and focused regression coverage; partial legacy handlers are corrected before their implementation boxes are checked.

## 10. Host Controls and Results

- [x] Add Resume, Rules, Skip Disconnected Player, Remove Player, Correct Drink Totals, End Game Early, and Main Menu controls.
- [x] Reject controller gameplay actions while paused.
- [x] Log host corrections in the visible event history.
- [x] Display house rules and unique Mate pairs in the Rules view.
- [x] Show a winner only when a player reaches Finish.
- [x] Show neutral player recaps in join order at game end.
- [x] Ensure End Game Early never declares a false winner.
- [x] Reset drink totals, relationships, prompts, camera state, and turns for Play Again.

Completion criteria: host recovery actions cannot corrupt turn state, and normal wins, early endings, replay, and menu return all produce consistent controller and Pygame states.

## 11. Testing and Release Readiness

- [x] Add unit tests for movement, finish clamping, drinks, Mate propagation, skip, ladder, replay, and player removal.
- [x] Add protocol tests for validation, authorization, stale turns, duplicate rolls, duplicate responses, and reconnection.
- [x] Keep controllers on one shared room URL while assigning distinct per-phone sessions, visibly label each phone's player identity, and prevent a connected controller from changing players.
- [x] Fix the gameplay flow getting stuck in a repeating sip prompt/action (and audit other event types for the same repeated-resolution loop); each landing effect must resolve exactly once before the turn advances.
- [x] Remove host-computer die rolling completely; gameplay rolls must come only from the active player's phone, while the host retains a Skip Disconnected Player recovery control.
- [x] Fix phone turn ownership synchronization so the active player's controller recognizes its turn and enables Roll only after the camera settles.
- [x] Add regression tests covering one-time sip resolution, rejection/removal of host roll input, and active-phone turn/roll authorization.
- [x] Test camera interpolation, settled state, culling, Start clamp, Finish clamp, backward movement, and turn-change pans.
- [x] Test the sidebar and results with 2, 8, and 15 players.
- [ ] Test two or more simultaneous iPhones on the same Wi-Fi.
- [ ] Test Safari refresh, screen lock, temporary Wi-Fi loss, and host pause during a prompt.
- [ ] Test a guest network that blocks device-to-device traffic and verify the troubleshooting message.
- [x] Test host shutdown and confirm controllers enter a reconnecting/error state instead of freezing.
- [x] Run Python syntax checks and repository whitespace checks.
- [x] Search code and documentation for obsolete full-board, local-only-input, and point-system assumptions.
- [x] Update the main specification and event documentation to match final verified behavior.

Completion criteria: automated checks pass, the LAN flow works on real phones, the scrolling presentation stays smooth at the player limit, and documentation matches the shipped behavior.
