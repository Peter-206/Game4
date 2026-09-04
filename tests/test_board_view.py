import unittest
from random import Random

from board_view import (
    HorizontalCamera,
    SPACE_GAP,
    WORLD_MARGIN,
    Y_POSITIONS,
    make_world_positions,
    world_width,
)


class WorldLayoutTests(unittest.TestCase):
    def test_path_is_wide_and_always_progresses_right(self):
        positions = make_world_positions(rng=Random(1234))
        self.assertEqual(36, len(positions))
        self.assertTrue(all(a[0] < b[0] for a, b in zip(positions, positions[1:])))
        self.assertTrue(all(
            b[0] - a[0] == SPACE_GAP for a, b in zip(positions, positions[1:])
        ))
        self.assertGreater(world_width(positions), 5 * 865)
        self.assertGreater(len({y for _, y in positions}), 4)

    def test_y_positions_average_one_to_five_distinct_candidates(self):
        class PredictableRandom:
            def __init__(self):
                self.counts = iter((1, 3, 5))

            def randint(self, lower, upper):
                self.asserted_range = (lower, upper)
                return next(self.counts)

            def sample(self, population, count):
                self.population = population
                return list(population[:count])

        rng = PredictableRandom()
        positions = make_world_positions(3, rng=rng)

        self.assertEqual((1, 5), rng.asserted_range)
        self.assertEqual(Y_POSITIONS, rng.population)
        self.assertEqual(
            [
                (WORLD_MARGIN, Y_POSITIONS[0]),
                (WORLD_MARGIN + SPACE_GAP, round(sum(Y_POSITIONS[:3]) / 3)),
                (WORLD_MARGIN + SPACE_GAP * 2, round(sum(Y_POSITIONS[:5]) / 5)),
            ],
            positions,
        )

    def test_position_count_can_follow_any_board_length(self):
        self.assertEqual([], make_world_positions(0, rng=Random(1)))
        self.assertEqual(2, len(make_world_positions(2, rng=Random(1))))
        self.assertEqual(100, len(make_world_positions(100, rng=Random(1))))

    def test_camera_clamps_start_and_finish_without_blank_world(self):
        camera = HorizontalCamera(865, 5600)
        camera.snap(0)
        self.assertEqual(0, camera.position)
        camera.snap(5600)
        self.assertEqual(4735, camera.position)

    def test_camera_interpolates_and_reports_settled(self):
        camera = HorizontalCamera(800, 4000, speed=1000)
        camera.focus(2400)
        self.assertFalse(camera.settled)
        camera.update(0.5)
        self.assertEqual(500, camera.position)
        self.assertFalse(camera.settled)
        camera.update(2)
        self.assertEqual(2000, camera.position)
        self.assertTrue(camera.settled)

    def test_pause_freezes_camera_and_conversion_uses_offset(self):
        camera = HorizontalCamera(800, 4000, position=100, target=900, settled=False)
        camera.update(1, paused=True)
        self.assertEqual(100, camera.position)
        self.assertEqual((150, 20), camera.world_to_screen((250, 20)))
        self.assertTrue(camera.visible_x(850))
        self.assertFalse(camera.visible_x(950))


if __name__ == "__main__":
    unittest.main()
