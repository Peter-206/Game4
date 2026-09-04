"""LAN HTTP/WebSocket transport, intentionally independent of game rules."""

from __future__ import annotations

import asyncio
import io
import ipaddress
import json
import queue
import secrets
import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from aiohttp import WSMsgType, web
import qrcode

from lobby import HostLobby, LobbyError
from protocol import ProtocolError, validate_client_message


ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CONTROLLER_DIR = Path(__file__).with_name("controller")
CARDBOARD_DIR = Path(__file__).with_name("assets") / "Cardboard"
CARDBOARD_ASSETS = {
    "cardboard1.png": CARDBOARD_DIR / "cardboard1.png",
    "cardboard2.jpg": CARDBOARD_DIR / "cardboard2.jpg",
}


def _private_ipv4(value: str) -> str | None:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return None
    return value if address.version == 4 and address.is_private and not address.is_loopback else None


def _usable_ipv4(value: str) -> str | None:
    """Return a routable interface IPv4, including managed/campus networks."""
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return None
    if (address.version != 4 or address.is_loopback or address.is_unspecified
            or address.is_link_local or address.is_multicast):
        return None
    return value


def detect_lan_ipv4() -> str:
    """Return the IPv4 used by the active route, avoiding virtual adapters."""
    candidates: list[str] = []
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 80))
        # The selected source address is the interface used by the OS routing
        # table. Prefer it even when a managed network assigns a public IPv4;
        # otherwise a private WSL/Hyper-V adapter can incorrectly win below.
        if routed := _usable_ipv4(probe.getsockname()[0]):
            return routed
    except OSError:
        pass
    finally:
        probe.close()

    try:
        candidates.extend(info[4][0] for info in socket.getaddrinfo(
            socket.gethostname(), None, socket.AF_INET, socket.SOCK_DGRAM
        ))
    except OSError:
        pass
    for candidate in candidates:
        if private := _private_ipv4(candidate):
            return private
    raise RuntimeError(
        "No usable LAN IPv4 address was found. Connect the host to private Wi-Fi "
        "and allow Python through Windows Firewall. Guest networks may block devices."
    )


def make_qr_png(value: str, box_size: int = 5, border: int = 2) -> bytes:
    """Render a join URL as PNG bytes without depending on Pygame."""
    if not value:
        raise ValueError("QR value cannot be empty")
    code = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    code.add_data(value)
    code.make(fit=True)
    output = io.BytesIO()
    code.make_image(fill_color="black", back_color="white").save(output, format="PNG")
    return output.getvalue()


@dataclass(frozen=True)
class RoomIdentity:
    token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    code: str = field(default_factory=lambda: "".join(secrets.choice(ROOM_ALPHABET) for _ in range(6)))


class LanServer:
    """Serve controller assets and exchange JSON messages over WebSockets."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765,
                 token_names: list[str] | None = None,
                 on_message: Callable[[dict], None] | None = None):
        self.host = host
        self.port = port
        self.identity = RoomIdentity()
        self.on_message = on_message
        self.lobby = HostLobby(token_names or ["pizza", "cup", "star"])
        self.connections: set[web.WebSocketResponse] = set()
        self.connection_players: dict[web.WebSocketResponse, str] = {}
        self.incoming: queue.Queue[dict] = queue.Queue()
        self._runner: web.AppRunner | None = None
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self.started = threading.Event()
        self.start_error: Exception | None = None

    @property
    def join_url(self) -> str:
        return f"http://{detect_lan_ipv4()}:{self.port}/?room={self.identity.token}"

    def make_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/", self._index)
        app.router.add_get("/styles.css", self._asset)
        app.router.add_get("/app.js", self._asset)
        app.router.add_get("/assets/cardboard1.png", self._cardboard_asset)
        app.router.add_get("/assets/cardboard2.jpg", self._cardboard_asset)
        app.router.add_get("/ws", self._websocket)
        return app

    def _authorized(self, request: web.Request) -> bool:
        return secrets.compare_digest(request.query.get("room", ""), self.identity.token)

    async def _index(self, request: web.Request) -> web.StreamResponse:
        if not self._authorized(request):
            raise web.HTTPForbidden(text="Invalid or expired Pizza Box Party room link.")
        return web.FileResponse(CONTROLLER_DIR / "index.html", headers={"Cache-Control": "no-store"})

    async def _asset(self, request: web.Request) -> web.StreamResponse:
        # Assets contain no room state and may be cached by the phone browser.
        path = CONTROLLER_DIR / request.path.lstrip("/")
        if path.parent != CONTROLLER_DIR or not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Cache-Control": "no-store"})

    async def _cardboard_asset(self, request: web.Request) -> web.StreamResponse:
        path = CARDBOARD_ASSETS.get(Path(request.path).name)
        if path is None or not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Cache-Control": "no-store"})

    async def _websocket(self, request: web.Request) -> web.WebSocketResponse:
        if not self._authorized(request):
            raise web.HTTPForbidden(text="Invalid or expired room token.")
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        self.connections.add(ws)
        await ws.send_json({
            "type": "connected",
            "room_code": self.identity.code,
            "available_tokens": list(self.lobby.token_names),
        })
        try:
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    try:
                        payload = json.loads(message.data)
                    except json.JSONDecodeError:
                        await ws.send_json({"type": "error", "error": "malformed_json"})
                        continue
                    try:
                        payload = validate_client_message(payload)
                    except ProtocolError as exc:
                        await ws.send_json({"type": "error", "error": exc.code, "message": str(exc)})
                        continue
                    if payload["type"] in ("join", "reconnect"):
                        if self.connection_players.get(ws):
                            await ws.send_json({
                                "type": "error",
                                "error": "already_joined",
                                "message": "This controller is already assigned to a player.",
                            })
                            continue
                        try:
                            player = (self.lobby.join(payload.get("name"), payload.get("token_name"))
                                      if payload["type"] == "join"
                                      else self.lobby.reconnect(payload.get("session_token")))
                        except LobbyError as exc:
                            await ws.send_json({"type": "error", "error": exc.code, "message": str(exc)})
                            continue
                        self.connection_players[ws] = player.player_id
                        await ws.send_json({
                            "type": "joined",
                            "player_id": player.player_id,
                            "session_token": player.session_token,
                            "player": player.public(),
                        })
                        await self.broadcast(self.lobby.public_state())
                    elif (payload["type"] in ("roll", "event_response", "leave")
                          and not self.connection_players.get(ws)):
                        await ws.send_json({
                            "type": "error",
                            "error": "not_joined",
                            "message": "Join or reconnect this controller before playing.",
                        })
                        continue
                    routed_payload = dict(payload)
                    routed_payload["_player_id"] = self.connection_players.get(ws)
                    routed_payload["_room_token"] = self.identity.token
                    self.incoming.put(routed_payload)
                    if payload["type"] in ("join", "reconnect"):
                        self.incoming.put({
                            "type": "connection_state",
                            "_player_id": self.connection_players.get(ws),
                            "connected": True,
                        })
                    if self.on_message is not None:
                        self.on_message(routed_payload)
                elif message.type == WSMsgType.ERROR:
                    break
        finally:
            self.connections.discard(ws)
            player_id = self.connection_players.pop(ws, None)
            still_connected = player_id and player_id in self.connection_players.values()
            if player_id and not still_connected:
                self.lobby.disconnect(player_id)
                await self.broadcast(self.lobby.public_state())
                self.incoming.put({
                    "type": "connection_state",
                    "_player_id": player_id,
                    "connected": False,
                })
        return ws

    async def broadcast(self, payload: dict) -> None:
        dead = []
        for connection in tuple(self.connections):
            try:
                await connection.send_json(payload)
            except ConnectionError:
                dead.append(connection)
        self.connections.difference_update(dead)

    def publish(self, payload: dict) -> None:
        """Thread-safely broadcast authoritative host state to controllers."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), self._loop)

    def remove_lobby_player(self, player_id: str):
        """Remove a pregame player and release their phone controller session."""
        try:
            player = self.lobby.remove(player_id, during_game=True)
        except LobbyError:
            return None
        self.publish({
            "type": "player_removed",
            "player_id": player.player_id,
            "message": "The host removed you from the lobby. You can join again.",
        })
        self.publish(self.lobby.public_state())
        return player

    async def start_async(self) -> None:
        self._runner = web.AppRunner(self.make_app())
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        if site._server and site._server.sockets:
            self.port = site._server.sockets[0].getsockname()[1]

    async def stop_async(self) -> None:
        for connection in tuple(self.connections):
            await connection.close(code=1001, message=b"Host shutting down")
        self.connections.clear()
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    def start(self, timeout: float = 5.0) -> None:
        if self._thread and self._thread.is_alive():
            return

        def _loop_exception_handler(loop, context):
            exc = context.get("exception")
            if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
                return
            if isinstance(exc, OSError) and getattr(exc, "winerror", None) in (10054, 10053, 10038):
                return
            loop.default_exception_handler(context)

        def run() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.set_exception_handler(_loop_exception_handler)
            try:
                self._loop.run_until_complete(self.start_async())
            except Exception as exc:
                self.start_error = exc
                self.started.set()
                return
            self.started.set()
            self._loop.run_forever()
            self._loop.run_until_complete(self.stop_async())
            self._loop.close()

        self.started.clear()
        self.start_error = None
        self._thread = threading.Thread(target=run, name="pizza-box-lan", daemon=True)
        self._thread.start()
        if not self.started.wait(timeout):
            raise TimeoutError("LAN server did not start in time")
        if self.start_error is not None:
            raise RuntimeError(f"Could not start LAN server: {self.start_error}") from self.start_error

    def stop(self, timeout: float = 5.0) -> None:
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout)
        self._thread = None
