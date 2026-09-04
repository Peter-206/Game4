import unittest
from unittest.mock import Mock, patch

import pygame

from game_engine import RulesEngine
from main import Game
from models import Player


class ForcedMovementResolutionTests(unittest.TestCase):
    def make_game(self, spaces):
        game = Game.__new__(Game)
        player = Player("Alex", "pizza")
        game.players = [player]
        game.board_spaces = spaces
        game.finish_index = len(spaces) - 1
        game.rules = RulesEngine(game.players, game.finish_index)
        game.last_effect = None
        game.last_effect_val = 0
        game.last_effect_msg = ""
        game.pending_interactive = None
        game._start_forced_move = Mock()
        return game, player

    def test_backward_move_schedules_animation_then_resolves_landing_effect(self):
        spaces = [
            {"id": 0, "label": "Start", "type": "start", "effect": "none"},
            {"id": 1, "label": "Sip", "type": "sip", "effect": "sip", "value": 2},
            {"id": 2, "label": "Plain", "type": "normal", "effect": "none"},
            {"id": 3, "label": "Back", "type": "back", "effect": "back", "value": 2},
        ]
        game, player = self.make_game(spaces)
        player.position = 3
        game._resolve_space(player, 4)
        game._start_forced_move.assert_called_once_with(player, 1)

        player.position = 1
        game._resolve_space(player, 4)
        self.assertEqual(2, player.sips)

    def test_forward_and_ladder_schedule_absolute_targets(self):
        spaces = [
            {"id": 0, "label": "Start", "type": "start", "effect": "none"},
            {"id": 1, "label": "Forward", "type": "forward", "effect": "forward", "value": 2},
            {"id": 2, "label": "Ladder", "type": "event", "effect": "ladder", "target": 3},
            {"id": 3, "label": "Finish", "type": "finish", "effect": "finish"},
        ]
        game, player = self.make_game(spaces)
        player.position = 1
        game._resolve_space(player, 2)
        game._start_forced_move.assert_called_with(player, 3)
        game._start_forced_move.reset_mock()
        player.position = 2
        game._resolve_space(player, 2)
        game._start_forced_move.assert_called_once_with(player, 3)

    def test_normal_sip_landing_leaves_movement_and_resolves_once(self):
        spaces = [
            {"id": 0, "label": "Start", "effect": "none", "pos": [0, 0]},
            {"id": 1, "label": "Sip", "effect": "sip", "value": 2, "pos": [1, 0]},
            {"id": 2, "label": "Finish", "effect": "finish", "pos": [2, 0]},
        ]
        game, player = self.make_game(spaces)
        game.current_idx = 0
        game.phase = "moving"
        game.anim_player = player
        game.anim_to_pos = 1
        game.anim_remaining = []
        game.anim_step_start = 0
        game.anim_step_dur = 1
        game.die_value = 1
        game.camera = Mock(settled=True)
        game.clock = Mock()
        game.clock.get_time.return_value = 16
        game.paused = False
        game.winner = None
        game.resolve_duration = 2000
        game.lan_server = Mock()
        game.lan_server.incoming.empty.return_value = True
        game._sync_player_connections = Mock()
        game._broadcast_turn_state = Mock()
        game._broadcast_game_state = Mock()
        game._broadcast_phone_prompt = Mock()
        game.add_message = Mock()

        with patch("pygame.time.get_ticks", return_value=100):
            game.update_game()
            game.update_game()

        self.assertEqual(2, player.sips)
        self.assertEqual("resolving", game.phase)
        self.assertIsNone(game.anim_player)

    def test_host_sidebar_control_skips_instead_of_rolling(self):
        game, player = self.make_game([
            {"id": 0, "label": "Start", "effect": "none"},
            {"id": 1, "label": "Finish", "effect": "finish"},
        ])
        game.players.append(Player("Blair", "cup"))
        game.current_idx = 0
        game.phase = "wait_roll"
        game.paused = False
        game.camera = Mock(settled=True)
        game.roll_btn = pygame.Rect(0, 0, 100, 100)
        game._advance_turn = Mock()
        game.add_message = Mock()

        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 50))
        game.handle_game([click])

        game._advance_turn.assert_called_once_with()
        self.assertEqual("wait_roll", game.phase)
        game.add_message.assert_called_once_with("Host skipped Alex.")

    @patch("main.make_world_positions")
    def test_board_layout_refresh_uses_the_active_space_count(self, make_positions):
        make_positions.return_value = [(110, 200), (265, 300), (420, 250)]
        game = Game.__new__(Game)
        game.board_spaces = [{"id": index} for index in range(3)]
        game._board_camera_x = 99

        game._randomize_board_layout()

        make_positions.assert_called_once_with(3)
        self.assertEqual(make_positions.return_value, [
            space["pos"] for space in game.board_spaces
        ])
        self.assertEqual(530, game.world_width)
        self.assertEqual(0, game.camera.position)
        self.assertIsNone(game._board_camera_x)

    def test_turn_change_pans_to_next_players_saved_position(self):
        game, alex = self.make_game([
            {"id": 0, "label": "Start", "effect": "none", "pos": [110, 200]},
            {"id": 1, "label": "Middle", "effect": "none", "pos": [510, 250]},
            {"id": 2, "label": "Finish", "effect": "finish", "pos": [910, 300]},
        ])
        blair = Player("Blair", "cup")
        blair.position = 2
        game.players.append(blair)
        game.rules.players = game.players
        game.current_idx = 0
        game.turn_id = 4
        game.camera = Mock()
        game.add_message = Mock()

        game._advance_turn()

        self.assertEqual(1, game.current_idx)
        self.assertEqual(5, game.turn_id)
        self.assertEqual("wait_roll", game.phase)
        game.camera.focus.assert_called_once_with(910)


if __name__ == "__main__":
    unittest.main()
