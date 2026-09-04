import unittest

from lobby import HostLobby, LobbyError


class HostLobbyTests(unittest.TestCase):
    def setUp(self):
        self.lobby = HostLobby(["pizza", "cup", "star"])

    def test_join_preserves_order_and_keeps_session_private(self):
        alex = self.lobby.join(" Alex ", "pizza")
        self.lobby.join("Blair", "cup")
        state = self.lobby.public_state()
        self.assertEqual(["Alex", "Blair"], [p["name"] for p in state["players"]])
        self.assertNotIn("session_token", state["players"][0])
        self.assertTrue(state["can_start"])
        self.assertGreater(len(alex.session_token), 32)

    def test_duplicate_token_is_rejected_while_alternative_exists(self):
        self.lobby.join("Alex", "pizza")
        with self.assertRaisesRegex(LobbyError, "claimed"):
            self.lobby.join("Blair", "pizza")

    def test_duplicate_token_is_allowed_after_all_are_claimed(self):
        for name, token in zip(("A", "B", "C"), self.lobby.token_names):
            self.lobby.join(name, token)
        self.assertEqual("pizza", self.lobby.join("D", "pizza").token_name)

    def test_reconnect_reclaims_player_without_duplicate(self):
        player = self.lobby.join("Alex", "pizza")
        self.lobby.disconnect(player.player_id)
        reclaimed = self.lobby.reconnect(player.session_token)
        self.assertIs(player, reclaimed)
        self.assertTrue(reclaimed.connected)
        self.assertEqual(1, len(self.lobby.players))

    def test_start_requires_two_players(self):
        self.lobby.join("Alex", "pizza")
        with self.assertRaisesRegex(LobbyError, "At least two"):
            self.lobby.start()
        self.lobby.join("Blair", "cup")
        self.lobby.start()
        self.assertTrue(self.lobby.started)

    def test_host_can_remove_player_before_start(self):
        player = self.lobby.join("Alex", "pizza")
        removed = self.lobby.remove(player.player_id)
        self.assertIs(player, removed)
        self.assertEqual([], self.lobby.players)

    def test_host_can_remove_during_game_only_with_recovery_flag(self):
        first = self.lobby.join("Alex", "pizza")
        self.lobby.join("Blair", "cup")
        self.lobby.start()
        with self.assertRaises(LobbyError):
            self.lobby.remove(first.player_id)
        self.assertIs(first, self.lobby.remove(first.player_id, during_game=True))

    def test_return_to_lobby_preserves_sessions_and_reopens_setup(self):
        first = self.lobby.join("Alex", "pizza")
        self.lobby.join("Blair", "cup")
        self.lobby.start()

        self.lobby.return_to_lobby()

        self.assertFalse(self.lobby.started)
        self.assertTrue(self.lobby.public_state()["can_start"])
        self.assertIs(first, self.lobby.reconnect(first.session_token))


if __name__ == "__main__":
    unittest.main()
