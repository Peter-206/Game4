import unittest
from unittest.mock import patch

import pygame

from main import Game, players_in_join_order
from models import Player


class PlayerOrderingTests(unittest.TestCase):
    def test_progress_and_drinks_never_change_public_or_turn_order(self):
        players = [Player("First", "pizza"), Player("Leader", "cup"), Player("Tied", "star")]
        players[0].position = 2
        players[1].position = 9
        players[2].position = 9
        players[0].shots = 10
        players[2].sips = 20

        displayed = players_in_join_order(players)

        self.assertEqual(["First", "Leader", "Tied"], [player.name for player in displayed])
        self.assertEqual(["First", "Leader", "Tied"], [player.name for player in players])

    def test_results_render_2_8_and_15_players_in_join_order(self):
        pygame.font.init()
        for count in (2, 8, 15):
            with self.subTest(count=count):
                game = Game.__new__(Game)
                game.players = [Player(f"Player {index + 1}", "pizza")
                                for index in range(count)]
                for index, player in enumerate(game.players):
                    player.position = count - index
                    player.shots = count - index
                    player.sips = index
                game.winner = None
                game.screen = pygame.Surface((1280, 800))
                game.f_title = pygame.font.Font(None, 64)
                game.f_header = pygame.font.Font(None, 38)
                game.f_label = pygame.font.Font(None, 28)
                game.f_body = pygame.font.Font(None, 24)
                game.token_lead = {}
                game._get_menu_bg = lambda: pygame.Surface((1280, 800))

                with patch("main.draw_text") as draw_text, \
                        patch("main.draw_outlined_text"), \
                        patch("main.draw_panel"), patch("main.draw_button"):
                    game.draw_end()

                rendered_names = [call.args[1] for call in draw_text.call_args_list
                                  if call.args[1].startswith("Player ")]
                self.assertEqual([player.name for player in game.players], rendered_names)


if __name__ == "__main__":
    unittest.main()
