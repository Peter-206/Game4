import asyncio
import io
import socket
import unittest
from unittest.mock import Mock, patch

from aiohttp import ClientSession, web
from PIL import Image

import lan_server


class LanAddressTests(unittest.TestCase):
    def test_private_probe_address_is_selected(self):
        probe = Mock()
        probe.getsockname.return_value = ("192.168.1.42", 50000)
        with patch.object(socket, "socket", return_value=probe), patch.object(
                socket, "getaddrinfo", return_value=[]):
            self.assertEqual("192.168.1.42", lan_server.detect_lan_ipv4())
        probe.close.assert_called_once()

    def test_active_public_wifi_route_beats_private_virtual_adapter(self):
        probe = Mock()
        probe.getsockname.return_value = ("129.21.137.191", 50000)
        with patch.object(socket, "socket", return_value=probe), patch.object(
                socket, "getaddrinfo", return_value=[
                    (socket.AF_INET, socket.SOCK_DGRAM, 0, "", ("172.19.0.1", 0)),
                ]):
            self.assertEqual("129.21.137.191", lan_server.detect_lan_ipv4())
        probe.close.assert_called_once()

    def test_missing_private_address_has_actionable_error(self):
        probe = Mock()
        probe.connect.side_effect = OSError
        with patch.object(socket, "socket", return_value=probe), patch.object(
                socket, "getaddrinfo", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "Windows Firewall"):
                lan_server.detect_lan_ipv4()

    def test_room_identity_is_unpredictable_and_readable(self):
        first, second = lan_server.RoomIdentity(), lan_server.RoomIdentity()
        self.assertNotEqual(first.token, second.token)
        self.assertNotEqual(first.code, second.code)
        self.assertGreaterEqual(len(first.token), 32)
        self.assertEqual(6, len(first.code))

    def test_join_url_renders_as_a_valid_qr_png(self):
        payload = lan_server.make_qr_png("http://192.168.1.42:8765/?room=secret")
        image = Image.open(io.BytesIO(payload))
        self.assertEqual("PNG", image.format)
        self.assertEqual(image.width, image.height)
        self.assertGreater(image.width, 100)

    def test_threaded_server_starts_and_stops_with_host_lifecycle(self):
        server = lan_server.LanServer(host="127.0.0.1", port=0)
        server.start()
        try:
            self.assertGreater(server.port, 0)
            self.assertTrue(server._thread.is_alive())
        finally:
            server.stop()
        self.assertIsNone(server._thread)

    def test_host_removal_notifies_controller_and_updates_roster(self):
        server = lan_server.LanServer(token_names=["pizza", "cup"])
        player = server.lobby.join("Alex", "pizza")
        server.publish = Mock()

        removed = server.remove_lobby_player(player.player_id)

        self.assertIs(player, removed)
        self.assertEqual([], server.lobby.players)
        removal, room_state = [call.args[0] for call in server.publish.call_args_list]
        self.assertEqual("player_removed", removal["type"])
        self.assertEqual(player.player_id, removal["player_id"])
        self.assertEqual("room_state", room_state["type"])
        self.assertEqual([], room_state["players"])

    def test_host_removal_of_disconnected_player_succeeds(self):
        server = lan_server.LanServer(token_names=["pizza", "cup"])
        player = server.lobby.join("Alex", "pizza")
        server.lobby.disconnect(player.player_id)
        server.publish = Mock()

        removed = server.remove_lobby_player(player.player_id)

        self.assertIs(player, removed)
        self.assertEqual([], server.lobby.players)
        removal, room_state = [call.args[0] for call in server.publish.call_args_list]
        self.assertEqual("player_removed", removal["type"])
        self.assertEqual(player.player_id, removal["player_id"])

    def test_host_removal_when_lobby_started_succeeds_without_error(self):
        server = lan_server.LanServer(token_names=["pizza", "cup"])
        first = server.lobby.join("Alex", "pizza")
        server.lobby.join("Blair", "cup")
        server.lobby.start()
        server.publish = Mock()

        removed = server.remove_lobby_player(first.player_id)

        self.assertIs(first, removed)
        self.assertEqual(1, len(server.lobby.players))

    def test_host_removal_of_unknown_player_returns_none(self):
        server = lan_server.LanServer(token_names=["pizza", "cup"])
        server.publish = Mock()

        removed = server.remove_lobby_player("nonexistent")

        self.assertIsNone(removed)
        server.publish.assert_not_called()


class LanServerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = lan_server.LanServer(host="127.0.0.1", port=0)
        runner = web.AppRunner(self.server.make_app())
        await runner.setup()
        self.site = web.TCPSite(runner, "127.0.0.1", 0)
        await self.site.start()
        self.runner = runner
        self.port = self.site._server.sockets[0].getsockname()[1]
        self.session = ClientSession()

    async def asyncTearDown(self):
        await self.session.close()
        await self.runner.cleanup()

    async def test_room_token_guards_controller(self):
        base = f"http://127.0.0.1:{self.port}"
        async with self.session.get(base + "/") as response:
            self.assertEqual(403, response.status)
        async with self.session.get(base + f"/?room={self.server.identity.token}") as response:
            self.assertEqual(200, response.status)
            self.assertIn("Pizza Box Party Controller", await response.text())

    async def test_assets_are_served_directly(self):
        async with self.session.get(f"http://127.0.0.1:{self.port}/styles.css") as response:
            self.assertEqual(200, response.status)
            self.assertEqual("no-store", response.headers["Cache-Control"])
            self.assertIn(".controller", await response.text())

    async def test_cardboard_assets_are_served_with_image_content_types(self):
        expected = {
            "/assets/cardboard1.png": "image/png",
            "/assets/cardboard2.jpg": "image/jpeg",
        }
        for path, content_type in expected.items():
            with self.subTest(path=path):
                async with self.session.get(f"http://127.0.0.1:{self.port}{path}") as response:
                    self.assertEqual(200, response.status)
                    self.assertEqual(content_type, response.content_type)
                    self.assertEqual("no-store", response.headers["Cache-Control"])
                    self.assertTrue(await response.read())

    async def test_websocket_accepts_valid_json_and_rejects_malformed_input(self):
        url = f"http://127.0.0.1:{self.port}/ws?room={self.server.identity.token}"
        async with self.session.ws_connect(url) as ws:
            hello = await ws.receive_json()
            self.assertEqual("connected", hello["type"])
            await ws.send_str("not-json")
            self.assertEqual("malformed_json", (await ws.receive_json())["error"])
            await ws.send_json({"type": "join", "name": "Alex", "token_name": "pizza"})
            joined = await ws.receive_json()
            self.assertEqual("joined", joined["type"])
            room_state = await ws.receive_json()
            self.assertEqual("room_state", room_state["type"])
            for _ in range(20):
                if not self.server.incoming.empty():
                    break
                await asyncio.sleep(0.01)
            payload = self.server.incoming.get_nowait()
            self.assertEqual("join", payload["type"])

    async def test_same_room_supports_distinct_controller_identities(self):
        url = f"http://127.0.0.1:{self.port}/ws?room={self.server.identity.token}"
        async with self.session.ws_connect(url) as first, self.session.ws_connect(url) as second:
            await first.receive_json()
            await second.receive_json()
            await first.send_json({"type": "join", "name": "Alex", "token_name": "pizza"})
            first_joined = await first.receive_json()
            await first.receive_json()
            await second.receive_json()
            await second.send_json({"type": "join", "name": "Blair", "token_name": "cup"})
            second_joined = await second.receive_json()
            await second.receive_json()
            await first.receive_json()

            self.assertNotEqual(first_joined["player_id"], second_joined["player_id"])
            self.assertNotEqual(first_joined["session_token"], second_joined["session_token"])
            self.assertEqual(["Alex", "Blair"], [p.name for p in self.server.lobby.players])

    async def test_socket_cannot_change_player_or_act_before_joining(self):
        url = f"http://127.0.0.1:{self.port}/ws?room={self.server.identity.token}"
        async with self.session.ws_connect(url) as unbound:
            await unbound.receive_json()
            await unbound.send_json({"type": "roll", "turn_id": 1})
            self.assertEqual("not_joined", (await unbound.receive_json())["error"])

        async with self.session.ws_connect(url) as controller:
            await controller.receive_json()
            await controller.send_json({"type": "join", "name": "Alex", "token_name": "pizza"})
            await controller.receive_json()
            await controller.receive_json()
            await controller.send_json({"type": "join", "name": "Blair", "token_name": "cup"})
            self.assertEqual("already_joined", (await controller.receive_json())["error"])
            self.assertEqual(["Alex"], [p.name for p in self.server.lobby.players])

    async def test_disconnect_and_reconnect_emit_authoritative_connection_events(self):
        url = f"http://127.0.0.1:{self.port}/ws?room={self.server.identity.token}"
        ws = await self.session.ws_connect(url)
        await ws.receive_json()
        await ws.send_json({"type": "join", "name": "Alex", "token_name": "pizza"})
        joined = await ws.receive_json()
        await ws.receive_json()
        player_id = joined["player_id"]
        session_token = joined["session_token"]
        await ws.close()
        await asyncio.sleep(0.01)

        events = []
        while not self.server.incoming.empty():
            events.append(self.server.incoming.get_nowait())
        self.assertTrue(any(event.get("type") == "connection_state"
                            and event.get("connected") is False for event in events))

        async with self.session.ws_connect(url) as reconnect:
            await reconnect.receive_json()
            await reconnect.send_json({"type": "reconnect", "session_token": session_token})
            self.assertEqual("joined", (await reconnect.receive_json())["type"])
            await reconnect.receive_json()
            await asyncio.sleep(0.01)
            events = []
            while not self.server.incoming.empty():
                events.append(self.server.incoming.get_nowait())
            self.assertTrue(any(event.get("type") == "connection_state"
                                and event.get("_player_id") == player_id
                                and event.get("connected") is True for event in events))


if __name__ == "__main__":
    unittest.main()
