import os
import tempfile
import unittest
from unittest import mock

import support  # noqa: F401  (src 경로 준비)
import providers


class ParseClaudeTest(unittest.TestCase):
    def test_windows(self):
        usage = providers.parse_claude({
            "five_hour": {"utilization": 34.0, "resets_at": "2026-10-15T05:00:00Z"},
            "seven_day": {"utilization": 78.0, "resets_at": None},
        })
        self.assertEqual([(w.label, w.used_pct) for w in usage.windows], [("5h", 34.0), ("wk", 78.0)])
        self.assertIsNone(usage.error)

    def test_missing_block(self):
        usage = providers.parse_claude({})
        self.assertEqual([w.used_pct for w in usage.windows], [None, None])


class ParseCopilotTest(unittest.TestCase):
    def test_premium_used_from_percent_remaining(self):
        usage = providers.parse_copilot({
            "quota_reset_date": "2026-11-01",
            "quota_snapshots": {
                "premium_interactions": {"percent_remaining": 70.0, "unlimited": False},
                "chat": {"unlimited": True},
            },
        })
        self.assertEqual([(w.label, w.used_pct) for w in usage.windows], [("premium", 30.0), ("chat", None)])
        self.assertEqual(usage.windows[0].resets_at, "2026-11-01")

    def test_no_snapshots(self):
        self.assertEqual(providers.parse_copilot({}).error, "no_quota_data")


class CopilotTokensTest(unittest.TestCase):
    def test_env_wins(self):
        with mock.patch.dict(os.environ, {"FEEDBAG_COPILOT_TOKEN": " abc "}, clear=False):
            self.assertEqual(providers.copilot_tokens(None), ["abc"])

    def test_config_file(self):
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.dict(os.environ, {"FEEDBAG_COPILOT_TOKEN": "", "GH_TOKEN": "", "GITHUB_TOKEN": ""}):
            with open(os.path.join(folder, "copilot-token"), "w", encoding="utf-8") as file:
                file.write("from-file\n")
            self.assertEqual(providers.copilot_tokens(folder), ["from-file"])

    def test_codex_windows(self):
        usage = providers.parse_codex({"rate_limit": {
            "primary_window": {"used_percent": 42, "reset_at": 0},
            "secondary_window": {"used_percent": 7, "reset_after_seconds": 60},
        }}, now=0)
        self.assertEqual([(w.label, w.used_pct) for w in usage.windows], [("5h", 42.0), ("wk", 7.0)])
        self.assertTrue(usage.windows[1].resets_at.startswith("1970-01-01T00:01"))

    def test_codex_no_limits(self):
        self.assertEqual(providers.parse_codex({}).error, "no_quota_data")

    def test_gemini_lowest_per_family(self):
        usage = providers.parse_gemini({"buckets": [
            {"modelId": "gemini-2.5-pro", "remainingFraction": 0.9},
            {"modelId": "gemini-2.5-pro", "tokenType": "REQUESTS", "remainingFraction": 0.25},
            {"modelId": "gemini-2.5-flash", "remainingFraction": 1.0},
            {"modelId": "other", "remainingFraction": 0.0},
        ]})
        self.assertEqual([(w.key, w.used_pct) for w in usage.windows], [("pro", 75.0), ("flash", 0.0)])

    def test_enabled_from_config(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, "config.json"), "w", encoding="utf-8") as file:
                file.write('{"providers": ["gemini", "nope", "claude", "gemini"]}')
            self.assertEqual(providers.enabled_providers(folder), ["gemini", "claude"])

    def test_enabled_default_detects_login_files(self):
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(providers, "codex_auth_path", return_value=os.path.join(folder, "x")), \
                mock.patch.object(providers, "gemini_creds_path", return_value=folder):
            self.assertEqual(providers.enabled_providers(None), ["claude", "copilot"])

    def test_decode_secret(self):
        self.assertEqual(providers._decode_secret("gho_x".encode("utf-16-le")), "gho_x")
        self.assertEqual(providers._decode_secret(b"gho_x"), "gho_x")


if __name__ == "__main__":
    unittest.main()
