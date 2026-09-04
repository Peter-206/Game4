import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from lobby import HostLobby
from main import Game
from models import Player


class PhoneOnlySetupTests(unittest.TestCase):
    def test_maximum_phone_roster_fits_above_setup_buttons(self):
        game = Game.__new__(Game)
        game.lobby_setup_players = [{} for _ in range(15)]

        cards = [game._setup_row_rects(index) for index in range(15)]

        self.assertTrue(all(card.bottom < 652 for card, _ in cards))
        self.assertTrue(all(card.contains(remove) for card, remove in cards))
        self.assertEqual(cards[0][0].y, cards[1][0].y)
        self.assertNotEqual(cards[0][0].x, cards[1][0].x)

    def test_game_players_come_from_authoritative_phone_lobby(self):
        lobby = HostLobby(["pizza", "cup"])
        alex = lobby.join("Alex", "pizza")
        blair = lobby.join("Blair", "cup")
        lobby.disconnect(blair.player_id)

        game = Game.__new__(Game)
        game.lan_server = SimpleNamespace(lobby=lobby)
        game.token_surfs = {"pizza": object(), "cup": object()}
        game.boards = []
        game.selected_board_idx = 0
        game.action_guard = Mock()
        game._render_board = Mock(return_value=object())
        game.add_message = Mock()

        game._start_game()

        self.assertEqual(["Alex", "Blair"], [player.name for player in game.players])
        self.assertEqual(["pizza", "cup"], [player.token_name for player in game.players])
        self.assertEqual([alex.player_id, blair.player_id],
                         [player.player_id for player in game.players])
        self.assertEqual([True, False], [player.connected for player in game.players])

    def test_in_game_remove_player_notifies_controller_and_updates_lobby(self):
        lobby = HostLobby(["pizza", "cup", "star"])
        alex = lobby.join("Alex", "pizza")
        blair = lobby.join("Blair", "cup")
        charlie = lobby.join("Charlie", "star")
        lobby.start()

        game = Game.__new__(Game)
        p1 = Player("Alex", "pizza", object())
        p1.player_id = alex.player_id
        p2 = Player("Blair", "cup", object())
        p2.player_id = blair.player_id
        p3 = Player("Charlie", "star", object())
        p3.player_id = charlie.player_id

        game.players = [p1, p2, p3]
        game.current_idx = 0
        game.rules = SimpleNamespace(remove_player=Mock(return_value=0))
        game.lan_server = SimpleNamespace(lobby=lobby, publish=Mock())
        game.pick_choices = []
        game.pick_source = None
        game.option_source = None
        game._stop_song_audio = Mock()
        game._hot_seat_sent_prompts = set()
        game.turn_id = 0
        game.camera = SimpleNamespace(focus=Mock())
        game.board_spaces = [{ "pos": (100, 100) }]
        game.add_message = Mock()

        game._remove_player(p2)

        published = [call.args[0] for call in game.lan_server.publish.call_args_list]
        self.assertTrue(any(msg.get("type") == "player_removed" and msg.get("player_id") == blair.player_id
                            for msg in published))
        self.assertEqual(2, len(lobby.players))
        self.assertEqual([alex.player_id, charlie.player_id], [p.player_id for p in lobby.players])


if __name__ == "__main__":
    unittest.main()
