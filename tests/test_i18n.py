import json
import re
import unittest

import support  # noqa: F401  (src 경로 준비)
import i18n

PLACEHOLDER = re.compile(r"\{(\w+)\}")


def load(language):
    return json.loads((i18n.LOCALES_DIR / f"{language}.json").read_text(encoding="utf-8"))


class LocalesTest(unittest.TestCase):
    def test_every_language_has_every_key(self):
        english = load("en")
        for language in i18n.SUPPORTED:
            self.assertEqual(set(load(language)), set(english), language)

    def test_placeholders_match_english(self):
        english = load("en")
        for language in i18n.SUPPORTED:
            for key, text in load(language).items():
                self.assertEqual(set(PLACEHOLDER.findall(text)), set(PLACEHOLDER.findall(english[key])),
                                 f"{language}:{key}")


class NormalizeTest(unittest.TestCase):
    def test_locale_forms(self):
        self.assertEqual(i18n.normalize("ko_KR.UTF-8"), "ko")
        self.assertEqual(i18n.normalize("ja-JP"), "ja")
        self.assertIsNone(i18n.normalize("xx"))


if __name__ == "__main__":
    unittest.main()
