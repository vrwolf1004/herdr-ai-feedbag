"""herdr-dock 의 빈 4번째 칸에 띄우는 플러그인 소개 상자. 도크 블록이 3개일 때만 쓰인다."""

import re
import sys
import unicodedata

TITLE = "🐺  herdr plugins  🌕"
ITEMS = [
    ("herdr-timekit", "Time, world clocks, counter and timer"),
    ("herdr-radio", "Internet radio in the sidebar (mpv required)"),
    ("herdr-talk", "Chat with people on other PCs, no server needed"),
]
FOOTER = 'Search "vrwolf1004" for more herdr plugins.'
MIN_INNER = 44
MAX_INNER = 70
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def style(text, sgr):
    return f"\x1b[{sgr}m{text}\x1b[0m"


def width(text):
    text = ANSI_RE.sub("", text)
    return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in text)


def box(title, sections):
    rows = []
    for index, section in enumerate(sections):
        if index:
            rows.append(None)
        rows.extend(section)
    widths = [width(row) for row in rows if row is not None] + [width(title)]
    inner = min(MAX_INNER, max([MIN_INNER] + [w + 2 for w in widths]))
    left = max(0, (inner - width(title)) // 2)
    lines = [
        "╭" + "─" * inner + "╮",
        "│" + " " * left + style(title, "1;97") + " " * (inner - left - width(title)) + "│",
        "├" + "─" * inner + "┤",
    ]
    for row in rows:
        if row is None:
            lines.append("├" + "─" * inner + "┤")
        else:
            lines.append("│ " + row + " " * (inner - 1 - width(row)) + "│")
    lines.append("╰" + "─" * inner + "╯")
    return "\n".join(lines)


def main():
    sections = [[style(name, "1;96"), "  " + style(desc, "90")] for name, desc in ITEMS]
    sections.append([style(FOOTER, "90")])
    # 화면과 스크롤백을 지워 셸이 찍은 명령 줄이 보이지 않게 한다 (panel 의 clear_screen 과 같은 방식)
    sys.stdout.write("\x1b[H\x1b[2J\x1b[3J")
    print(box(TITLE, sections))


if __name__ == "__main__":
    main()
