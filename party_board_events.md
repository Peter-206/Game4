
# Party Board Game Event Rules

This file defines **special event tiles** for the pizza‑box party board game.  
Each tile has a clear rule and how it affects **drinks and points**.

Scoring reference:
- **Sip = 20 points**
- **Shot = 100 points**

---

# Event Tiles

## Chicks / Dicks
Rule:
All players who identify as **chicks** take a sip.  
All players who identify as **dicks** take a sip.

Effect:
- Each affected player drinks **1 sip**
- Each affected player gains **20 points**

---

## Androids / iPhones

Rule:
Players drink based on their phone type.

Effect:
- Android users take **1 sip**
- iPhone users take **1 sip**
- Each affected player gains **20 points**

---

## Shotgun

Rule:
Player must **shotgun a drink**.

Effect:
- Counts as **1 shot**
- Player gains **100 points**

---

## Double Shot / Single Shot

Rule:
Player chooses:

Option A — Single Shot  
- Take **1 shot**
- Gain **100 points**

Option B — Double Shot  
- Take **2 shots**
- Gain **200 points**

---

## Karaoke

Rule:
Player must sing something.

Constraints:
- No other players interact

Effect:
- Treated like a **shot**
- Player gains **100 points**

---

## Thunderstruck

Rule:
Open **Thunderstruck by AC/DC on YouTube** and play the song.

Game Effect:
- Everyone drinks **1 shot**
- Everyone gains **120 points**

Reasoning:
This tile is meant to be a **big party moment**.

---

## Rattlin Bog

Rule:
Open **The Rattlin Bog on YouTube**.

Game Effect:
- Everyone drinks **1 shot**
- Everyone gains **120 points**

Same style event as Thunderstruck.

---

## Mate

Rule:
Select another player to become your **Mate**.

Effect:
Whenever **either of the paired players** must drink:

- BOTH players drink
- BOTH players gain the associated points

This persists for the rest of the game unless overwritten.

Implementation Suggestion:

Store pairs like:

```
mates = {
    playerA: playerB,
    playerB: playerA
}
```

---

## Hot Seat

Rule:
Player enters the **Hot Seat**.

Effect:
- No drinks
- No points
- Just a prompt screen for discussion or questions

This is purely a **social event tile**.

---

## Drunk Driving

Rule:
Group selects the player who "lost".

UI Behavior:
- Show a selection menu of players.

Effect on selected player:
- Add **1 shot**
- Add **100 drink points**
- Then subtract **100 points** as penalty

Net score result:
- Drink still happens
- Score balances out to 0 change

But the drink still counts toward totals.

---

## New Rule

Rule:
Landing player may create a **new house rule**.

Behavior:
- A text box appears
- Player types a rule

Example:
```
Anyone who says "um" drinks.
```

System Behavior:
- The rule is stored in a **rules list**
- Accessible in the **Rules menu**

---

# Escape Menu

Press **ESC** during gameplay to open the pause menu.

Menu Options:

### Resume
Return to the game.

### Quit Early
End the game immediately.

### Rules
Open the **rules screen**.

This screen displays:
- All **New Rules**
- Any persistent rule text added during the game.
