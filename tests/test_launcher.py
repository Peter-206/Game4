import pathlib
import unittest


class LauncherTests(unittest.TestCase):
    def test_launcher_uses_project_environment_and_main_host(self):
        root = pathlib.Path(__file__).parents[1]
        launcher = (root / "play.bat").read_text(encoding="utf-8")
        self.assertIn('.venv\\Scripts\\python.exe" main.py', launcher)
        main = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("self.lan_server.start()", main)
        self.assertIn("self.lan_server.stop()", main)

    def test_readme_documents_start_stop_and_firewall(self):
        readme = (pathlib.Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")
        for phrase in ("play.bat", "shut down", "Windows Firewall", "Private networks", "guest Wi-Fi"):
            self.assertIn(phrase, readme)


if __name__ == "__main__":
    unittest.main()
