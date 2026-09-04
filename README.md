# Pizza Box Party

## Setup and launch

Python 3.11 or newer is recommended. On Windows, create a virtual environment
in `.venv`, install the dependencies, and launch the game:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\play.bat
```

`play.bat` starts the fullscreen host display and its LAN controller server
together. Phones on the same private Wi-Fi can use the join URL shown during
setup. Exit from the main menu or close the host window to shut down both.

## Windows Firewall and Wi-Fi

On the first launch, allow Python on **Private networks** when Windows Firewall
prompts. Do not enable Public networks. If phones cannot open the join URL:

1. Confirm the host and phones use the same private Wi-Fi and are not on cellular data.
2. Avoid guest Wi-Fi; many guest networks block device-to-device traffic.
3. In Windows Security, allow the project's `.venv\Scripts\python.exe` through
   the firewall on Private networks.
4. Restart `play.bat` after changing networks so the displayed address refreshes.

If the host reports that no private LAN address exists, connect it to Wi-Fi or
Ethernet before restarting. Controllers disconnect cleanly when the host exits.

## Custom boards

Board files in `game_boards/*.json` may contain any ordered path of two or more
spaces. IDs must be contiguous from `0`, the first space must be the only Start,
and the final space must be the only Finish. The host generates a new horizontal
layout from the number of spaces at each game start, so JSON files do not need
screen coordinates.

Choose **Create Board** on the main menu to build a board without editing JSON.
The creator starts with five spaces, lets you add or remove middle spaces, and
offers built-in effects plus every reusable event registered by the game. Saved
boards are added to `game_boards/` and appear in the normal board selector.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The rules tests do not initialize Pygame or open a window.
