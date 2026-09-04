import json
import os
import tempfile
import unittest
from unittest.mock import patch

import game_data


def valid_board(count=36):
    spaces = [
        {"id": i, "label": f"Space {i}", "type": "normal", "effect": "none"}
        for i in range(count)
    ]
    spaces[0] = {"id": 0, "label": "Start", "type": "start", "effect": "none"}
    spaces[-1] = {"id": count - 1, "label": "Finish", "type": "finish", "effect": "finish"}
    return {"name": "Test Board", "spaces": spaces}


class BoardValidationTests(unittest.TestCase):
    def test_valid_board_is_accepted(self):
        self.assertEqual(36, len(game_data.validate_board_data(valid_board())))

    def test_variable_length_boards_are_accepted(self):
        for count in (2, 7, 80):
            with self.subTest(count=count):
                self.assertEqual(count, len(game_data.validate_board_data(valid_board(count))))

    def test_board_needs_distinct_start_and_finish_spaces(self):
        board = {
            "name": "Too Short",
            "spaces": [{"id": 0, "label": "Start", "type": "start", "effect": "none"}],
        }
        with self.assertRaises(game_data.BoardValidationError):
            game_data.validate_board_data(board)

    def test_non_contiguous_ids_are_rejected(self):
        board = valid_board()
        board["spaces"][5]["id"] = 6
        with self.assertRaises(game_data.BoardValidationError):
            game_data.validate_board_data(board)

    def test_unknown_component_is_rejected(self):
        board = valid_board()
        board["spaces"][5] = {"id": 5, "component": "missing"}
        with self.assertRaises(game_data.BoardValidationError):
            game_data.validate_board_data(board)

    def test_invalid_value_and_ladder_target_are_rejected(self):
        board = valid_board()
        board["spaces"][5].update(effect="skip", value=0)
        with self.assertRaises(game_data.BoardValidationError):
            game_data.validate_board_data(board)
        board = valid_board()
        board["spaces"][5].update(effect="ladder", target=99)
        with self.assertRaises(game_data.BoardValidationError):
            game_data.validate_board_data(board)

    def test_scan_reports_empty_files_instead_of_hiding_them(self):
        with tempfile.TemporaryDirectory() as directory:
            empty_path = os.path.join(directory, "empty.json")
            open(empty_path, "w", encoding="utf-8").close()
            good_path = os.path.join(directory, "good.json")
            with open(good_path, "w", encoding="utf-8") as file:
                json.dump(valid_board(), file)
            with patch.object(game_data, "BOARDS_DIR", directory):
                boards, warnings = game_data.scan_boards()
        self.assertEqual(["Test Board"], [board["name"] for board in boards])
        self.assertEqual(1, len(warnings))
        self.assertIn("empty.json", warnings[0])

    def test_loading_generates_fresh_positions_for_the_board_length(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "short.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump(valid_board(3), file)
            first = [(10, 20), (30, 40), (50, 60)]
            second = [(11, 21), (31, 41), (51, 61)]
            with patch.object(game_data, "make_world_positions", side_effect=(first, second)) as make_positions:
                first_spaces, first_finish, _ = game_data.load_board(path)
                second_spaces, second_finish, _ = game_data.load_board(path)

        self.assertEqual(first, [space["pos"] for space in first_spaces])
        self.assertEqual(second, [space["pos"] for space in second_spaces])
        self.assertEqual((2, 2), (first_finish, second_finish))
        self.assertEqual([unittest.mock.call(3), unittest.mock.call(3)], make_positions.call_args_list)

    def test_og_gangsters_paradise_board_loads_whirlpool_and_all_components(self):
        boards, warnings = game_data.scan_boards()
        self.assertEqual([], warnings)
        og_boards = [b for b in boards if "Original_Gangsters_Paradise" in b["path"]]
        self.assertEqual(1, len(og_boards))

        spaces, finish_index, name = game_data.load_board(og_boards[0]["path"])
        self.assertEqual("Original Gangster's Paradise", name)
        self.assertEqual(50, len(spaces))
        self.assertEqual(49, finish_index)

        # Whirlpool spaces
        self.assertEqual("whirlpool", spaces[5]["effect"])
        self.assertEqual("Whirlpool", spaces[5]["label"])
        self.assertEqual("whirlpool", spaces[39]["effect"])
        self.assertEqual("Whirlpool", spaces[39]["label"])

        # Check all spaces have valid effects and types
        for i, space in enumerate(spaces):
            self.assertEqual(i, space["id"])
            self.assertIn("effect", space)
            self.assertIn("type", space)
            self.assertIn("pos", space)

    def test_pink_color_constant_is_defined(self):
        self.assertTrue(hasattr(game_data, "PINK"))
        self.assertEqual(3, len(game_data.PINK))
        for channel in game_data.PINK:
            self.assertIsInstance(channel, int)
            self.assertGreaterEqual(channel, 0)
            self.assertLessEqual(channel, 255)


if __name__ == "__main__":
    unittest.main()
