import unittest

import support  # noqa: F401  (src 경로 준비)
import i18n
import render
from providers import Usage, Window


def claude(five_hour, week=10):
    return Usage("claude", [Window("five_hour", "5h", five_hour), Window("seven_day", "wk", week)])


class TrackTest(unittest.TestCase):
    def test_width_is_fixed(self):
        for pct in (0, 1, 12, 50, 87.5, 99, 100):
            for frame in range(6):
                self.assertEqual(len(render.track(pct, frame)), render.BAR_CELLS, (pct, frame))

    def test_runner_sits_at_fill_edge(self):
        self.assertEqual(render.track(0, 0), "►" + "░" * 7)
        self.assertEqual(render.track(50, 99).index("►"), 4)

    def test_full_has_no_runner(self):
        self.assertEqual(render.track(100, 3), "█" * render.BAR_CELLS)

    def test_shine_moves_each_frame(self):
        frames = {render.track(60, frame) for frame in range(4)}
        self.assertGreater(len(frames), 1)


class SidebarTokenTest(unittest.TestCase):
    def test_claude_shows_both_windows(self):
        token = render.sidebar_token(claude(52, 31), 0)
        self.assertTrue(token.startswith("● cld "))
        self.assertIn("52%", token)
        self.assertIn("wk 31%", token)

    def test_warning_replaces_mark_and_blinks(self):
        self.assertTrue(render.sidebar_token(claude(85), 0).startswith("! cld "))
        off = render.sidebar_token(claude(85), 1)
        self.assertTrue(off.startswith(render.BLINK_OFF + " cld "))
        self.assertEqual(off, off.strip())  # herdr 가 앞을 잘라 내지 않도록
        self.assertTrue(render.sidebar_token(claude(79), 0).startswith("● cld "))

    def test_warning_does_not_shift_line(self):
        widths = {len(render.sidebar_token(claude(pct), frame)) for pct in (79, 85) for frame in (0, 1)}
        self.assertEqual(len(widths), 1)

    def test_weekly_over_threshold_also_warns(self):
        self.assertTrue(render.sidebar_token(claude(10, 90), 0).startswith("! "))

    def test_copilot_shows_reset_date(self):
        usage = Usage("copilot", [Window("premium_interactions", "premium", 30, "2026-11-01T00:00:00Z")])
        self.assertRegex(render.sidebar_token(usage, 0), r"^● cop .+ 30% rst \d\d/\d\d$")

    def test_error_without_numbers(self):
        self.assertEqual(render.sidebar_token(Usage("copilot", error="not_logged_in"), 0), "● cop · not logged in")

    def test_error_detail_is_filled(self):
        usage = Usage("claude", error="network", detail="timed out")
        self.assertEqual(render.sidebar_token(usage, 0), "● cld · network error: timed out")


class DetailTest(unittest.TestCase):
    def test_wide_labels_keep_columns(self):
        i18n.set_language("ja")
        try:
            lines = [line for line in render.detail_lines([claude(30, 40)], 0, None) if "►" in line]
            # 라벨(5時間 / 週間) 폭이 달라도 막대가 같은 열에서 시작해야 한다.
            bar_columns = {render.display_width(line[:min(line.index(c) for c in "█▓▒►" if c in line)])
                           for line in lines}
            self.assertEqual(len(lines), 2)
            self.assertEqual(len(bar_columns), 1, lines)
        finally:
            i18n.set_language("en")

    def test_unlimited(self):
        usage = Usage("copilot", [Window("chat", "chat", None)])
        self.assertEqual(render.sidebar_token(usage, 0), "● cop chat unl")


if __name__ == "__main__":
    unittest.main()
