import unittest

from game_data import BOARD_W, SCREEN_W, SIDEBAR_W, SIDEBAR_X
from view_layout import DisplayLayout, sidebar_row_height, sidebar_rows_fit


class SidebarLayoutTests(unittest.TestCase):
    def test_supported_player_counts_fit_available_sidebar(self):
        for count in (2, 8, 15):
            with self.subTest(count=count):
                self.assertTrue(sidebar_rows_fit(count, 374))

    def test_layout_expands_for_small_games_and_compacts_for_large_games(self):
        self.assertEqual(58, sidebar_row_height(2, 374))
        self.assertEqual(46, sidebar_row_height(8, 374))
        self.assertEqual(24, sidebar_row_height(15, 374))


class DisplayLayoutTests(unittest.TestCase):
    def test_board_and_sidebar_share_an_edge_and_fill_the_design_width(self):
        self.assertEqual(BOARD_W, SIDEBAR_X)
        self.assertEqual(SCREEN_W, SIDEBAR_X + SIDEBAR_W)

    def test_standard_resolutions_fill_the_complete_native_viewport(self):
        for size in ((1920, 1200), (1920, 1080), (2560, 1440), (3840, 2160)):
            with self.subTest(size=size):
                layout = DisplayLayout.from_window(*size)
                self.assertEqual((0, 0, *size), layout.viewport)

    def test_4k_maps_the_full_design_and_round_sizes_without_distortion(self):
        layout = DisplayLayout.from_window(3840, 2160)
        self.assertEqual((3840, 2160), layout.point((1280, 800)))
        self.assertEqual(2.7, layout.uniform_scale)
        self.assertEqual(86, layout.size(32))

    def test_non_widescreen_window_uses_every_available_pixel(self):
        layout = DisplayLayout.from_window(1280, 1024)
        self.assertEqual((0, 0, 1280, 1024), layout.viewport)
        self.assertEqual((20, 15), layout.window_to_design((20, 20)))
        self.assertEqual((640, 400), layout.window_to_design((640, 512)))

    def test_gui_scale_changes_round_assets_without_changing_full_screen_mapping(self):
        compact = DisplayLayout.from_window(1920, 1200, 0.8)
        large = DisplayLayout.from_window(1920, 1200, 1.2)
        self.assertEqual(compact.viewport, large.viewport)
        self.assertEqual((1920, 1200), compact.point((1280, 800)))
        self.assertEqual(38, compact.size(32))
        self.assertEqual(58, large.size(32))

    def test_4k_input_round_trips_to_design_coordinates(self):
        layout = DisplayLayout.from_window(3840, 2160)
        self.assertEqual((865, 400), layout.window_to_design(layout.point((865, 400))))


if __name__ == "__main__":
    unittest.main()
