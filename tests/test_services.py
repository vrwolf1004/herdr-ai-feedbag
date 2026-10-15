import json
import os
import tempfile
import unittest
from unittest import mock

import support  # noqa: F401  (src 경로 준비)
import providers
import rows
import services


def make_screen(enabled):
    with mock.patch.object(providers, "enabled_providers", return_value=enabled), \
            mock.patch.object(providers, "login_status", return_value="ok"):
        return services.Screen("unused")


class ScreenTest(unittest.TestCase):
    def test_enabled_first_then_rest(self):
        screen = make_screen(["codex", "claude"])
        self.assertEqual(screen.items, ["codex", "claude", "copilot", "gemini"])
        self.assertEqual(screen.chosen(), ["codex", "claude"])

    def test_toggle_and_save(self):
        screen = make_screen(["claude"])
        screen.apply(services.DOWN)
        screen.apply(services.DOWN)
        screen.apply(services.TOGGLE)
        self.assertEqual(screen.chosen(), ["claude", "codex"])
        self.assertTrue(screen.apply(services.SAVE))

    def test_keeps_last_one(self):
        screen = make_screen(["claude"])
        screen.apply(services.TOGGLE)
        self.assertEqual(screen.chosen(), ["claude"])
        self.assertTrue(screen.message)

    def test_quit_does_not_save(self):
        self.assertFalse(make_screen(["claude"]).apply(services.QUIT))

    def test_save_keeps_other_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, "config.json"), "w", encoding="utf-8") as file:
                json.dump({"lang": "ko"}, file)
            services.save(folder, ["gemini"])
            with open(os.path.join(folder, "config.json"), encoding="utf-8") as file:
                self.assertEqual(json.load(file), {"lang": "ko", "providers": ["gemini"]})


class RowsTest(unittest.TestCase):
    def test_missing_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "config.toml")
            with open(path, "w", encoding="utf-8") as file:
                file.write('rows = [[{ token = "$fb_claude" }]]\n')
            self.assertEqual(rows.missing_rows(["claude", "codex"], path), ["codex"])

    def test_missing_file_means_all_missing(self):
        self.assertEqual(rows.missing_rows(["claude"], os.path.join("nope", "config.toml")), ["claude"])

    def test_row_line(self):
        self.assertIn('"$fb_gemini"', rows.row_line("gemini"))


class CopilotAccountTest(unittest.TestCase):
    def test_account_from_config(self):
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.dict(os.environ, {"FEEDBAG_COPILOT_TOKEN": "", "GH_TOKEN": "", "GITHUB_TOKEN": ""}), \
                mock.patch.object(providers, "copilot_cli_tokens", return_value=["t"]) as cli:
            with open(os.path.join(folder, "config.json"), "w", encoding="utf-8") as file:
                json.dump({"copilot_account": "octocat"}, file)
            self.assertEqual(providers.copilot_tokens(folder), ["t"])
            cli.assert_called_once_with("octocat")


class GeminiRefreshTest(unittest.TestCase):
    def test_expired_without_client_is_login_expired(self):
        creds = {"access_token": "a", "refresh_token": "r", "expiry_date": 1000}
        with mock.patch.object(providers, "_read_json", return_value=creds), \
                mock.patch.object(providers, "gemini_client", return_value=None):
            self.assertEqual(providers.fetch_gemini().error, "login_expired")
            self.assertEqual(providers.login_status("gemini"), "expired")

    def test_expired_with_client_is_ok_status(self):
        creds = {"access_token": "a", "refresh_token": "r", "expiry_date": 1000}
        with mock.patch.object(providers, "_read_json", return_value=creds), \
                mock.patch.object(providers, "gemini_client", return_value=("id", "secret")):
            self.assertEqual(providers.login_status("gemini"), "ok")


if __name__ == "__main__":
    unittest.main()
