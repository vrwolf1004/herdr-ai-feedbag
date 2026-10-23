"""사이드바 토큰 문자열과 상세 화면 문자열을 만든다. herdr 호출 없이 순수 함수만 둔다.

이모지 대신 옛 DOS 박스 문자(█▓▒░►)만 쓴다. 폰트에 따라 그림으로 바뀌지 않고 칸 너비도 일정하다.
사이드바 한 줄 예 (frame 마다 ▓▒ 반짝임이 막대 안을 왼쪽→오른쪽으로 흘러 달리는 것처럼 보인다):

    ● cld ██▓▒█►░░ 52% wk 31%
    ! cop █████▓▒► 84% rst 11/01      (80% 이상이면 ● 자리가 ! 로 바뀌어 깜빡이고 config rule 로 빨갛게)

앞 표시는 항상 한 칸이라 경고가 켜지고 꺼져도 줄이 밀리지 않는다.
"""

import re
import unicodedata
from datetime import datetime

from i18n import t

BAR_CELLS = 8
WARN_PCT = 80
FILL = "█"
SHINE = "▒▓"   # 반짝임 앞(▒)과 뒤(▓)
RUNNER = "►"
EMPTY = "░"
MARK = "●"
WARN_MARK = "!"
# 깜빡임 꺼진 frame 의 한 칸. herdr 가 토큰 앞뒤 공백을 잘라 내므로 공백이 아닌 빈 글자(점자 빈칸)를 쓴다.
BLINK_OFF = "⠀"

SHORT_NAMES = {"claude": "cld", "copilot": "cop", "codex": "cdx", "gemini": "gem"}


def track(used_pct, frame):
    """채운 칸 + 달리는 머리(►) + 남은 칸. 머리 칸까지 BAR_CELLS 칸으로 고정한다.

    채운 칸 위로 2칸짜리 반짝임이 frame 마다 한 칸씩 지나가고, 끝나면 다시 처음부터 돈다.
    """
    if used_pct >= 100:
        return FILL * BAR_CELLS
    filled = min(BAR_CELLS - 1, max(0, round(BAR_CELLS * used_pct / 100)))
    cells = [FILL] * filled
    if filled:
        head = frame % (filled + len(SHINE))
        for offset, glyph in enumerate(reversed(SHINE)):
            index = head - offset
            if 0 <= index < filled:
                cells[index] = glyph
    return "".join(cells) + RUNNER + EMPTY * (BAR_CELLS - filled - 1)


def pct_text(used_pct):
    return "unl" if used_pct is None else f"{round(used_pct)}%"


def reset_date(iso):
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone().strftime("%m/%d")
    except ValueError:
        return ""


def is_warning(usage):
    return any(w.used_pct is not None and w.used_pct >= WARN_PCT for w in usage.windows)


def error_text(usage):
    key = f"error.{usage.error}"
    text = t(key, detail=usage.detail)
    if text == key:  # 번역 키가 없는 오류 (예상하지 못한 예외 이름): 키 이름 대신 일반 문구를 보인다
        return t("error.unexpected")
    return text


def sidebar_token(usage, frame):
    """사이드바에 보낼 한 줄. 첫 창은 달리는 막대로, 두 번째 정보는 짧게 붙인다.

    cld/cop/wk/rst 같은 약어는 폭이 일정하도록 번역하지 않는다. 오류 문구만 번역한다.
    """
    name = SHORT_NAMES.get(usage.provider, usage.provider)
    if usage.error and not usage.windows:
        return f"{MARK} {name} · {error_text(usage)}"
    main = usage.windows[0]
    if main.used_pct is None:
        body = f"{name} {main.label} unl"
    else:
        body = f"{name} {track(main.used_pct, frame)} {pct_text(main.used_pct)}"
    if usage.provider == "copilot":
        reset = reset_date(main.resets_at)
        if reset:
            body += f" rst {reset}"
    elif len(usage.windows) > 1:
        second = usage.windows[1]
        body += f" {second.label} {pct_text(second.used_pct)}"
    if is_warning(usage):
        # rule(starts_with "!")가 짝수 frame 에만 걸려 빨간색이 깜빡인다. 홀수 frame 은 같은 폭의 빈 글자.
        mark = WARN_MARK if frame % 2 == 0 else BLINK_OFF
    else:
        mark = MARK
    return f"{mark} {body}"


# ---------------------------------------------------------------- 상세 화면 (feedbag pane)

ANSI_RESET = "\033[0m"
ANSI_DIM = "\033[2m"
ANSI_BOLD = "\033[1m"
ANSI_RED = "\033[31m"
ANSI_YELLOW = "\033[33m"
ANSI_GREEN = "\033[32m"
TITLES = {"claude": "Claude Code", "copilot": "GitHub Copilot", "codex": "OpenAI Codex", "gemini": "Gemini CLI"}


def color_for(used_pct):
    if used_pct is None:
        return ANSI_GREEN
    if used_pct >= WARN_PCT:
        return ANSI_RED
    if used_pct >= 50:
        return ANSI_YELLOW
    return ANSI_GREEN


def reset_text(iso):
    if not iso:
        return ""
    try:
        moment = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return iso
    return t("detail.resets", time=moment.strftime("%m/%d %H:%M"))


def display_width(text):
    # 한글·일본어처럼 두 칸을 차지하는 글자를 세어 열을 맞춘다.
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def pad(text, width):
    return text + " " * max(1, width - display_width(text))


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def box(*sections, min_inner=44, max_inner=70, title=None):
    """상세 화면을 timekit 패널처럼 테두리 상자에 담는다. 섹션 사이는 가로줄로 나눈다.
    title 은 가운데 맞춰 맨 위 줄에 두고 구분선을 긋는다. ANSI 색 코드는 칸 수에서 뺀다."""
    rows = []
    for index, section in enumerate(sections):
        if index:
            rows.append(None)
        rows += section
    widths = [display_width(ANSI_RE.sub("", row)) for row in rows if row is not None]
    if title:
        widths.append(display_width(ANSI_RE.sub("", title)))
    inner = min(max_inner, max([min_inner] + [w + 2 for w in widths]))
    out = ["╭" + "─" * inner + "╮"]
    if title:
        left = max(0, (inner - display_width(ANSI_RE.sub("", title))) // 2)
        out.append("│" + " " * left + title + " " * max(0, inner - left - display_width(ANSI_RE.sub("", title))) + "│")
        out.append("├" + "─" * inner + "┤")
    for row in rows:
        if row is None:
            out.append("├" + "─" * inner + "┤")
            continue
        width = display_width(ANSI_RE.sub("", row))
        out.append("│ " + row + " " * max(0, inner - 1 - width) + "│")
    out.append("╰" + "─" * inner + "╯")
    return out


def detail_lines(usages, frame, updated_at):
    lines = [""]
    labels = {w.key: t(f"window.{w.key}") for usage in usages for w in usage.windows}
    label_width = max([display_width(label) + 1 for label in labels.values()] + [8])
    for usage in usages:
        lines.append(f" {ANSI_BOLD}{TITLES.get(usage.provider, usage.provider)}{ANSI_RESET}")
        if usage.error and not usage.windows:
            lines.append(f"   {ANSI_DIM}{error_text(usage)}{ANSI_RESET}")
        for window in usage.windows:
            color = color_for(window.used_pct)
            label = pad(labels[window.key], label_width)
            if window.used_pct is None:
                lines.append(f"   {label}{color}{t('detail.unlimited')}{ANSI_RESET}")
                continue
            lines.append(
                f"   {label}{color}{track(window.used_pct, frame)}{ANSI_RESET} {pct_text(window.used_pct):>4}"
                f"  {ANSI_DIM}{reset_text(window.resets_at)}{ANSI_RESET}"
            )
        if usage.error and usage.windows:
            lines.append(f"   {ANSI_DIM}{t('detail.last_failed', error=error_text(usage))}{ANSI_RESET}")
        lines.append("")
    stamp = updated_at.strftime("%H:%M:%S") if updated_at else "-"
    # 시간은 보통 색, 단축키([Ctrl+C] ...)는 회색으로 보여 준다.
    footer = t("detail.footer", time=stamp)
    split = footer.find("[")
    lines.append(f" {footer[:split]}{ANSI_DIM}{footer[split:]}{ANSI_RESET}")
    body = lines[1:-1]
    while body and not body[-1].strip():
        body.pop()
    return box(body, lines[-1:], title=f"{ANSI_BOLD}🐺  herdr-ai-feedbag  🌕{ANSI_RESET}")
