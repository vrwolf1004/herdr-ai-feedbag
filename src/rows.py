"""herdr config.toml 의 사이드바 줄($fb_<서비스>) 검사. 파일은 읽기만 하고 고치지 않는다.

config.toml 은 사용자의 다른 설정과 섞여 있어서, 빠진 줄은 보여 주기만 하고 넣는 것은 사용자에게 맡긴다.
"""

import os

ROW_COLORS = {"claude": "#d97757", "copilot": "#a371f7", "codex": "#10a37f", "gemini": "#4285f4"}
WARN_COLOR = "#ff5f5f"


def herdr_config_path():
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "herdr", "config.toml")


def row_line(name):
    color = ROW_COLORS.get(name, "#c9d1d9")
    return (f'  [{{ token = "$fb_{name}", fg = "{color}", '
            f'rules = [{{ starts_with = "!", fg = "{WARN_COLOR}", bold = true }}] }}],')


def missing_rows(names, path=None):
    """config.toml 에 줄이 없는 서비스 목록. 파일이 없으면 전부 빠진 것으로 본다."""
    try:
        with open(path or herdr_config_path(), encoding="utf-8") as file:
            text = file.read()
    except OSError:
        text = ""
    return [name for name in names if f'"$fb_{name}"' not in text and f"'$fb_{name}'" not in text]
