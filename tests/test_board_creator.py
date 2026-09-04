import json
import os
import tempfile
import unittest

import pygame

import main
from board_creator import (
    BoardCreatorError,
    BoardDraft,
    MIN_CREATOR_SPACES,
    available_event_options,
    event_key_for_space,
    save_new_board,
)
from game_data import PARTY_SQUARE_COMPONENTS, validate_board_data


class BoardDraftTests(unittest.TestCase):
    def test_default_draft_has_locked_endpoints_and_five_spaces(self):
        draft = BoardDraft.create_default()
        self.assertEqual(MIN_CREATOR_SPACES, len(draft.spaces))
        self.assertEqual(list(range(5)), [space["id"] for space in draft.spaces])
        self.assertEqual(("start", "finish"),
                         (draft.spaces[0]["type"], draft.spaces[-1]["type"]))
        self.assertFalse(draft.dirty)

    def test_add_and_remove_keep_finish_last_and_renumber(self):
        draft = BoardDraft.create_default()
        added = draft.add_space()
        draft.set_space_field(added, "label", "Temporary")
        self.assertEqual(4, added)
        self.assertEqual("finish", draft.spaces[-1]["type"])
        self.assertEqual(list(range(6)), [space["id"] for space in draft.spaces])

        selected = draft.remove_space(added)
        self.assertEqual(3, selected)
        self.assertEqual(list(range(5)), [space["id"] for space in draft.spaces])
        with self.assertRaises(BoardCreatorError):
            draft.remove_space(1)

    def test_start_finish_cannot_be_removed_or_retyped(self):
        draft = BoardDraft.create_default(6)
        for index in (0, len(draft.spaces) - 1):
            with self.subTest(index=index):
                with self.assertRaises(BoardCreatorError):
                    draft.remove_space(index)
                with self.assertRaises(BoardCreatorError):
                    draft.set_event(index, "sip", PARTY_SQUARE_COMPONENTS)

    def test_every_registered_component_appears_and_serializes(self):
        options = available_event_options(PARTY_SQUARE_COMPONENTS)
        option_keys = {option.key for option in options}
        for key, component in PARTY_SQUARE_COMPONENTS.items():
            with self.subTest(component=key):
                self.assertIn(f"component:{key}", option_keys)
                draft = BoardDraft.create_default()
                draft.set_event(1, f"component:{key}", PARTY_SQUARE_COMPONENTS)
                self.assertEqual(key, draft.spaces[1]["component"])
                self.assertEqual(component["label"], draft.spaces[1]["label"])
                self.assertEqual(f"component:{key}", event_key_for_space(draft.spaces[1]))

    def test_builtin_events_receive_their_required_fields(self):
        for key in ("normal", "sip", "shot", "everyone_sip", "forward",
                    "back", "skip", "ladder", "custom"):
            with self.subTest(event=key):
                draft = BoardDraft.create_default()
                draft.set_metadata("name", "Event Board")
                draft.set_event(1, key, PARTY_SQUARE_COMPONENTS)
                data = draft.validate(validate_board_data)
                self.assertEqual(5, len(data["spaces"]))
                self.assertEqual(key, event_key_for_space(draft.spaces[1]))

    def test_creator_specific_invalid_fields_are_rejected(self):
        draft = BoardDraft.create_default()
        with self.assertRaisesRegex(BoardCreatorError, "name"):
            draft.validate(validate_board_data)

        draft.set_metadata("name", "Invalid Board")
        draft.set_event(1, "sip", PARTY_SQUARE_COMPONENTS)
        draft.set_space_field(1, "value", "")
        with self.assertRaisesRegex(BoardCreatorError, "positive"):
            draft.validate(validate_board_data)

        draft.set_event(1, "custom", PARTY_SQUARE_COMPONENTS)
        draft.set_space_field(1, "msg", "   ")
        with self.assertRaisesRegex(BoardCreatorError, "custom message"):
            draft.validate(validate_board_data)

        draft.set_event(1, "ladder", PARTY_SQUARE_COMPONENTS)
        draft.set_space_field(1, "target", 99)
        with self.assertRaisesRegex(BoardCreatorError, "valid target"):
            draft.validate(validate_board_data)


class BoardSaveTests(unittest.TestCase):
    def test_save_is_valid_utf8_uses_suffixes_and_leaves_no_temp_file(self):
        draft = BoardDraft.create_default()
        draft.set_metadata("name", "Fiesta / Night")
        draft.set_metadata("description", "Jalapeño board")
        with tempfile.TemporaryDirectory() as directory:
            first = save_new_board(draft, directory, validate_board_data)
            second_draft = BoardDraft.create_default()
            second_draft.set_metadata("name", "Fiesta / Night")
            second = save_new_board(second_draft, directory, validate_board_data)

            self.assertEqual("Fiesta_Night.json", os.path.basename(first))
            self.assertEqual("Fiesta_Night_2.json", os.path.basename(second))
            with open(first, "r", encoding="utf-8") as file:
                saved = json.load(file)
            self.assertEqual("Jalapeño board", saved["description"])
            self.assertEqual(5, len(validate_board_data(saved)))
            self.assertFalse(any(name.endswith(".tmp") for name in os.listdir(directory)))
            self.assertFalse(draft.dirty)


class BoardCreatorUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        main._BACKGROUND_TEXTURE = pygame.Surface((16, 16)).convert()
        main._BACKGROUND_TEXTURE.fill(main.CARDBOARD)
        main._BUTTON_TEXTURE = pygame.Surface((16, 16)).convert()
        main._BUTTON_TEXTURE.fill(main.CARDBOARD_LITE)

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()

    def make_game(self):
        game = main.Game.__new__(main.Game)
        game.screen = pygame.Surface((main.SCREEN_W, main.SCREEN_H))
        game.f_header = game._font("arial", 36, bold=True)
        game.f_label = game._font("arial", 22, bold=True)
        game.f_body = game._font("arial", 20)
        game.f_small = game._font("arial", 15)
        game._menu_bg = pygame.Surface((main.SCREEN_W, main.SCREEN_H))
        game._menu_bg.fill(main.CARDBOARD)
        game._begin_board_creator()
        return game

    def test_creator_screen_renders_and_primary_controls_work(self):
        game = self.make_game()
        game.draw_board_creator()
        self.assertEqual("board_creator", game.state)
        self.assertEqual(5, len(game._creator_space_rects))
        self.assertGreater(len(game._creator_options), 9)

        add_click = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=game._creator_add_btn.center
        )
        game.handle_board_creator([add_click])
        self.assertEqual(6, len(game.board_draft.spaces))
        self.assertEqual(4, game.creator_selected)

        game.draw_board_creator()
        dropdown_click = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=game._creator_dropdown_rect.center,
        )
        game.handle_board_creator([dropdown_click])
        self.assertTrue(game.creator_dropdown_open)
        game.draw_board_creator()
        sip_rect = next(
            rect for rect, option in game._creator_option_rects if option.key == "sip"
        )
        option_click = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=sip_rect.center
        )
        game.handle_board_creator([option_click])
        self.assertEqual("sip", game.board_draft.spaces[4]["effect"])

        game.draw_board_creator()
        cancel_click = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=game._creator_cancel_btn.center
        )
        game.handle_board_creator([cancel_click])
        self.assertTrue(game.creator_confirm_cancel)
        game.draw_board_creator()
        discard_click = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=game._creator_discard_btn.center,
        )
        game.handle_board_creator([discard_click])
        self.assertEqual("menu", game.state)
        game.draw_board_creator()  # The old state still draws for this transition frame.


if __name__ == "__main__":
    unittest.main()
