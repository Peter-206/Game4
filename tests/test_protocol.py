import unittest

from protocol import MESSAGE_TYPES, ProtocolError, TurnActionGuard, validate_client_message


class ProtocolValidationTests(unittest.TestCase):
    def test_protocol_declares_every_required_message(self):
        required = {"join", "reconnect", "roll", "event_response", "leave", "room_state",
                    "turn_state", "roll_result", "event_prompt", "event_resolved",
                    "drink_state", "pause", "game_end", "hot_seat_state"}
        self.assertEqual(required, MESSAGE_TYPES)

    def test_messages_are_normalized_and_malformed_payloads_rejected(self):
        self.assertEqual({"type": "roll", "turn_id": 3},
                         validate_client_message({"type": "roll", "turn_id": 3, "junk": True}))
        for payload in ({"type": "roll"}, {"type": "roll", "turn_id": True},
                        {"type": "unknown"}, [], {"type": "event_response", "turn_id": 1}):
            with self.subTest(payload=payload), self.assertRaises(ProtocolError):
                validate_client_message(payload)

    def test_roll_authorization_rejects_wrong_stale_duplicate_and_paused_actions(self):
        guard = TurnActionGuard()
        self.assertFalse(guard.accept_roll(player_id="b", active_player_id="a", submitted_turn=1, current_turn=1, can_roll=True))
        self.assertFalse(guard.accept_roll(player_id="a", active_player_id="a", submitted_turn=0, current_turn=1, can_roll=True))
        self.assertFalse(guard.accept_roll(player_id="a", active_player_id="a", submitted_turn=1, current_turn=1, can_roll=False))
        self.assertTrue(guard.accept_roll(player_id="a", active_player_id="a", submitted_turn=1, current_turn=1, can_roll=True))
        self.assertFalse(guard.accept_roll(player_id="a", active_player_id="a", submitted_turn=1, current_turn=1, can_roll=True))

    def test_prompt_response_is_idempotent_and_owner_scoped(self):
        guard = TurnActionGuard()
        args = dict(player_id="a", owner_id="a", submitted_turn=2, current_turn=2,
                    prompt_id="p1", current_prompt_id="p1")
        self.assertTrue(guard.accept_prompt(**args))
        self.assertFalse(guard.accept_prompt(**args))


if __name__ == "__main__":
    unittest.main()
