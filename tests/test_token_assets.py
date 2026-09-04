import os
import pathlib
import unittest
from PIL import Image
import pygame

import game_data
from token_generator import DEFAULT_SIZES, TOKEN_DRAWERS, generate_all_tokens, render_token_image
from main import ensure_token_images, load_token_surface, load_token_surfaces


class TokenAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        # Ensure default tokens are generated
        ensure_token_images()

    def test_all_13_default_tokens_exist_as_ico_and_png(self):
        token_dir = pathlib.Path(game_data.TOKENS_DIR) / "default"
        self.assertEqual(13, len(TOKEN_DRAWERS))

        for name in TOKEN_DRAWERS:
            ico_file = token_dir / f"{name}.ico"
            png_file = token_dir / f"{name}.png"
            self.assertTrue(ico_file.is_file(), f"Missing {ico_file}")
            self.assertTrue(png_file.is_file(), f"Missing {png_file}")

    def test_ico_files_contain_multiple_resolution_qualities(self):
        token_dir = pathlib.Path(game_data.TOKENS_DIR) / "default"
        expected_sizes = set(DEFAULT_SIZES)

        for name in TOKEN_DRAWERS:
            ico_file = token_dir / f"{name}.ico"
            with Image.open(ico_file) as img:
                self.assertTrue(hasattr(img, "ico"), f"{name}.ico is not an ICO file")
                available_sizes = img.ico.sizes()
                for size in expected_sizes:
                    self.assertIn(size, available_sizes, f"{name}.ico missing size {size}")

    def test_load_token_surface_extracts_specified_resolutions(self):
        token_dir = pathlib.Path(game_data.TOKENS_DIR) / "default"

        for name in ("beer", "pizza", "crown", "dice", "star"):
            ico_file = str(token_dir / f"{name}.ico")
            for target_size in ((16, 16), (32, 32), (64, 64), (128, 128), (256, 256)):
                surf = load_token_surface(ico_file, target_size)
                self.assertIsInstance(surf, pygame.Surface)
                self.assertEqual(target_size, surf.get_size())

    def test_load_token_surfaces_loads_all_registered_tokens(self):
        surfaces = load_token_surfaces()
        self.assertEqual(len(game_data.ALL_TOKENS), len(surfaces))
        for name in game_data.ALL_TOKENS:
            self.assertIn(name, surfaces)
            surf = surfaces[name]
            self.assertIsInstance(surf, pygame.Surface)
            self.assertEqual((64, 64), surf.get_size())

    def test_render_token_image_produces_clean_rgba_master(self):
        for name in TOKEN_DRAWERS:
            img = render_token_image(name, size=128)
            self.assertEqual("RGBA", img.mode)
            self.assertEqual((128, 128), img.size)


if __name__ == "__main__":
    unittest.main()
