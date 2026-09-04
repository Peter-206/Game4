import unittest
from game_engine import PlayerState
from game_data import calculate_player_titles, get_player_title


class PlayerTitlesTests(unittest.TestCase):
    def test_winner_gets_champion(self):
        p1 = PlayerState(name="Alice", token_name="pizza", finished=True)
        p2 = PlayerState(name="Bob", token_name="beer")
        titles = calculate_player_titles([p1, p2], winner=p1)
        self.assertEqual("Champion", titles[p1])

    def test_beer_bitch_title(self):
        p1 = PlayerState(name="Alice", token_name="pizza", finished=True)
        p2 = PlayerState(name="Bob", token_name="beer", is_beer_bitch=True)
        titles = calculate_player_titles([p1, p2], winner=p1)
        self.assertEqual("Champion", titles[p1])
        self.assertEqual("Beer Bitch", titles[p2])

    def test_whirlpool_title(self):
        p1 = PlayerState(name="Alice", token_name="pizza", finished=True)
        p2 = PlayerState(name="Bob", token_name="beer", whirlpool_position=2)
        titles = calculate_player_titles([p1, p2], winner=p1)
        self.assertEqual("Champion", titles[p1])
        self.assertEqual("Still Spinning", titles[p2])
        self.assertEqual("Still Spinning", get_player_title(p2, [p1, p2], winner=p1))

    def test_superlative_awards(self):
        winner = PlayerState(name="Winner", token_name="crown", finished=True)
        marathon = PlayerState(name="Runner", token_name="plane", distance_traveled=50)
        sipper = PlayerState(name="SipMaster", token_name="cup", sips=15)
        shooter = PlayerState(name="ShotMaster", token_name="beer", shots=5)
        moonwalker = PlayerState(name="Backwards", token_name="ducky", backward_steps=8)
        party_animal = PlayerState(name="Party", token_name="star", events_landed=7)
        clean = PlayerState(name="Sober", token_name="cactus", sips=0, shots=0)

        players = [winner, marathon, sipper, shooter, moonwalker, party_animal, clean]
        titles = calculate_player_titles(players, winner=winner)

        self.assertEqual("Champion", titles[winner])
        self.assertEqual("Marathoner", titles[marathon])
        self.assertEqual("Sip Goblin", titles[sipper])
        self.assertEqual("Shot Caller", titles[shooter])
        self.assertEqual("Moonwalker", titles[moonwalker])
        self.assertEqual("Party Animal", titles[party_animal])
        self.assertEqual("Iron Liver", titles[clean])

    def test_single_player_fallback(self):
        p = PlayerState(name="Solo", token_name="dice")
        self.assertEqual("Pub Regular", get_player_title(p))
        p.is_beer_bitch = True
        self.assertEqual("Beer Bitch", get_player_title(p))
        p.is_beer_bitch = False
        p.whirlpool_position = 0
        self.assertEqual("Still Spinning", get_player_title(p))
        p.finished = True
        self.assertEqual("Champion", get_player_title(p))


if __name__ == "__main__":
    unittest.main()
