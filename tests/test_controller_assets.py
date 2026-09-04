import pathlib
import unittest

from PIL import Image


class ControllerAssetTests(unittest.TestCase):
    def test_controller_assets_are_dedicated_and_linked(self):
        root = pathlib.Path(__file__).parents[1] / "controller"
        html = (root / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="styles.css"', html)
        self.assertIn('src="app.js?v=7"', html)
        self.assertTrue((root / "styles.css").is_file())
        self.assertTrue((root / "app.js").is_file())

    def test_cardboard_assets_are_valid_and_used_by_controller_surfaces(self):
        project = pathlib.Path(__file__).parents[1]
        styles = (project / "controller" / "styles.css").read_text(encoding="utf-8")
        with Image.open(project / "assets" / "Cardboard" / "cardboard1.png") as button:
            self.assertEqual("PNG", button.format)
        with Image.open(project / "assets" / "Cardboard" / "cardboard2.jpg") as background:
            self.assertEqual("JPEG", background.format)
        self.assertIn('url("/assets/cardboard1.png")', styles)
        self.assertIn('url("/assets/cardboard2.jpg")', styles)
        self.assertIn("button { border: 4px solid", styles)
        self.assertIn(".panel {", styles)

    def test_controller_declares_every_required_view_state(self):
        script = (pathlib.Path(__file__).parents[1] / "controller" / "app.js").read_text(encoding="utf-8")
        for state in ("connecting", "setup", "lobby", "waiting", "active-turn",
                      "prompt", "submitted", "paused", "reconnecting", "game-ended"):
            self.assertIn(f'"{state}"', script)

    def test_roll_is_authorized_by_host_turn_and_camera_state(self):
        script = (pathlib.Path(__file__).parents[1] / "controller" / "app.js").read_text(encoding="utf-8")
        self.assertIn('message.type==="turn_state"', script)
        self.assertIn("message.active_player_id===playerId&&message.can_roll", script)
        self.assertIn('send({type:"roll",turn_id:turnId})', script)

    def test_room_updates_do_not_overwrite_active_turn_state(self):
        script = (pathlib.Path(__file__).parents[1] / "controller" / "app.js").read_text(encoding="utf-8")
        self.assertIn("[STATES.SETUP,STATES.LOBBY].includes(document.body.dataset.state)", script)

    def test_controller_identity_is_atomic_and_visible(self):
        root = pathlib.Path(__file__).parents[1] / "controller"
        html = (root / "index.html").read_text(encoding="utf-8")
        script = (root / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="identity"', html)
        self.assertIn('id="roster"', html)
        self.assertIn("pizza-box-controller:${room}", script)
        self.assertIn("JSON.stringify(controllerSession)", script)
        self.assertIn("Playing as ${controllerSession.name}", script)
        self.assertIn('local?" (You)":""', script)
        self.assertNotIn("pizza-box-player:", script)

    def test_controller_roster_preserves_authoritative_join_order(self):
        script = (pathlib.Path(__file__).parents[1] / "controller" / "app.js").read_text(encoding="utf-8")
        self.assertIn("const ordered=[...(players||[])];", script)
        self.assertNotIn(".sort((a,b)", script)

    def test_private_prompts_reconnect_and_safe_rendering_are_implemented(self):
        root = pathlib.Path(__file__).parents[1] / "controller"
        script = (root / "app.js").read_text(encoding="utf-8")
        styles = (root / "styles.css").read_text(encoding="utf-8")
        for value in ('"confirmation"', '"text"', '"event_response"', '"event_resolved"'):
            self.assertIn(value, script)
        self.assertIn('message.type==="hot_seat_state"', script)
        self.assertIn('message.confirm_label||"Confirm"', script)
        self.assertIn("localStorage", script)
        self.assertIn("scheduleReconnect", script)
        self.assertIn('message.type==="player_removed"', script)
        self.assertIn("clearControllerSession();rosterPanel.hidden=true", script)
        self.assertIn("textContent", script)
        self.assertNotIn("innerHTML", script)
        self.assertIn("@media (max-width: 380px)", styles)
        self.assertIn("orientation: landscape", styles)

    def test_host_shutdown_moves_controller_to_reconnecting_state(self):
        script = (pathlib.Path(__file__).parents[1] / "controller" / "app.js").read_text(encoding="utf-8")
        self.assertIn('socket.addEventListener("close",scheduleReconnect)', script)
        self.assertIn('renderState(STATES.RECONNECTING,"Host disconnected. Retrying…")', script)

    def test_controller_supports_host_authoritative_stopwatch_prompts(self):
        root = pathlib.Path(__file__).parents[1] / "controller"
        script = (root / "app.js").read_text(encoding="utf-8")
        styles = (root / "styles.css").read_text(encoding="utf-8")
        self.assertIn('message.kind==="timer"', script)
        self.assertIn("timer_started_at_epoch_ms", script)
        self.assertIn("setInterval(update,100)", script)
        self.assertIn("timer-readout", styles)

    def test_pikmin_link_is_exact_safe_and_reports_activation(self):
        script = (pathlib.Path(__file__).parents[1] / "controller" / "app.js").read_text(encoding="utf-8")
        self.assertIn('allowedUrl="https://youtu.be/uEXP0iXGwRU"', script)
        self.assertIn('link.target="_blank"', script)
        self.assertIn('link.rel="noopener noreferrer"', script)
        self.assertIn('submitPromptResponse("activated")', script)

    def test_beer_bitch_role_uses_safe_bright_pink_roster_markup(self):
        root = pathlib.Path(__file__).parents[1] / "controller"
        script = (root / "app.js").read_text(encoding="utf-8")
        styles = (root / "styles.css").read_text(encoding="utf-8")
        self.assertIn("player.is_beer_bitch", script)
        self.assertIn('role.textContent="Beer Bitch "', script)
        self.assertIn("document.createTextNode", script)
        self.assertIn("#ff28b4", styles)


if __name__ == "__main__":
    unittest.main()
