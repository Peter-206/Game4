"""
models.py — Player data model.
"""


class Player:
    def __init__(self, name: str, token_name: str, token_image):
        self.name        = name
        self.token_name  = token_name
        self.token_image = token_image  # pygame.Surface (64x64)
        self.position    = 0
        self.shots       = 0
        self.sips        = 0
        self.bonus_pts   = 0   # event bonuses (e.g. +20 on special all-shot events)
        self.penalty_pts = 0   # used by Drunk Driving (shot counts but score nets zero)
        self.finished    = False

    @property
    def score(self) -> int:
        """100 pts per shot, 20 pts per sip, minus any penalties."""
        return self.shots * 100 + self.sips * 20 + self.bonus_pts - self.penalty_pts

    def reset(self):
        """Reset for Play Again without recreating the object."""
        self.position    = 0
        self.shots       = 0
        self.sips        = 0
        self.bonus_pts   = 0
        self.penalty_pts = 0
        self.finished    = False
