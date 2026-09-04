import unittest

from game_engine import PlayerState, RulesEngine


class RulesEngineTests(unittest.TestCase):
    def setUp(self):
        self.alex = PlayerState("Alex", "pizza")
        self.blair = PlayerState("Blair", "cup")
        self.engine = RulesEngine([self.alex, self.blair], finish_index=35)

    def test_movement_steps_clamp_at_finish(self):
        self.alex.position = 33
        self.assertEqual([34, 35], self.engine.movement_steps(self.alex, 6))

    def test_forced_movement_walks_forward_backward_and_clamps(self):
        self.alex.position = 5
        self.assertEqual([6, 7, 8], self.engine.movement_to(self.alex, 8))
        self.assertEqual([4, 3, 2], self.engine.movement_to(self.alex, 2))
        self.assertEqual([4, 3, 2, 1, 0], self.engine.movement_to(self.alex, -20))

    def test_relative_movement_clamps_both_boundaries(self):
        self.assertEqual(0, self.engine.move_relative(self.alex, -5))
        self.assertEqual(35, self.engine.move_relative(self.alex, 99))
        self.assertTrue(self.alex.finished)

    def test_individual_drink_propagates_to_mate(self):
        self.engine.pair_mates(self.alex, self.blair)
        self.engine.give_sips(self.alex, 2)
        self.engine.give_shots(self.blair)
        self.assertEqual((2, 1), (self.alex.sips, self.alex.shots))
        self.assertEqual((2, 1), (self.blair.sips, self.blair.shots))

    def test_group_drinks_do_not_double_count_mates(self):
        self.engine.pair_mates(self.alex, self.blair)
        self.engine.give_group_sips()
        self.engine.give_group_shots()
        self.assertEqual((1, 1), (self.alex.sips, self.alex.shots))
        self.assertEqual((1, 1), (self.blair.sips, self.blair.shots))

    def test_repairing_mates_removes_previous_pair(self):
        casey = PlayerState("Casey", "star")
        self.engine.players.append(casey)
        self.engine.pair_mates(self.alex, self.blair)
        self.engine.pair_mates(self.alex, casey)
        self.assertNotIn(self.blair, self.engine.mates)
        self.assertIs(self.engine.mates[self.alex], casey)

    def test_reset_clears_authoritative_state(self):
        self.engine.pair_mates(self.alex, self.blair)
        self.engine.give_sips(self.alex, 3)
        self.alex.position = 10
        self.alex.skip_turns = 2
        self.alex.whirlpool_position = 4
        self.alex.is_beer_bitch = True
        self.engine.reset()
        self.assertEqual((0, 0, 0, 0), (self.alex.position, self.alex.sips,
                                        self.alex.shots, self.alex.skip_turns))
        self.assertEqual({}, self.engine.mates)
        self.assertIsNone(self.alex.whirlpool_position)
        self.assertFalse(self.alex.is_beer_bitch)

    def test_negative_mutations_are_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.movement_steps(self.alex, -1)
        with self.assertRaises(ValueError):
            self.engine.give_sips(self.alex, -1)

    def test_skip_counter_is_consumed_and_player_is_bypassed(self):
        casey = PlayerState("Casey", "star")
        self.engine.players.append(casey)
        self.engine.add_skipped_turns(self.blair, 2)

        next_index, skipped = self.engine.advance_turn(0)

        self.assertEqual(2, next_index)
        self.assertEqual([self.blair], skipped)
        self.assertEqual(1, self.blair.skip_turns)

    def test_all_skipped_players_eventually_resume_rotation(self):
        self.engine.add_skipped_turns(self.alex)
        self.engine.add_skipped_turns(self.blair)

        next_index, skipped = self.engine.advance_turn(0)

        self.assertEqual(1, next_index)
        self.assertEqual([self.blair, self.alex], skipped)
        self.assertEqual([0, 0], [self.alex.skip_turns, self.blair.skip_turns])

    def test_invalid_skip_count_is_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.add_skipped_turns(self.alex, -1)

    def test_drink_totals_do_not_affect_turn_order(self):
        self.alex.shots = 99
        self.alex.sips = 999
        self.blair.shots = 0
        self.blair.sips = 0

        next_index, skipped = self.engine.advance_turn(0)

        self.assertEqual(1, next_index)
        self.assertEqual([], skipped)
        self.assertIs(self.engine.players[next_index], self.blair)

    def test_drink_totals_do_not_affect_finish(self):
        self.alex.shots = 0
        self.alex.sips = 0
        self.blair.shots = 500
        self.blair.sips = 500
        self.alex.position = 34

        self.engine.move_relative(self.alex, 1)

        self.assertTrue(self.alex.finished)
        self.assertFalse(self.blair.finished)

    def test_removing_player_repairs_turn_index_and_mates(self):
        casey = PlayerState("Casey", "star")
        self.engine.players.append(casey)
        self.engine.pair_mates(self.alex, self.blair)

        current = self.engine.remove_player(self.alex, current_index=2)

        self.assertEqual([self.blair, casey], self.engine.players)
        self.assertEqual(1, current)
        self.assertIs(casey, self.engine.players[current])
        self.assertEqual({}, self.engine.mates)

    def test_removing_current_player_selects_the_following_player(self):
        casey = PlayerState("Casey", "star")
        self.engine.players.append(casey)

        current = self.engine.remove_player(self.blair, current_index=1)

        self.assertEqual([self.alex, casey], self.engine.players)
        self.assertEqual(1, current)
        self.assertIs(casey, self.engine.players[current])


if __name__ == "__main__":
    unittest.main()
