"""서비스 선택 화면. 방향키로 고르고 스페이스로 켜고 끈 뒤 Enter 로 config.json 에 저장한다.

feedbag 의 services 액션이 overlay pane 으로 띄운다. 저장하면 host 에 refresh 신호를 보내
목록을 바로 다시 읽게 한다. herdr config.toml 은 고치지 않고, 빠진 사이드바 줄만 보여 준다.
"""

import json
import os
import sys

import i18n
import providers
import rows
from i18n import t
from render import TITLES

ANSI_RESET = "\033[0m"
ANSI_DIM = "\033[2m"
ANSI_BOLD = "\033[1m"
ANSI_REVERSE = "\033[7m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
STATUS_COLORS = {"ok": ANSI_GREEN, "expired": ANSI_YELLOW, "missing": ANSI_RED}

UP, DOWN, TOGGLE, SAVE, QUIT = "up", "down", "toggle", "save", "quit"


def read_key():
    """키 하나를 읽어 UP/DOWN/TOGGLE/SAVE/QUIT 로 바꾼다. 다른 키는 None."""
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            return {"H": UP, "P": DOWN}.get(msvcrt.getwch())
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        saved = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                if sys.stdin.read(1) != "[":
                    return QUIT
                return {"A": UP, "B": DOWN}.get(sys.stdin.read(1))
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, saved)
    return {"k": UP, "j": DOWN, " ": TOGGLE, "\r": SAVE, "\n": SAVE, "q": QUIT, "\x1b": QUIT, "\x03": QUIT}.get(ch)


class Screen:
    def __init__(self, config_dir):
        self.config_dir = config_dir
        enabled = providers.enabled_providers(config_dir)
        # 켜진 서비스를 지금 순서대로 먼저, 나머지를 뒤에 둔다. 저장 순서가 곧 사이드바 순서다.
        self.items = enabled + [name for name in providers.ALL_PROVIDERS if name not in enabled]
        self.checked = set(enabled)
        self.status = {name: providers.login_status(name, config_dir) for name in self.items}
        self.cursor = 0
        self.message = ""

    def apply(self, key):
        """키 하나를 반영한다. 끝낼 때는 저장 여부(True/False)를, 계속할 때는 None 을 돌려준다."""
        if key == UP:
            self.cursor = (self.cursor - 1) % len(self.items)
        elif key == DOWN:
            self.cursor = (self.cursor + 1) % len(self.items)
        elif key == TOGGLE:
            name = self.items[self.cursor]
            if name in self.checked and len(self.checked) == 1:
                self.message = t("services.need_one")
            else:
                self.checked ^= {name}
                self.message = ""
        elif key == SAVE:
            return True
        elif key == QUIT:
            return False
        return None

    def chosen(self):
        return [name for name in self.items if name in self.checked]

    def lines(self):
        out = [f"{ANSI_BOLD} feedbag{ANSI_RESET}  {ANSI_DIM}{t('services.title')}{ANSI_RESET}", ""]
        width = max(len(TITLES[name]) for name in self.items) + 2
        for index, name in enumerate(self.items):
            box = "[x]" if name in self.checked else "[ ]"
            status = self.status[name]
            label = f" {box} {TITLES[name].ljust(width)}"
            if index == self.cursor:
                label = f"{ANSI_REVERSE}{label}{ANSI_RESET}"
            out.append(f"{label} {STATUS_COLORS[status]}{t('services.status_' + status)}{ANSI_RESET}")
        out.append("")
        missing = rows.missing_rows(self.chosen())
        if missing:
            out.append(f" {ANSI_YELLOW}{t('services.rows_missing', path=rows.herdr_config_path())}{ANSI_RESET}")
            out.extend(f" {ANSI_DIM}{rows.row_line(name)}{ANSI_RESET}" for name in missing)
            out.append("")
        if self.message:
            out.append(f" {ANSI_RED}{self.message}{ANSI_RESET}")
        out.append(f" {ANSI_DIM}{t('services.help')}{ANSI_RESET}")
        return out

    def draw(self):
        # 같은 자리에 덮어쓴다. 화면을 지우면 터미널 스크롤백에 이전 프레임이 쌓인다.
        painted = "\n".join(line + "\033[K" for line in self.lines())
        sys.stdout.write("\033[H" + painted + "\033[J")
        sys.stdout.flush()


def save(config_dir, names):
    """config.json 의 다른 값(lang, copilot_account 등)은 그대로 두고 providers 만 바꾼다."""
    config = providers.read_config(config_dir)
    config["providers"] = names
    os.makedirs(config_dir, exist_ok=True)
    with open(providers.config_path(config_dir), "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)
        file.write("\n")


def run(config_dir, state_dir):
    if not config_dir:
        print("feedbag: HERDR_PLUGIN_CONFIG_DIR is not set", file=sys.stderr)
        return 1
    i18n.set_language(i18n.detect())
    screen = Screen(config_dir)
    try:
        while True:
            screen.draw()
            result = screen.apply(read_key())
            if result is not None:
                break
    except KeyboardInterrupt:
        result = False
    if result:
        save(config_dir, screen.chosen())
        if state_dir:
            # host 가 다음 바퀴에 목록을 다시 읽고 바로 조회하도록 refresh 신호를 남긴다.
            os.makedirs(state_dir, exist_ok=True)
            with open(os.path.join(state_dir, "refresh"), "w", encoding="utf-8") as file:
                file.write("services")
    return 0
