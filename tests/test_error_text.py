import json
import unittest

import support  # noqa: F401  (src 경로 준비)
import i18n
import providers
import render

LANGUAGES = ("en", "ko", "ru", "fr", "es", "de", "ja")


class ErrorTextTest(unittest.TestCase):
    def setUp(self):
        i18n.set_language("en")

    def tearDown(self):
        i18n.set_language("en")

    def test_unknown_exception_name_shows_a_plain_message_not_the_key(self):
        text = render.error_text(providers.Usage("claude", error="KeyError"))
        self.assertFalse(text.startswith("error."), text)
        self.assertEqual(text, "unexpected error")

    def test_unknown_exception_name_is_plain_in_korean_too(self):
        i18n.set_language("ko")
        self.assertEqual(render.error_text(providers.Usage("claude", error="ValueError")), "예상하지 못한 오류")

    def test_known_errors_keep_their_text(self):
        cases = [
            (providers.Usage("claude", error="not_logged_in"), "not logged in"),
            (providers.Usage("claude", error="login_expired"), "login expired"),
            (providers.Usage("claude", error="network", detail="timed out"), "network error: timed out"),
            (providers.Usage("claude", error="http", detail="500"), "HTTP 500"),
            (providers.Usage("claude", error="no_quota_data"), "no quota data"),
        ]
        for usage, expected in cases:
            with self.subTest(error=usage.error):
                self.assertEqual(render.error_text(usage), expected)

    def test_every_language_has_the_generic_message(self):
        english = json.loads((i18n.LOCALES_DIR / "en.json").read_text(encoding="utf-8"))
        for language in LANGUAGES:
            with self.subTest(language=language):
                messages = json.loads((i18n.LOCALES_DIR / f"{language}.json").read_text(encoding="utf-8"))
                self.assertIn("error.unexpected", messages)
                self.assertEqual(set(messages), set(english))


if __name__ == "__main__":
    unittest.main()
