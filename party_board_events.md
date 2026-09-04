# Party Board Event Rules and Phone Interactions

This document defines reusable event tiles for Pizza Box Party's LAN multiplayer mode.

The Pygame host owns event state, validates responses, records neutral drink totals, and reveals public outcomes. Phones receive private instructions and submit only the action requested by the active event.

## Shared Interaction Rules

- Every interactive event receives a unique prompt identifier tied to the active turn.
- Only an intended recipient may answer a prompt.
- Duplicate, stale, or unauthorized responses are ignored with an error returned to that controller.
- While a required response is pending, normal turn progression is paused.
- Private text is not shown live on Pygame. It is revealed only after submission when the rule calls for a public reveal.
- If the responsible phone disconnects, keep the prompt pending while reconnection is possible. The host may cancel the event, skip the turn, or remove the player.
- Public Pygame messages must identify the outcome without exposing private session tokens or hidden answers prematurely.
- A Mate receives propagated drinks and scoring automatically; the Mate does not submit a second confirmation.

## Chicks / Dicks

Rule: The landing player privately identifies themselves as a girl or a guy; the opposite group drinks. The choice applies only to the current event and is not retained.

- **Phone:** Clearly asks the landing player to choose their own category.
- **Pygame:** Hides the choice until it is submitted, then announces which opposite group drinks.
- **Resolution:** The owner-only response resolves once without storing gender data or changing neutral drink totals.

## Droids / iPhones

Rule: The landing player privately identifies their own phone as iPhone or Android; the opposite phone group drinks. The choice is not retained.

- **Phone:** Clearly asks which phone the landing player personally uses.
- **Pygame:** Hides the choice until submission, then announces the opposite phone group.
- **Resolution:** The owner-only response resolves once without storing device-brand data or changing neutral drink totals.

## Shotgun

Rule: The landing player shotguns a drink.

- **Phone:** The landing player receives a completion confirmation.
- **Pygame:** Shows the Shotgun prompt and the player's name.
- **Resolution:** Add one shot after confirmation.
- **Mate:** Propagation applies.

## Double Shot / Single Shot

Rule: The landing player chooses one or two shots.

- **Phone:** Privately shows `Single Shot` and `Double Shot` options to the landing player.
- **Pygame:** Shows that the player is choosing without revealing the selection early.
- **Resolution:** Reveal the choice after submission and add one or two shots.
- **Mate:** Propagation applies to the chosen drink count.

## Karaoke

Rule: The landing player sings something. No other player input is required.

- **Phone:** Shows the private instruction and a `Performance Complete` button.
- **Pygame:** Displays the Karaoke event and player's name.
- **Resolution:** Add one shot after confirmation.
- **Mate:** Propagation applies.

## Thunderstruck

Rule: The host plays the bundled studio recording after a five-second countdown and flashes `THUNDER` at every synchronized use of “thunder” or “thunderstruck.”

- **Phone:** No response is required; controllers wait while the host runs the event.
- **Pygame:** Plays the complete song and consumes the 35 verified cues in playback order, once each.
- **Resolution:** Add one shot to every player. Do not propagate the group drink again through Mate pairs.

## Rattlin Bog

Rule: The host plays the bundled 328-second Carlyle Fraser recording after a five-second countdown. A new player drinks through each cumulative verse, beginning with its `With the ...` chain and ending at `valley-o`.

- **Phone:** No response is required; controllers wait while the host runs the event.
- **Pygame:** Flashes `DRINK!` at all 14 verified chain-start cues in playback order, once each.
- **Resolution:** Add one shot to every player. Do not propagate the group drink again through Mate pairs.

## Longest Road

Rule: The game randomly generates a number from one through five for the landing player.

- **Phone:** No response is required; the result is generated immediately.
- **Pygame:** Reveals the generated number and resulting shot count.
- **Resolution:** Add the generated number of shots to the landing player.
- **Mate:** Propagation applies to every generated shot.

## Gay Chicken

Rule: The landing player chooses any other player, or Random, as their opponent and completes the social challenge without a tracked loser or drink.

- **Phone:** The landing player selects an opponent, then receives the completion confirmation.
- **Pygame:** Shows that selection is pending, then publicly identifies the pair until completion.
- **Resolution:** Continue after the landing player confirms. No shots or sips are recorded.
- **Selection:** Random is chosen authoritatively by the host and always excludes the landing player.

## Chug Speak

Rule: The landing player times their chug; every elapsed second becomes one required minute of speaking.

- **Phone:** Shows host-backed Start and Stop controls plus a live stopwatch while running.
- **Pygame:** Shows the ready/running state, then publicly announces the measured seconds and matching speech minutes.
- **Resolution:** The host measures elapsed time, performs the one-to-one seconds-to-minutes conversion, and advances the turn after Stop.
- **Reconnects:** The active Stop prompt carries its start time so the controller can restore the visible stopwatch while the host retains authority over the result.

## Email a Professor

Rule: The landing player emails a professor themselves; the game does not compose or send the message.

- **Phone:** Shows the private instruction and an `Email Sent` completion control.
- **Pygame:** Publicly identifies the player who must complete the instruction.
- **Resolution:** Only the landing player may confirm; the pending prompt is restored after reconnect and resolves once.

## Call a Parent

Rule: The landing player calls a parent themselves; the game does not initiate the call.

- **Phone:** Shows the private instruction and a `Call Complete` completion control.
- **Pygame:** Publicly identifies the player who must complete the instruction.
- **Resolution:** Only the landing player may confirm; the pending prompt is restored after reconnect and resolves once.

## Pikmin

Rule: The landing player opens the exact Pikmin video at `https://youtu.be/uEXP0iXGwRU`.

- **Phone:** Shows an allowlisted external link that opens in a new window with `noopener noreferrer` protection.
- **Pygame:** Publicly identifies the player who must activate the video.
- **Resolution:** Activating the link submits a one-time response without waiting for the video to finish.

## Swap Pants

Rule: The landing player chooses another player, or Random, as their partner and confirms after the social challenge is complete.

- **Phone:** Shows the eligible-player picker followed by a `Pants Swapped` confirmation.
- **Pygame:** Publicly shows both selected players throughout the completion stage.
- **Resolution:** Only the landing player may confirm; no drink is recorded.

## Serenade

Rule: The landing player chooses another player, or Random, to serenade and confirms after finishing.

- **Phone:** Shows the eligible-player picker followed by a `Serenade Complete` confirmation.
- **Pygame:** Publicly shows the performer and recipient throughout the completion stage.
- **Resolution:** Only the landing player may confirm; no drink is recorded.

## Do a Jig / Dance

Rule: On landing, the host randomly chooses either `Do a Jig` or `Dance` for the landing player.

- **Phone:** Shows the selected challenge and an appropriately labeled completion control.
- **Pygame:** Publicly reveals the host-selected variation and performer.
- **Resolution:** Only the landing player may confirm, and the event resolves once without recording a drink.

## Lap

Rule: The landing player runs a lap using the stopwatch on their controller.

- **Phone:** Shows Start and Stop stopwatch controls, restores the running time after reconnect, then requires a final confirmation.
- **Pygame:** Publicly shows the ready, running, and completed states with the final elapsed time.
- **Resolution:** The host owns the elapsed-time result and advances only after the landing player confirms the stopped lap.

## Whirlpool

Rule: The landing player becomes trapped on a shared circular six-space mini-board. On each normal turn, their roll applies `1 = 1 sip`, `2 = 2 sips`, `3 = 1 shot`, `4 = 2 shots`, `5 = 3 shots`, or `6 = exit`.

- **Phone:** Uses the normal owner-only Roll control on each trapped turn.
- **Pygame:** Replaces the world view for the trapped active player with the circular mini-board and shows every trapped player's token, including shared spaces.
- **Resolution:** Rolls and drink mutations are host-authoritative; individual drinks propagate to Mates. A 6 clears trapped state without moving the main-board token.
- **Lifecycle:** Multiple players may remain trapped in normal turn order. Player reset/replay clears the state, and removal discards it with the player.

## Beer Bitch

Rule: The landing player becomes the only Beer Bitch, replacing any previous holder.

- **Phone:** Prefixes the holder's roster name with a bold bright-pink `Beer Bitch` label using safe DOM nodes.
- **Pygame:** Uses the same bright-pink prefix in the current-player banner, player sidebar, and final recap.
- **Resolution:** Assignment and transfer are host-authoritative and maintain exactly one holder while assigned.
- **Lifecycle:** Reconnect preserves the player-owned role; removing its player removes the role, and replay resets every player's role flag.

## Specialty Shot

Rule: The host randomly selects a different player to prepare a specialty shot for the landing player.

- **Phone:** The landing player sees the selected maker and receives a `Shot Taken` confirmation.
- **Pygame:** Publicly shows who is pouring for whom until confirmation.
- **Resolution:** Only the landing player may confirm. The host records one shot for that player exactly once, with normal Mate propagation.
- **Selection:** The host chooses uniformly from every non-self player.

## East / West

Rule: On landing, the host randomly chooses either `East` or `West`.

- **Phone:** No response is required.
- **Pygame:** Immediately displays the host-selected direction.
- **Resolution:** Advance normally after showing the result; no drink is recorded.

## Younger / Older

Rule: On landing, the host randomly chooses either `Younger` or `Older`.

- **Phone:** No response is required.
- **Pygame:** Immediately displays the host-selected age group.
- **Resolution:** Advance normally after showing the result; no drink is recorded.

## Mate

Rule: The landing player selects another player or Random as their Mate. Whenever either Mate later receives an individual drink, both record the same drink.

- **Phone:** Privately shows every eligible non-self player plus Random.
- **Pygame:** Shows that a selection is pending, then reveals the new pair.
- **Resolution:** Store a bidirectional pairing. Replacing a pairing cleanly removes both sides of any previous Mate relationships.
- **Exceptions:** Group-wide drinks must not double-count Mate pairs. Removing a player clears their pairing.

## Hot Seat

Rule: Every other connected controller submits one private question, then the landing player works through the submitted questions and completes the Hot Seat.

- **Phone:** Other players each receive a question field; the landing player receives the questions one at a time and a final completion control.
- **Pygame:** Shows collection and answering progress without revealing text before submission.
- **Resolution:** The host skips a missing disconnected participant safely and advances after the landing player completes the final prompt. No automatic drink is recorded.

## Drunk Driving

Rule: The landing player identifies which other player lost, or chooses Random; the selected player takes one shot.

- **Phone:** The landing player receives every eligible non-self player plus Random.
- **Pygame:** Displays that group selection is pending, then reveals the selected player.
- **Resolution:** The host resolves Random authoritatively, excludes the landing player, and applies one shot exactly once. This group-decided penalty does not propagate to a Mate.

## New Rule

Rule: The landing player creates a persistent house rule.

- **Phone:** Shows a text field with a 100-character limit and Submit/Cancel controls.
- **Pygame:** Shows that the player is writing a rule; typed text is not displayed live.
- **Resolution:** Trim, validate, escape, and store non-empty submitted text in the host's rules list, then reveal it publicly.
- **Rules menu:** The Pygame pause menu displays all accepted rules for the current game.

## Generic Custom Event

Board JSON may define an event with `"effect": "custom"` and a message containing `{name}` or `{label}` placeholders.

- **Phone:** Shows the same instruction to the landing player with a completion confirmation unless the component defines a more specific interaction.
- **Pygame:** Shows the formatted public event message.
- **Resolution:** The game waits for confirmation but does not infer drink changes from free-form text.

## Pause and Rules Menu

Press Escape on the Pygame host during gameplay to pause the authoritative game state.

Host options:

- Resume
- Rules
- Skip Disconnected Player
- Remove Player
- Correct Drink Totals
- End Game Early
- Main Menu

While paused, all controllers show a waiting state and gameplay submissions are rejected. The Rules screen displays current house rules and active Mate pairs. Host corrections must be logged in the visible event history.

## Disconnect Behavior

- A disconnected player remains reserved for reconnection through their private session token.
- If that player owns the current turn or prompt, pause progression.
- After reconnection, resend the authoritative turn or prompt state.
- The host may skip the turn, cancel the pending event, or remove the player.
- Never resolve an interactive event twice after reconnection or browser refresh.
