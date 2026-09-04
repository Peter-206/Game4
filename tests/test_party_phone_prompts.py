import unittest
from unittest.mock import Mock, patch

import pygame

import game_data
from game_engine import RulesEngine
from main import Game
from models import Player
from protocol import TurnActionGuard


class PartyPhonePromptTests(unittest.TestCase):
    def make_game(self, effect):
        game = Game.__new__(Game)
        alex = Player("Alex", "pizza")
        blair = Player("Blair", "cup")
        alex.player_id = "alex-id"
        blair.player_id = "blair-id"
        alex.position = 0
        game.players = [alex, blair]
        game.current_idx = 0
        game.rules = RulesEngine(game.players, 0)
        game.mates = game.rules.mates
        game.board_spaces = [{"id": 0, "label": "Party Event", "effect": effect,
                              "msg": "{name} completes the custom event."}]
        game.finish_index = 0
        game.turn_id = 7
        game.last_effect = None
        game.last_effect_val = 0
        game.last_effect_msg = ""
        game.pending_interactive = None
        game.current_prompt = None
        game._last_prompt_broadcast = None
        game.hot_seat = None
        game._hot_seat_sent_prompts = set()
        game._last_hot_seat_broadcast = None
        game.song_event = None
        game.jfk_event = None
        game.rule_announcement = None
        game.rule_announcement_remaining_ms = 0
        game.house_rules = []
        game.messages = []
        game.action_guard = TurnActionGuard()
        game.lan_server = Mock()
        return game, alex, blair

    def test_every_reusable_party_effect_creates_the_documented_phone_prompt(self):
        expected = {
            "chicks_dicks": "option", "androids_iphones": "option",
            "shotgun": "confirmation", "double_or_single_shot": "option",
            "karaoke": "confirmation", "mate": "player",
            "drunk_driving": "player", "gay_chicken": "player",
            "chug_speak": "timer",
            "email_professor": "confirmation", "call_parent": "confirmation",
            "pikmin": "link",
            "swap_pants": "player", "serenade": "player",
            "jig_dance": "confirmation",
            "lap": "timer",
            "specialty_shot": "confirmation",
            "new_rule": "text", "custom": "confirmation",
        }
        for effect, kind in expected.items():
            with self.subTest(effect=effect):
                game, alex, _ = self.make_game(effect)
                game._resolve_space(alex, 4)
                self.assertEqual("phone_prompt", game.pending_interactive)
                self.assertEqual(kind, game.current_prompt["kind"])
                self.assertEqual("alex-id", game.current_prompt["player_id"])

    def test_chicks_dicks_privately_asks_for_self_category(self):
        game, alex, _ = self.make_game("chicks_dicks")
        game._resolve_space(alex, 4)

        self.assertIn("Choose for yourself", game.current_prompt["text"])
        self.assertEqual(
            [("girl", "I'm a girl"), ("guy", "I'm a guy")],
            [(choice["value"], choice["label"])
             for choice in game.current_prompt["choices"]],
        )
        self.assertIn("privately choosing for themselves", game.last_effect_msg)
        self.assertEqual((0, 0), (alex.sips, game.players[1].sips))

    def test_chicks_dicks_resolves_each_choice_once_with_opposite_instruction(self):
        for response, opposite_group in (("girl", "guys"), ("guy", "girls")):
            with self.subTest(response=response):
                game, alex, blair = self.make_game("chicks_dicks")
                game._resolve_space(alex, 4)
                game.phase = "phone_prompt"
                prompt_id = game.current_prompt["prompt_id"]
                payload = {
                    "_player_id": alex.player_id,
                    "turn_id": game.turn_id,
                    "prompt_id": prompt_id,
                    "response": response,
                }

                with patch("pygame.time.get_ticks", return_value=900):
                    game._consume_event_response(payload)
                    game._consume_event_response(payload)

                matching = [message for message in game.messages
                            if f"all {opposite_group} drink" in message["text"]]
                self.assertEqual(1, len(matching))
                self.assertEqual((0, 0), (alex.sips, blair.sips))
                self.assertIsNone(game.current_prompt)
                self.assertEqual("resolving", game.phase)

    def test_droids_iphones_privately_asks_for_personal_phone_type(self):
        game, alex, _ = self.make_game("androids_iphones")
        game._resolve_space(alex, 4)

        self.assertIn("Choose for yourself", game.current_prompt["text"])
        self.assertIn("personally have", game.current_prompt["text"])
        self.assertEqual(
            [("iphone", "I have an iPhone"), ("android", "I have an Android")],
            [(choice["value"], choice["label"])
             for choice in game.current_prompt["choices"]],
        )
        self.assertIn("privately choosing their own phone type", game.last_effect_msg)
        self.assertEqual((0, 0), (alex.sips, game.players[1].sips))

    def test_droids_iphones_resolves_each_choice_once_with_opposite_instruction(self):
        for response, opposite_group in (("iphone", "Android users"),
                                         ("android", "iPhone users")):
            with self.subTest(response=response):
                game, alex, blair = self.make_game("androids_iphones")
                game._resolve_space(alex, 4)
                game.phase = "phone_prompt"
                prompt_id = game.current_prompt["prompt_id"]
                payload = {
                    "_player_id": alex.player_id,
                    "turn_id": game.turn_id,
                    "prompt_id": prompt_id,
                    "response": response,
                }

                with patch("pygame.time.get_ticks", return_value=900):
                    game._consume_event_response(payload)
                    game._consume_event_response(payload)

                matching = [message for message in game.messages
                            if f"all {opposite_group} drink" in message["text"]]
                self.assertEqual(1, len(matching))
                self.assertEqual((0, 0), (alex.sips, blair.sips))
                self.assertIsNone(game.current_prompt)
                self.assertEqual("resolving", game.phase)

    def test_hot_seat_collects_one_question_from_every_other_player(self):
        game, alex, blair = self.make_game("hot_seat")
        game._resolve_space(alex, 4)
        self.assertEqual("hot_seat", game.pending_interactive)
        self.assertEqual({"blair-id": "Blair"}, game.hot_seat["pending"])
        game.phase = "hot_seat"
        prompt_id = game._hot_seat_prompt("blair-id", "ask")
        game._consume_hot_seat_response({
            "_player_id": "blair-id", "turn_id": 7,
            "prompt_id": prompt_id, "response": "What is your wildest story?",
        })
        self.assertEqual("answering", game.hot_seat["stage"])
        self.assertEqual("Blair", game.hot_seat["questions"][0]["author"])

        answer_id = game._hot_seat_prompt("alex-id", "answered", 0)
        game._consume_hot_seat_response({
            "_player_id": "alex-id", "turn_id": 7,
            "prompt_id": answer_id, "response": "confirmed",
        })
        self.assertEqual("finish", game.hot_seat["stage"])
        finish_id = game._hot_seat_prompt("alex-id", "finish")
        with patch("pygame.time.get_ticks", return_value=900):
            game._consume_hot_seat_response({
                "_player_id": "alex-id", "turn_id": 7,
                "prompt_id": finish_id, "response": "confirmed",
            })
        self.assertIsNone(game.hot_seat)
        self.assertEqual("resolving", game.phase)

    def test_host_can_skip_a_missing_hot_seat_question(self):
        game, alex, blair = self.make_game("hot_seat")
        game._resolve_space(alex, 4)
        game.phase = "hot_seat"
        game._handle_hot_seat_host_action(("skip_player", blair.player_id))
        self.assertEqual("finish", game.hot_seat["stage"])
        game.lan_server.publish.assert_called()

    def test_song_events_enter_countdown_without_phone_confirmation(self):
        for effect, filename in (("thunderstruck", "Thunderstruck.mp3"),
                                 ("rattlin_bog", "RattlinBog.mp3")):
            with self.subTest(effect=effect):
                game, alex, _ = self.make_game(effect)
                game._resolve_space(alex, 4)
                self.assertEqual("song_countdown", game.pending_interactive)
                self.assertTrue(game.song_event["path"].endswith(filename))
                self.assertIsNone(game.current_prompt)

    def test_song_events_load_complete_verified_animation_cues(self):
        thunder, alex, _ = self.make_game("thunderstruck")
        thunder._resolve_space(alex, 4)
        bog, alex, _ = self.make_game("rattlin_bog")
        bog._resolve_space(alex, 4)

        self.assertEqual(35, len(thunder.song_event["cue_times_ms"]))
        self.assertEqual(29020, thunder.song_event["cue_times_ms"][0])
        self.assertEqual(281140, thunder.song_event["cue_times_ms"][-1])
        self.assertEqual(sorted(set(thunder.song_event["cue_times_ms"])),
                         thunder.song_event["cue_times_ms"])
        self.assertEqual("THUNDER", thunder.song_event["cue_label"])
        self.assertEqual(14, len(bog.song_event["cue_times_ms"]))
        self.assertEqual(16240, bog.song_event["cue_times_ms"][0])
        self.assertEqual(282770, bog.song_event["cue_times_ms"][-1])
        self.assertEqual(sorted(set(bog.song_event["cue_times_ms"])),
                         bog.song_event["cue_times_ms"])
        self.assertEqual("DRINK!", bog.song_event["cue_label"])

    def test_thunderstruck_cues_advance_once_and_handle_frame_jumps(self):
        game, alex, _ = self.make_game("thunderstruck")
        game._resolve_space(alex, 4)
        game.phase = "song_playing"
        game.song_channel = Mock()
        game.song_channel.get_busy.return_value = True
        game.song_event["cue_times_ms"] = [1000, 2000, 3000]
        game.song_event["started_at"] = 1000

        game._update_song_event(1999)
        self.assertEqual(0, game.song_event["next_cue_index"])
        self.assertIsNone(game.song_event["cue_animation_started_at"])

        game._update_song_event(5000)
        self.assertEqual(1, game.song_event["next_cue_index"])
        self.assertEqual(5000, game.song_event["cue_animation_started_at"])

        game._update_song_event(5000)
        self.assertEqual(1, game.song_event["next_cue_index"])
        self.assertEqual(5000, game.song_event["cue_animation_started_at"])

        game._update_song_event(5900)
        self.assertEqual(2, game.song_event["next_cue_index"])
        self.assertEqual(5900, game.song_event["cue_animation_started_at"])

    def test_rattlin_bog_drink_cues_advance_once_and_handle_frame_jumps(self):
        game, alex, _ = self.make_game("rattlin_bog")
        game._resolve_space(alex, 4)
        game.phase = "song_playing"
        game.song_channel = Mock()
        game.song_channel.get_busy.return_value = True
        game.song_event["cue_times_ms"] = [1000, 2000, 3000]
        game.song_event["started_at"] = 2000

        game._update_song_event(2999)
        self.assertEqual(0, game.song_event["next_cue_index"])

        game._update_song_event(6000)
        self.assertEqual(1, game.song_event["next_cue_index"])
        self.assertEqual(6000, game.song_event["cue_animation_started_at"])

        game._update_song_event(6000)
        self.assertEqual(1, game.song_event["next_cue_index"])

        game._update_song_event(6900)
        self.assertEqual(2, game.song_event["next_cue_index"])
        self.assertEqual(6900, game.song_event["cue_animation_started_at"])

        game._update_song_event(59689)
        self.assertEqual(3, game.song_event["next_cue_index"])
        self.assertEqual(59689, game.song_event["cue_animation_started_at"])

        game._update_song_event(60589)
        self.assertIsNone(game.song_event["cue_animation_started_at"])

    def test_longest_road_generates_one_to_five_shots(self):
        game, alex, _ = self.make_game("longest_road")

        with patch("main.random.randint", return_value=4) as randint:
            message = game._resolve_space(alex, 2)

        randint.assert_called_once_with(1, 5)
        self.assertEqual(4, alex.shots)
        self.assertEqual(4, game.last_effect_val)
        self.assertIn("rolled 4", message)
        self.assertIsNone(game.current_prompt)

    def test_jfk_runs_ten_seconds_then_prompts_for_non_self_player_or_random(self):
        game, alex, blair = self.make_game("jfk")
        game._resolve_space(alex, 2)
        self.assertEqual("jfk_countdown", game.pending_interactive)
        self.assertEqual(10000, game.jfk_event["remaining_ms"])
        self.assertIsNone(game.current_prompt)

        game.phase = "jfk_countdown"
        game._update_jfk_event(9999)
        self.assertEqual("jfk_countdown", game.phase)
        self.assertIsNone(game.current_prompt)

        game._update_jfk_event(1)
        self.assertEqual("phone_prompt", game.phase)
        self.assertEqual("jfk", game.current_prompt["resolution"])
        self.assertEqual("Choose who was last to answer FDR.",
                         game.current_prompt["text"])
        choices = {choice["value"] for choice in game.current_prompt["choices"]}
        self.assertEqual({"random", blair.player_id}, choices)
        self.assertNotIn(alex.player_id, choices)

    def test_jfk_host_presentation_contains_no_visible_timer(self):
        game, _, _ = self.make_game("jfk")
        pygame.font.init()
        game.screen = pygame.Surface((1280, 800))
        game.f_title = pygame.font.Font(None, 72)

        with patch("main.draw_outlined_text") as draw_title:
            game._draw_jfk_overlay()

        draw_title.assert_called_once()
        self.assertEqual("JFK", draw_title.call_args.args[1])

    def test_jfk_explicit_and_random_results_assign_one_sip_once(self):
        for response in ("blair-id", "random"):
            with self.subTest(response=response):
                game, alex, blair = self.make_game("jfk")
                game._resolve_space(alex, 2)
                game.phase = "jfk_countdown"
                game._update_jfk_event(10000)
                prompt_id = game.current_prompt["prompt_id"]
                payload = {
                    "_player_id": alex.player_id,
                    "turn_id": game.turn_id,
                    "prompt_id": prompt_id,
                    "response": response,
                }
                with patch("main.random.choice", return_value=blair) as choose, \
                        patch("pygame.time.get_ticks", return_value=11000):
                    game._consume_event_response(payload)
                    game._consume_event_response(payload)

                self.assertEqual(1, blair.sips)
                self.assertEqual(0, alex.sips)
                self.assertIsNone(game.jfk_event)
                if response == "random":
                    choose.assert_called_once_with([blair])
                else:
                    choose.assert_not_called()

    def test_gay_chicken_explicit_and_random_opponents_require_completion(self):
        for response in ("blair-id", "random"):
            with self.subTest(response=response):
                game, alex, blair = self.make_game("gay_chicken")
                game._resolve_space(alex, 2)
                choices = {choice["value"] for choice in game.current_prompt["choices"]}
                self.assertEqual({"random", blair.player_id}, choices)
                self.assertNotIn(alex.player_id, choices)
                game.phase = "phone_prompt"
                select_prompt_id = game.current_prompt["prompt_id"]
                selection = {
                    "_player_id": alex.player_id,
                    "turn_id": game.turn_id,
                    "prompt_id": select_prompt_id,
                    "response": response,
                }

                with patch("main.random.choice", return_value=blair) as choose:
                    game._consume_event_response(selection)
                    game._consume_event_response(selection)

                if response == "random":
                    choose.assert_called_once_with([blair])
                else:
                    choose.assert_not_called()
                self.assertEqual("phone_prompt", game.phase)
                self.assertEqual("confirmation", game.current_prompt["kind"])
                self.assertEqual("gay_chicken_complete",
                                 game.current_prompt["resolution"])
                self.assertIn("Alex faces Blair", game.last_effect_msg)
                self.assertIn("Blair", game.current_prompt["text"])
                self.assertEqual((0, 0, 0, 0),
                                 (alex.shots, alex.sips, blair.shots, blair.sips))

                complete_prompt_id = game.current_prompt["prompt_id"]
                completion = {
                    "_player_id": alex.player_id,
                    "turn_id": game.turn_id,
                    "prompt_id": complete_prompt_id,
                    "response": "confirmed",
                }
                with patch("pygame.time.get_ticks", return_value=1200):
                    game._consume_event_response(completion)
                    game._consume_event_response(completion)

                self.assertEqual("resolving", game.phase)
                self.assertIsNone(game.current_prompt)
                self.assertEqual((0, 0, 0, 0),
                                 (alex.shots, alex.sips, blair.shots, blair.sips))
                completed = [message for message in game.messages
                             if "Gay Chicken complete" in message["text"]]
                self.assertEqual(1, len(completed))

    def test_gay_chicken_rejects_self_and_non_owner_responses(self):
        game, alex, blair = self.make_game("gay_chicken")
        game._resolve_space(alex, 2)
        game.phase = "phone_prompt"
        prompt_id = game.current_prompt["prompt_id"]

        for player_id, response in ((blair.player_id, blair.player_id),
                                    (alex.player_id, alex.player_id)):
            game._consume_event_response({
                "_player_id": player_id,
                "turn_id": game.turn_id,
                "prompt_id": prompt_id,
                "response": response,
            })

        self.assertEqual("gay_chicken_select", game.current_prompt["resolution"])
        self.assertEqual([], game.messages)

    def test_chug_speak_times_on_host_and_converts_seconds_to_minutes_once(self):
        game, alex, _ = self.make_game("chug_speak")
        game._resolve_space(alex, 2)
        self.assertEqual("timer", game.current_prompt["kind"])
        self.assertEqual("started", game.current_prompt["timer_action"])
        game.phase = "phone_prompt"
        start_prompt_id = game.current_prompt["prompt_id"]
        start = {
            "_player_id": alex.player_id,
            "turn_id": game.turn_id,
            "prompt_id": start_prompt_id,
            "response": "started",
        }

        with patch("pygame.time.get_ticks", return_value=1000), \
                patch("main.time.time", return_value=50.0):
            game._consume_event_response(start)
            game._consume_event_response(start)

        self.assertEqual(1000, game.chug_speak["started_at_ms"])
        self.assertEqual(50000, game.current_prompt["timer_started_at_epoch_ms"])
        self.assertEqual("stopped", game.current_prompt["timer_action"])
        self.assertEqual("phone_prompt", game.phase)

        stop_prompt_id = game.current_prompt["prompt_id"]
        stop = {
            "_player_id": alex.player_id,
            "turn_id": game.turn_id,
            "prompt_id": stop_prompt_id,
            "response": "stopped",
        }
        with patch("pygame.time.get_ticks", return_value=4250):
            game._consume_event_response(stop)
            game._consume_event_response(stop)

        self.assertIsNone(game.chug_speak)
        self.assertEqual(3.25, game.last_effect_val)
        self.assertIn("3.25 seconds", game.last_effect_msg)
        self.assertIn("3.25 minutes", game.last_effect_msg)
        self.assertEqual("resolving", game.phase)
        results = [message for message in game.messages
                   if "must speak for" in message["text"]]
        self.assertEqual(1, len(results))

    def test_chug_speak_rejects_wrong_timer_action_and_non_owner(self):
        game, alex, blair = self.make_game("chug_speak")
        game._resolve_space(alex, 2)
        game.phase = "phone_prompt"
        prompt_id = game.current_prompt["prompt_id"]
        for player_id, response in ((blair.player_id, "started"),
                                    (alex.player_id, "stopped")):
            game._consume_event_response({
                "_player_id": player_id,
                "turn_id": game.turn_id,
                "prompt_id": prompt_id,
                "response": response,
            })
        self.assertIsNone(game.chug_speak)
        self.assertEqual("chug_speak_start", game.current_prompt["resolution"])

    def test_email_professor_and_call_parent_are_owner_only_and_reconnect_safe(self):
        cases = (
            ("email_professor", "Email Sent", "EMAIL A PROFESSOR!"),
            ("call_parent", "Call Complete", "CALL A PARENT!"),
        )
        for effect, confirm_label, public_title in cases:
            with self.subTest(effect=effect):
                game, alex, blair = self.make_game(effect)
                game._resolve_space(alex, 2)
                self.assertEqual(confirm_label, game.current_prompt["confirm_label"])
                self.assertIn(public_title, game.last_effect_msg)
                game.phase = "phone_prompt"

                game._broadcast_phone_prompt()
                game._last_prompt_broadcast = None
                game._broadcast_phone_prompt()
                broadcasts = [call for call in game.lan_server.publish.call_args_list
                              if call.args[0].get("type") == "event_prompt"]
                self.assertEqual(2, len(broadcasts))
                self.assertEqual(game.current_prompt["prompt_id"],
                                 broadcasts[-1].args[0]["prompt_id"])

                prompt_id = game.current_prompt["prompt_id"]
                unauthorized = {
                    "_player_id": blair.player_id,
                    "turn_id": game.turn_id,
                    "prompt_id": prompt_id,
                    "response": "confirmed",
                }
                game._consume_event_response(unauthorized)
                self.assertIsNotNone(game.current_prompt)

                completion = {**unauthorized, "_player_id": alex.player_id}
                with patch("pygame.time.get_ticks", return_value=1500):
                    game._consume_event_response(completion)
                    game._consume_event_response(completion)
                self.assertEqual("resolving", game.phase)
                self.assertIsNone(game.current_prompt)
                completed = [message for message in game.messages
                             if "complete:" in message["text"]]
                self.assertEqual(1, len(completed))
                self.assertEqual((0, 0, 0, 0),
                                 (alex.shots, alex.sips, blair.shots, blair.sips))

    def test_pikmin_uses_exact_link_and_resolves_once_after_activation(self):
        game, alex, _ = self.make_game("pikmin")
        game._resolve_space(alex, 2)
        self.assertEqual("link", game.current_prompt["kind"])
        self.assertEqual("https://youtu.be/uEXP0iXGwRU", game.current_prompt["url"])
        game.phase = "phone_prompt"
        prompt_id = game.current_prompt["prompt_id"]
        payload = {
            "_player_id": alex.player_id,
            "turn_id": game.turn_id,
            "prompt_id": prompt_id,
            "response": "activated",
        }
        with patch("pygame.time.get_ticks", return_value=1750):
            game._consume_event_response(payload)
            game._consume_event_response(payload)
        self.assertEqual("resolving", game.phase)
        self.assertIsNone(game.current_prompt)
        opened = [message for message in game.messages
                  if "Pikmin opened" in message["text"]]
        self.assertEqual(1, len(opened))

    def test_pikmin_rejects_non_activation_responses(self):
        game, alex, _ = self.make_game("pikmin")
        game._resolve_space(alex, 2)
        game.phase = "phone_prompt"
        game._consume_event_response({
            "_player_id": alex.player_id,
            "turn_id": game.turn_id,
            "prompt_id": game.current_prompt["prompt_id"],
            "response": "confirmed",
        })
        self.assertEqual("pikmin", game.current_prompt["resolution"])

    def test_swap_pants_and_serenade_select_and_complete_once(self):
        cases = (
            ("swap_pants", "Pants Swapped", "SWAP PANTS!"),
            ("serenade", "Serenade Complete", "SERENADE!"),
        )
        for effect, confirm_label, public_title in cases:
            for response in ("blair-id", "random"):
                with self.subTest(effect=effect, response=response):
                    game, alex, blair = self.make_game(effect)
                    game._resolve_space(alex, 2)
                    choices = {choice["value"] for choice in game.current_prompt["choices"]}
                    self.assertEqual({"random", blair.player_id}, choices)
                    game.phase = "phone_prompt"
                    selection = {
                        "_player_id": alex.player_id,
                        "turn_id": game.turn_id,
                        "prompt_id": game.current_prompt["prompt_id"],
                        "response": response,
                    }
                    with patch("main.random.choice", return_value=blair) as choose:
                        game._consume_event_response(selection)
                        game._consume_event_response(selection)
                    if response == "random":
                        choose.assert_called_once_with([blair])
                    else:
                        choose.assert_not_called()
                    self.assertIn(public_title, game.last_effect_msg)
                    self.assertIn("Alex", game.last_effect_msg)
                    self.assertIn("Blair", game.last_effect_msg)
                    self.assertEqual(confirm_label, game.current_prompt["confirm_label"])

                    completion = {
                        "_player_id": alex.player_id,
                        "turn_id": game.turn_id,
                        "prompt_id": game.current_prompt["prompt_id"],
                        "response": "confirmed",
                    }
                    with patch("pygame.time.get_ticks", return_value=1900):
                        game._consume_event_response(completion)
                        game._consume_event_response(completion)
                    self.assertEqual("resolving", game.phase)
                    self.assertEqual((0, 0, 0, 0),
                                     (alex.shots, alex.sips, blair.shots, blair.sips))
                    completed = [message for message in game.messages
                                 if "complete:" in message["text"]]
                    self.assertEqual(1, len(completed))

    def test_jig_dance_host_selects_either_variation_and_completes_once(self):
        for variation in ("Do a Jig", "Dance"):
            with self.subTest(variation=variation):
                game, alex, _ = self.make_game(jig_dance) if False else self.make_game("jig_dance")
                with patch("main.random.choice", return_value=variation) as choose:
                    game._resolve_space(alex, 2)
                choose.assert_called_once_with(("Do a Jig", "Dance"))
                self.assertIn(variation.upper(), game.last_effect_msg)
                self.assertIn(variation, game.current_prompt["text"])
                game.phase = "phone_prompt"
                payload = {
                    "_player_id": alex.player_id,
                    "turn_id": game.turn_id,
                    "prompt_id": game.current_prompt["prompt_id"],
                    "response": "confirmed",
                }
                with patch("pygame.time.get_ticks", return_value=2100):
                    game._consume_event_response(payload)
                    game._consume_event_response(payload)
                self.assertEqual("resolving", game.phase)
                completed = [message for message in game.messages
                             if "Jig / Dance complete" in message["text"]]
                self.assertEqual(1, len(completed))

    def test_lap_stopwatch_restores_stops_and_requires_final_confirmation(self):
        game, alex, _ = self.make_game("lap")
        game._resolve_space(alex, 2)
        game.phase = "phone_prompt"
        start = {
            "_player_id": alex.player_id,
            "turn_id": game.turn_id,
            "prompt_id": game.current_prompt["prompt_id"],
            "response": "started",
        }
        with patch("pygame.time.get_ticks", return_value=2000), \
                patch("main.time.time", return_value=75.0):
            game._consume_event_response(start)

        self.assertEqual("lap_stop", game.current_prompt["resolution"])
        self.assertEqual(75000, game.current_prompt["timer_started_at_epoch_ms"])
        self.assertIn("stopwatch is live", game.last_effect_msg)
        game._last_prompt_broadcast = None
        game._broadcast_phone_prompt()
        self.assertEqual("lap_stop", game.current_prompt["resolution"])

        stop = {
            "_player_id": alex.player_id,
            "turn_id": game.turn_id,
            "prompt_id": game.current_prompt["prompt_id"],
            "response": "stopped",
        }
        with patch("pygame.time.get_ticks", return_value=7250):
            game._consume_event_response(stop)
            game._consume_event_response(stop)
        self.assertEqual(5.25, game.last_effect_val)
        self.assertIn("5.25 seconds", game.last_effect_msg)
        self.assertEqual("lap_complete", game.current_prompt["resolution"])
        self.assertEqual("phone_prompt", game.phase)

        finish = {
            "_player_id": alex.player_id,
            "turn_id": game.turn_id,
            "prompt_id": game.current_prompt["prompt_id"],
            "response": "confirmed",
        }
        with patch("pygame.time.get_ticks", return_value=8000):
            game._consume_event_response(finish)
            game._consume_event_response(finish)
        self.assertIsNone(game.lap_event)
        self.assertEqual("resolving", game.phase)
        confirmed = [message for message in game.messages
                     if "Lap confirmed" in message["text"]]
        self.assertEqual(1, len(confirmed))

    def test_whirlpool_all_roll_outcomes_propagate_to_mates_and_six_exits(self):
        outcomes = {
            1: (0, 1),
            2: (0, 2),
            3: (1, 0),
            4: (2, 0),
            5: (3, 0),
            6: (0, 0),
        }
        for roll, (shots, sips) in outcomes.items():
            with self.subTest(roll=roll):
                game, alex, blair = self.make_game("whirlpool")
                game.rules.pair_mates(alex, blair)
                game._resolve_space(alex, 2)
                self.assertEqual(0, alex.whirlpool_position)
                game._resolve_whirlpool_roll(alex, roll, 3000)
                self.assertEqual((shots, sips), (alex.shots, alex.sips))
                self.assertEqual((shots, sips), (blair.shots, blair.sips))
                self.assertEqual("resolving", game.phase)
                self.assertEqual(3000, game.resolve_start)
                if roll == 6:
                    self.assertIsNone(alex.whirlpool_position)
                    self.assertIn("escaped", game.last_effect_msg)
                else:
                    self.assertEqual(roll % 6, alex.whirlpool_position)

    def test_whirlpool_is_shared_and_preserves_normal_turn_order(self):
        game, alex, blair = self.make_game("whirlpool")
        alex.whirlpool_position = 1
        blair.whirlpool_position = 1
        next_index, skipped = game.rules.advance_turn(0)
        self.assertEqual(1, next_index)
        self.assertEqual([], skipped)
        self.assertEqual(1, alex.whirlpool_position)
        self.assertEqual(1, blair.whirlpool_position)

    def test_whirlpool_draws_six_spaces_and_all_trapped_tokens(self):
        game, alex, blair = self.make_game("whirlpool")
        pygame.font.init()
        game.screen = pygame.Surface((1280, 800))
        game.f_title = pygame.font.Font(None, 64)
        game.f_label = pygame.font.Font(None, 28)
        game.f_small = pygame.font.Font(None, 20)
        game.token_surfs = {
            alex.token_name: pygame.Surface((20, 20)),
            blair.token_name: pygame.Surface((20, 20)),
        }
        alex.whirlpool_position = 2
        blair.whirlpool_position = 2
        with patch("main.draw_text") as draw:
            game._draw_whirlpool_board()
        rendered = {call.args[1] for call in draw.call_args_list}
        self.assertTrue({"1 SIP", "2 SIPS", "1 SHOT", "2 SHOTS",
                         "3 SHOTS", "6 EXIT"}.issubset(rendered))

    def test_beer_bitch_transfers_single_role_and_broadcasts_it(self):
        game, alex, blair = self.make_game("beer_bitch")
        game._last_game_broadcast = None
        game._resolve_space(alex, 2)
        self.assertTrue(alex.is_beer_bitch)
        self.assertFalse(blair.is_beer_bitch)
        self.assertIn("Alex now holds", game.last_effect_msg)

        game._resolve_space(blair, 2)
        self.assertFalse(alex.is_beer_bitch)
        self.assertTrue(blair.is_beer_bitch)
        self.assertEqual(1, sum(player.is_beer_bitch for player in game.players))

        game._broadcast_game_state()
        room_states = [call.args[0] for call in game.lan_server.publish.call_args_list
                       if call.args[0].get("type") == "room_state"]
        roles = {item["player_id"]: item["is_beer_bitch"]
                 for item in room_states[-1]["players"]}
        self.assertEqual({"alex-id": False, "blair-id": True}, roles)

    def test_beer_bitch_sidebar_and_banner_draw_renders_pink(self):
        game, alex, blair = self.make_game("beer_bitch")
        pygame.font.init()
        game.screen = pygame.Surface((1280, 800))
        game.f_title = pygame.font.Font(None, 64)
        game.f_label = pygame.font.Font(None, 28)
        game.f_small = pygame.font.Font(None, 20)
        game.f_tiny = pygame.font.Font(None, 14)
        game.token_lead = {
            alex.token_name: pygame.Surface((20, 20)),
            blair.token_name: pygame.Surface((20, 20)),
        }
        game.token_surfs = {
            alex.token_name: pygame.Surface((20, 20)),
            blair.token_name: pygame.Surface((20, 20)),
        }
        game.camera = Mock(settled=True)
        game.display_die = 1
        game.die_value = 1
        game.phase = "wait_roll"
        game.paused = False
        game.roll_btn = pygame.Rect(0, 0, 10, 10)
        game.msg_new_ms = 1500
        game.msg_enter_ms = 250
        alex.is_beer_bitch = True

        with patch("main.draw_text") as draw_mock, \
                patch("main.draw_panel"), \
                patch("main.draw_die_face"), \
                patch("main.draw_button"):
            game._draw_sidebar()

        # Both the banner and the roster card for Alex should use PINK
        pink_calls = [c for c in draw_mock.call_args_list if c.args[3] == game_data.PINK]
        self.assertGreaterEqual(len(pink_calls), 2)

    def test_specialty_shot_selects_every_eligible_maker_and_applies_once(self):
        for maker_index in (1, 2):
            with self.subTest(maker_index=maker_index):
                game, alex, blair = self.make_game("specialty_shot")
                casey = Player("Casey", "star")
                casey.player_id = "casey-id"
                game.players.append(casey)
                game.rules.players = game.players
                game.rules.pair_mates(alex, blair)
                maker = game.players[maker_index]
                with patch("main.random.choice", return_value=maker) as choose:
                    game._resolve_space(alex, 2)
                choose.assert_called_once_with([blair, casey])
                self.assertIn(f"{maker.name} pours for Alex", game.last_effect_msg)
                self.assertIn(maker.name, game.current_prompt["text"])
                game.phase = "phone_prompt"
                prompt_id = game.current_prompt["prompt_id"]

                game._consume_event_response({
                    "_player_id": maker.player_id,
                    "turn_id": game.turn_id,
                    "prompt_id": prompt_id,
                    "response": "confirmed",
                })
                self.assertEqual(0, alex.shots)

                completion = {
                    "_player_id": alex.player_id,
                    "turn_id": game.turn_id,
                    "prompt_id": prompt_id,
                    "response": "confirmed",
                }
                with patch("pygame.time.get_ticks", return_value=2300):
                    game._consume_event_response(completion)
                    game._consume_event_response(completion)
                self.assertEqual(1, alex.shots)
                self.assertEqual(1, blair.shots)
                self.assertEqual(0, casey.shots)
                self.assertEqual("resolving", game.phase)

    def test_direction_and_age_events_choose_and_display_each_result(self):
        cases = (
            ("east_west", ("East", "West"), "EAST / WEST"),
            ("younger_older", ("Younger", "Older"), "YOUNGER / OLDER"),
        )
        for effect, choices, title in cases:
            for result in choices:
                with self.subTest(effect=effect, result=result):
                    game, alex, _ = self.make_game(effect)
                    with patch("main.random.choice", return_value=result) as choose:
                        message = game._resolve_space(alex, 2)
                    choose.assert_called_once_with(choices)
                    self.assertEqual("custom", game.last_effect)
                    self.assertEqual(f"{title}! {result}", game.last_effect_msg)
                    self.assertEqual(game.last_effect_msg, message)
                    self.assertIsNone(game.current_prompt)
                    self.assertIsNone(game.pending_interactive)

    def test_non_self_events_skip_cleanly_when_no_target_exists(self):
        for effect in ("mate", "drunk_driving", "gay_chicken", "swap_pants",
                       "serenade", "specialty_shot", "jfk"):
            with self.subTest(effect=effect):
                game, alex, _ = self.make_game(effect)
                game.players[:] = [alex]
                game.rules.players = game.players
                game.current_prompt = None
                game.pending_interactive = None

                message = game._resolve_space(alex, 2)

                self.assertIsNone(game.current_prompt)
                self.assertIsNone(game.pending_interactive)
                self.assertTrue("another player" in message or
                                "No available player" in message)

    def test_finishing_song_applies_group_shots_once_and_resumes_media(self):
        game, alex, blair = self.make_game("thunderstruck")
        game.media_pauser = Mock()
        game.song_channel = Mock()
        game._resolve_space(alex, 4)
        game.song_channel = Mock()
        with patch("pygame.time.get_ticks", return_value=1200):
            game._finish_song_event()
        self.assertEqual((1, 1), (alex.shots, blair.shots))
        game.media_pauser.resume_async.assert_called_once_with()
        self.assertEqual("resolving", game.phase)
        game._finish_song_event()
        self.assertEqual((1, 1), (alex.shots, blair.shots))

    def test_song_waits_for_full_five_second_countdown_before_playing(self):
        game, alex, _ = self.make_game("thunderstruck")
        game.media_pauser = Mock(available=True)
        game.song_channel = None
        game._resolve_space(alex, 4)
        game.phase = "song_countdown"
        sound = Mock()
        sound.get_length.return_value = 12.0
        sound.play.return_value = Mock()
        with patch("pygame.mixer.Sound", return_value=sound):
            game._update_song_event(100)
            game._update_song_event(5099)
            sound.play.assert_not_called()
            game._update_song_event(5100)
        sound.play.assert_called_once_with()
        self.assertEqual("song_playing", game.phase)

    def test_drinks_are_recorded_only_after_confirmation(self):
        game, alex, _ = self.make_game("shotgun")
        game._resolve_space(alex, 2)
        self.assertEqual(0, alex.shots)
        game._resolve_phone_prompt("shotgun", "confirmed")
        self.assertEqual(1, alex.shots)

    def test_phone_choices_and_text_mutate_authoritative_state(self):
        game, alex, blair = self.make_game("mate")
        game._resolve_space(alex, 1)
        game._resolve_phone_prompt("mate", blair.player_id)
        self.assertIs(blair, game.rules.mates[alex])

        game.current_prompt = None
        game._resolve_phone_prompt("new_rule", "  Keep elbows off the box  ")
        self.assertEqual(["Keep elbows off the box"], game.house_rules)
        self.assertEqual("rule_announcement", game.phase)
        self.assertEqual({"author": "Alex", "text": "Keep elbows off the box"},
                         game.rule_announcement)
        self.assertEqual(5000, game.rule_announcement_remaining_ms)

    def test_mate_picker_excludes_self_and_supports_authoritative_random(self):
        game, alex, blair = self.make_game("mate")
        game._resolve_space(alex, 1)

        choices = [(choice["value"], choice["label"])
                   for choice in game.current_prompt["choices"]]
        self.assertEqual([("random", "Random"), (blair.player_id, blair.name)], choices)
        self.assertNotIn(alex.player_id, {value for value, _ in choices})

        with patch("main.random.choice", return_value=blair) as choose:
            game._resolve_phone_prompt("mate", "random")
        choose.assert_called_once_with([blair])
        self.assertIs(blair, game.rules.mates[alex])

    def test_drunk_driving_excludes_self_and_assigns_explicit_or_random_shot_once(self):
        for response in ("blair-id", "random"):
            with self.subTest(response=response):
                game, alex, blair = self.make_game("drunk_driving")
                game._resolve_space(alex, 1)
                choices = {choice["value"] for choice in game.current_prompt["choices"]}
                self.assertEqual({"random", blair.player_id}, choices)
                self.assertNotIn(alex.player_id, choices)
                game.phase = "phone_prompt"
                prompt_id = game.current_prompt["prompt_id"]
                payload = {
                    "_player_id": alex.player_id,
                    "turn_id": game.turn_id,
                    "prompt_id": prompt_id,
                    "response": response,
                }

                with patch("main.random.choice", return_value=blair) as choose, \
                        patch("pygame.time.get_ticks", return_value=900):
                    game._consume_event_response(payload)
                    game._consume_event_response(payload)

                self.assertEqual(1, blair.shots)
                self.assertEqual(0, alex.shots)
                if response == "random":
                    choose.assert_called_once_with([blair])
                else:
                    choose.assert_not_called()

    def test_new_rule_announcement_lasts_five_active_seconds_then_advances(self):
        game, _, _ = self.make_game("new_rule")
        game._resolve_phone_prompt("new_rule", "Keep elbows off the box")
        game._advance_turn = Mock()

        game._update_rule_announcement(4999)
        game._advance_turn.assert_not_called()
        self.assertEqual(1, game.rule_announcement_remaining_ms)

        game._update_rule_announcement(1)
        game._advance_turn.assert_called_once_with()
        self.assertIsNone(game.rule_announcement)

    def test_empty_new_rule_does_not_create_an_announcement(self):
        game, _, _ = self.make_game("new_rule")
        game._resolve_phone_prompt("new_rule", "   ")
        self.assertEqual([], game.house_rules)
        self.assertIsNone(game.rule_announcement)


if __name__ == "__main__":
    unittest.main()
