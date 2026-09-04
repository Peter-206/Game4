import unittest

import pygame

import main


class DynamicUiSizingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def test_centered_popup_grows_to_request_and_clamps_to_viewport(self):
        compact = main.centered_popup(420, 260)
        self.assertEqual((420, 260), compact.size)
        self.assertEqual((main.SCREEN_W // 2, main.SCREEN_H // 2), compact.center)

        oversized = main.centered_popup(5000, 5000, margin=40)
        self.assertEqual((main.SCREEN_W - 80, main.SCREEN_H - 80), oversized.size)
        self.assertEqual((main.SCREEN_W // 2, main.SCREEN_H // 2), oversized.center)

    def test_wrap_text_never_returns_a_line_wider_than_its_limit(self):
        font = pygame.font.SysFont("arial", 20)
        lines = main.wrap_text("A very long popup message with Supercalifragilisticexpialidocious",
                               font, 150)
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(font.size(line)[0] <= 150 for line in lines))

    def test_button_labels_shrink_without_exceeding_original_font_size(self):
        font = pygame.font.SysFont("arial", 28, bold=True)
        main._FONT_SPECS[id(font)] = ("arial", 28, True)
        label, fitted = main._fit_button_label(
            "This button label is much too long for the available space",
            font, 180, 30,
        )
        self.assertLessEqual(fitted.size(label)[0], 180)
        self.assertLessEqual(fitted.get_height(), 30)
        self.assertLessEqual(main._FONT_SPECS[id(fitted)][1], 28)


if __name__ == "__main__":
    unittest.main()
