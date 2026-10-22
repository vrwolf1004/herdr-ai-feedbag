"""herdr-ai-feedbag: Claude Code / GitHub Copilot 사용량을 herdr 사이드바 맨 아래에 한 번만 보여 준다.

동작 방식
  - 공용 "herdr-dock" workspace 에 pane 하나를 두고 가짜 agent(feedbag)로 등록한다. dock 이 없으면 만들고,
    이미 있으면(다른 플러그인이 만든 경우) pane 을 나눠 들어간다.
    agents 패널은 spaces 순서로 정렬되므로 dock 을 항상 맨 뒤로 옮기면 블록이 맨 아래에 온다.
  - 그 pane 에서 host 루프가 돈다. 별도 백그라운드 프로세스를 두지 않으므로 pane 을 닫으면 같이 끝난다.
  - 사용량 숫자는 $fb_<서비스>(claude, copilot, codex, gemini) 토큰으로 이 pane 에만 붙는다. 다른 agent 행에는 나오지 않는다.

명령
  ensure  workspace 와 host 를 확인하고 없으면 띄운다 (startup / event hook)
  host    feedbag pane 안에서 도는 루프. 상세 화면 표시 + 사이드바 토큰 갱신
  refresh host 에게 즉시 다시 조회하라고 알린다
  stop    host 를 멈추고 workspace 를 닫는다
  services    서비스 선택 화면(services-ui)을 overlay pane 으로 띄운다
  rows    herdr config.toml 에 빠진 사이드바 줄을 출력한다
"""

import argparse
import dataclasses
import os
import sys
import threading
import time
from datetime import datetime

import herdr_api


def load_dock_layout():
    """설치된 herdr-dock-grid 가 있으면 그 원본을, 없으면 이 plugin 의 복사본(src/dock_layout.py)을 쓴다."""
    grid = herdr_api.installed_plugin_path("herdr-dock-grid")
    if grid:
        sys.path.insert(0, os.path.join(grid, "src"))
    import dock_layout
    return dock_layout


dock = load_dock_layout()
FEEDBAG_KEY = "herdr-ai-feedbag"
import i18n
import providers
import render

PLUGIN_ID = "herdr-ai-feedbag"
SOURCE = f"plugin:{PLUGIN_ID}"
# 하단 고정 블록을 두는 공용 workspace. 다른 플러그인도 같은 이름을 찾아 pane 을 나눠 들어오면
# agents 패널에서 feedbag 과 함께 맨 아래에 모인다.
DOCK_LABEL = "herdr-dock"
# 도크 블록이 3개일 때 빈 4번째 칸에 띄우는 소개 pane 의 이름 (정의는 intro.py 에 있다)
INTRO_LABEL = "herdr-dock-intro"
INTRO_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "intro.py")
AGENT_ID = "feedbag"
DISPLAY_AGENT = "feedbag"

TICK_SECONDS = 1             # 루프 한 바퀴 (heartbeat, 토큰 갱신)
FRAME_TICKS = 2               # 이 바퀴 수마다 애니메이션이 한 칸 움직인다
HEARTBEAT_STALE_SECONDS = 10  # 이보다 오래 heartbeat 가 없으면 host 가 죽은 것으로 본다
TOKEN_TTL_MS = 15_000         # host 가 죽으면 토큰이 이 시간 뒤 사라진다
LAYOUT_EVERY_TICKS = 5        # 맨 아래 위치 확인, agent 재등록 주기
FETCH_SECONDS = {"claude": 300, "copilot": 600, "codex": 300, "gemini": 600}
RATE_LIMIT_BACKOFF = 3
RETRY_SECONDS = 30
# herdr-sidebar 는 포커스된 탭마다 사이드바를 자동으로 띄운다. feedbag 탭에 뜨면 잠시 뒤 그 사이드바의
# 숨기기 키(b)를 보낸다. 사용자가 직접 숨긴 것과 같아서 herdr-sidebar 가 이 탭을 기억하고 다시 열지 않는다.
SIDEBAR_TOKEN_PREFIX = "herdr-sidebar"
SIDEBAR_HIDE_KEY = "b"
SIDEBAR_HIDE_DELAY_SECONDS = 1
SIDEBAR_HIDE_RETRY_SECONDS = 5
MAX_SOCKET_FAILURES = 10


# ---------------------------------------------------------------- 경로/상태 파일


def default_state_dir():
    path = os.environ.get("HERDR_PLUGIN_STATE_DIR")
    if path:
        return path
    base = os.environ.get("LOCALAPPDATA") if herdr_api.IS_WINDOWS else os.path.expanduser("~/.local/state")
    return os.path.join(base or os.path.expanduser("~"), "herdr", "plugins", PLUGIN_ID)


def default_config_dir():
    return os.environ.get("HERDR_PLUGIN_CONFIG_DIR") or ""


class State:
    """state dir 안의 작은 파일들. host 와 hook 이 서로 다른 프로세스라 파일로 주고받는다."""

    def __init__(self, directory):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def path(self, name):
        return os.path.join(self.directory, name)

    def read(self, name):
        try:
            with open(self.path(name), encoding="utf-8") as file:
                return file.read().strip() or None
        except OSError:
            return None

    def write(self, name, value):
        # 임시 파일에 쓰고 바꿔 끼운다. 중간에 멈춰도 읽는 쪽은 예전 값이나 새 값 중 하나만 본다.
        target = self.path(name)
        temp = target + ".tmp"
        with open(temp, "w", encoding="utf-8") as file:
            file.write(value)
        os.replace(temp, target)

    def remove(self, name):
        try:
            os.remove(self.path(name))
        except OSError:
            pass

    def touch_heartbeat(self):
        self.write("heartbeat", str(time.time()))

    def host_alive(self):
        beat = self.read("heartbeat")
        try:
            return beat is not None and time.time() - float(beat) < HEARTBEAT_STALE_SECONDS
        except ValueError:
            return False


# ---------------------------------------------------------------- workspace / pane


def workspace_panes(workspace_id):
    panes = herdr_api.cli("pane", "list").get("panes", [])
    return [p for p in panes if p["workspace_id"] == workspace_id]


def is_sidebar(pane):
    return any(name.startswith(SIDEBAR_TOKEN_PREFIX) for name in (pane.get("tokens") or {}))


def foreign_tokens(pane):
    """이 플러그인(fb_*)이 아닌 토큰이 있는지. 예전 feedbag 토큰은 ttl 이 지나면 사라지므로 빈 pane 으로 본다."""
    return any(not name.startswith("fb_") for name in (pane.get("tokens") or {}))


def ensure_intro(workspace_id, new_pane, cwd):
    """도크 블록이 3개이고 소개 칸이 없으면 빈 4번째 칸에 소개 문구를 띄운다. 이미 있으면 아무것도 하지 않는다."""
    agent_panes = {a["pane_id"] for a in herdr_api.cli("agent", "list").get("agents", [])}
    panes = [p for p in workspace_panes(workspace_id) if not is_sidebar(p)]
    if any(p.get("label") == INTRO_LABEL for p in panes):
        return
    blocks = [p for p in panes if p["pane_id"] in agent_panes or p["pane_id"] == new_pane]
    if len(blocks) != 3:
        return
    if any(not p.get("label") and not p.get("tokens") and p["pane_id"] not in agent_panes and p["pane_id"] != new_pane
           for p in panes):
        return  # 빈 칸이 이미 있으면 그 칸은 나중 블록이 쓴다
    pane_id = dock.grid_split(blocks[0]["pane_id"], cwd)
    herdr_api.cli("pane", "rename", pane_id, INTRO_LABEL)
    herdr_api.cli("pane", "run", pane_id, sys.executable, "-X", "utf8", INTRO_SCRIPT)


def ensure_workspace(state):
    """공용 dock workspace 와 그 안의 feedbag pane 을 확보한다. 자리 배정과 정리는 herdr-dock-grid 공용 모듈이 한다."""
    workspace_id, pane_id = dock.ensure_dock_pane(FEEDBAG_KEY, state.directory)
    state.write("workspace.id", workspace_id)
    panes = workspace_panes(workspace_id)
    if any(p["pane_id"] == pane_id and p.get("label") == INTRO_LABEL for p in panes):
        herdr_api.cli("pane", "rename", pane_id, "--clear")  # 소개 칸을 블록이 쓰므로 이름을 지운다
    state.write("pane.id", pane_id)
    ensure_intro(workspace_id, pane_id, state.directory)
    return workspace_id, pane_id


def keep_at_bottom(workspace_id):
    workspaces = herdr_api.request("workspace.list", {}).get("workspaces", [])
    ids = [w["workspace_id"] for w in workspaces]
    if workspace_id not in ids:
        return False
    if ids[-1] != workspace_id:
        # insert_index 는 옮기기 전 목록 기준 "이 위치 앞에 넣기"다. 길이를 주면 맨 뒤로 간다.
        herdr_api.try_request("workspace.move", {"workspace_id": workspace_id, "insert_index": len(ids)})
    return True


# ---------------------------------------------------------------- ensure / stop / refresh


def host_command(state_dir, config_dir, pane_id):
    script = os.path.abspath(__file__)
    command = [sys.executable, "-X", "utf8", script, "host", "--state", state_dir, "--pane", pane_id]
    if config_dir:
        command += ["--config", config_dir]
    return command


def pane_alive(pane_id):
    """pane 이 아직 herdr 에 있는지. 닫힌 pane 의 heartbeat 가 몇 초 남아 있어도 블록은 다시 띄워야 한다."""
    if not pane_id:
        return False
    return herdr_api.cli("pane", "get", pane_id, check=False) is not None


def cmd_ensure(args):
    state = State(args.state)
    if state.host_alive() and pane_alive(state.read("pane.id")):
        return 0
    # workspace 를 만들면 workspace.created hook 이 곧바로 ensure 를 한 번 더 부른다.
    # host 가 첫 heartbeat 를 쓰기 전이라 두 번째 호출이 같은 pane 에 명령을 또 입력하지 않도록 막는다.
    starting = state.read("starting")
    try:
        if starting is not None and time.time() - float(starting) < HEARTBEAT_STALE_SECONDS:
            return 0
    except ValueError:
        pass
    state.write("starting", str(time.time()))
    _, pane_id = ensure_workspace(state)
    state.remove("stop")
    herdr_api.cli("pane", "run", pane_id, *host_command(args.state, args.config, pane_id))
    return 0


def cmd_refresh(args):
    state = State(args.state)
    state.write("refresh", str(time.time()))
    return cmd_ensure(args)


def cmd_stop(args):
    state = State(args.state)
    state.write("stop", str(time.time()))
    deadline = time.time() + 3
    while state.host_alive() and time.time() < deadline:
        time.sleep(0.2)
    workspace_id = state.read("workspace.id")
    pane_id = state.read("pane.id")
    if workspace_id:
        # dock 은 다른 플러그인과 같이 쓴다. 자기 pane 만 닫고, 남은 게 herdr-sidebar 뿐이면 workspace 도 닫는다.
        others = [p for p in workspace_panes(workspace_id) if p["pane_id"] != pane_id and not is_sidebar(p)]
        if others:
            if pane_id:
                herdr_api.cli("pane", "close", pane_id, check=False)
            ensure_intro(workspace_id, None, state.directory)  # 블록이 빠져 생긴 빈 칸에 소개를 띄운다
        else:
            herdr_api.cli("workspace", "close", workspace_id, check=False)
    for name in ("workspace.id", "pane.id", "heartbeat"):
        state.remove(name)
    return 0


# ---------------------------------------------------------------- host


class Host:
    def __init__(self, args):
        self.state = State(args.state)
        self.config_dir = args.config
        self.pane_id = args.pane
        self.workspace_id = self.state.read("workspace.id")
        self.usages = {}
        self.next_fetch = {}
        self.config_mtime = None
        self.sync_providers()
        self.updated_at = None
        self.socket_failures = 0
        self.sidebar_seen = {}  # 사이드바 pane id → 처음 본 시각
        self.sidebar_sent = {}  # 사이드바 pane id → 마지막으로 숨기기 키를 보낸 시각

    def config_changed(self):
        try:
            mtime = os.path.getmtime(providers.config_path(self.config_dir) or "")
        except OSError:
            mtime = None
        changed = mtime != self.config_mtime
        self.config_mtime = mtime
        return changed

    def sync_providers(self):
        """config.json 의 providers 를 다시 읽는다. 이미 있던 서비스는 숫자와 조회 일정을 그대로 둔다."""
        self.config_changed()
        names = providers.enabled_providers(self.config_dir)
        for name in set(self.usages) - set(names):
            # 끈 서비스의 줄은 ttl 을 기다리지 않고 바로 지운다.
            herdr_api.cli("pane", "report-metadata", self.pane_id, "--source", SOURCE, "--clear-token", f"fb_{name}",
                          check=False)
        self.usages = {name: self.usages.get(name) or providers.Usage(name, error="loading") for name in names}
        self.next_fetch = {name: self.next_fetch.get(name, 0.0) for name in names}

    def fetch_due(self, now):
        forced = self.state.read("refresh") is not None
        if forced:
            self.state.remove("refresh")
        if forced or self.config_changed():
            self.sync_providers()
        for name in self.usages:
            if not forced and now < self.next_fetch[name]:
                continue
            try:
                fetched = providers.fetch(name, self.config_dir)
            except Exception as error:  # noqa: BLE001 - 제공자 하나의 예외가 host 루프를 멈추지 않게 한다
                fetched = providers.Usage(name, error=type(error).__name__)
            previous = self.usages[name]
            if fetched.error and previous.windows:
                # 일시적인 실패면 마지막 숫자를 유지하고 실패 이유만 보여 준다.
                fetched = dataclasses.replace(fetched, windows=previous.windows)
            self.usages[name] = fetched
            if fetched.rate_limited:
                interval = FETCH_SECONDS[name] * RATE_LIMIT_BACKOFF
            elif fetched.error and not fetched.windows:
                interval = RETRY_SECONDS  # 보여 줄 숫자가 아직 없으면 빨리 다시 시도한다
            else:
                interval = FETCH_SECONDS[name]
            self.next_fetch[name] = now + interval
            self.updated_at = datetime.now()

    def report(self, frame):
        tokens = {f"fb_{name}": render.sidebar_token(usage, frame) for name, usage in self.usages.items()}
        ok = herdr_api.try_request("pane.report_metadata", {
            "pane_id": self.pane_id,
            "source": SOURCE,
            "display_agent": DISPLAY_AGENT,
            "tokens": tokens,
            "ttl_ms": TOKEN_TTL_MS,
        })
        self.socket_failures = 0 if ok else self.socket_failures + 1

    def register_agent(self):
        herdr_api.try_request("pane.report_agent", {
            "pane_id": self.pane_id,
            "source": SOURCE,
            "agent": AGENT_ID,
            "state": "idle",
        })
        if self.workspace_id:
            try:
                keep_at_bottom(self.workspace_id)
            except (herdr_api.HerdrError, ValueError):
                pass

    def hide_foreign_sidebars(self, now):
        if not self.workspace_id:
            return
        try:
            panes = herdr_api.request("pane.list", {"workspace_id": self.workspace_id}).get("panes", [])
        except (herdr_api.HerdrError, ValueError):
            return
        sidebars = {
            p["pane_id"] for p in panes
            if p["pane_id"] != self.pane_id
            and is_sidebar(p)
        }
        for pane_id in list(self.sidebar_seen):
            if pane_id not in sidebars:
                self.sidebar_seen.pop(pane_id, None)
                self.sidebar_sent.pop(pane_id, None)
        for pane_id in sidebars:
            first_seen = self.sidebar_seen.setdefault(pane_id, now)
            if now - first_seen < SIDEBAR_HIDE_DELAY_SECONDS:
                continue
            if now - self.sidebar_sent.get(pane_id, 0) < SIDEBAR_HIDE_RETRY_SECONDS:
                continue
            herdr_api.try_request("pane.send_keys", {"pane_id": pane_id, "keys": [SIDEBAR_HIDE_KEY]})
            self.sidebar_sent[pane_id] = now

    def draw(self, frame):
        lines = render.detail_lines(list(self.usages.values()), frame, self.updated_at)
        # 같은 자리에 덮어쓴다. 화면을 지우면 터미널 스크롤백에 이전 프레임이 쌓인다.
        painted = "\n".join(line + "\033[K" for line in lines)
        sys.stdout.write("\033[H" + painted + "\033[J")
        sys.stdout.flush()

    def fetch_forever(self):
        """조회는 별도 스레드에서 한다. 느린 네트워크가 애니메이션과 heartbeat 를 멈추지 않게 한다."""
        while self.state.read("stop") is None:
            try:
                self.fetch_due(time.time())
            except Exception:  # noqa: BLE001 - 조회 스레드가 죽으면 사이드바 숫자가 멈춘다
                pass
            time.sleep(TICK_SECONDS)

    def run(self):
        sys.stdout.write("\033[?25l")  # 커서 숨김
        self.state.remove("starting")
        threading.Thread(target=self.fetch_forever, daemon=True).start()
        tick = 0
        try:
            while self.state.read("stop") is None and self.socket_failures < MAX_SOCKET_FAILURES:
                self.state.touch_heartbeat()
                now = time.time()
                if tick % LAYOUT_EVERY_TICKS == 0:
                    self.register_agent()
                self.hide_foreign_sidebars(now)
                frame = tick // FRAME_TICKS
                self.report(frame)
                self.draw(frame)
                tick += 1
                time.sleep(TICK_SECONDS)
        finally:
            sys.stdout.write("\033[?25h")
            herdr_api.try_request("pane.release_agent", {"pane_id": self.pane_id, "source": SOURCE, "agent": AGENT_ID})
            self.state.remove("heartbeat")
            self.state.remove("stop")
        return 0


def cmd_services(args):
    """서비스 선택 화면을 overlay pane 으로 띄운다. pane 안의 프로세스는 플러그인 환경을 못 받으므로 넘겨 준다."""
    entrypoint = "services-windows" if herdr_api.IS_WINDOWS else "services"
    command = ["plugin", "pane", "open", "--plugin", PLUGIN_ID, "--entrypoint", entrypoint,
               "--placement", "overlay", "--focus",
               "--env", f"HERDR_PLUGIN_STATE_DIR={args.state}"]
    if args.config:
        command += ["--env", f"HERDR_PLUGIN_CONFIG_DIR={args.config}"]
    herdr_api.cli(*command)
    return 0


def cmd_services_ui(args):
    import services
    return services.run(args.config, args.state)


def cmd_rows(args):
    """켜진 서비스 중 herdr config.toml 에 사이드바 줄이 없는 것을 출력한다. 파일은 고치지 않는다."""
    import rows
    missing = rows.missing_rows(providers.enabled_providers(args.config))
    if not missing:
        print(f"feedbag: all sidebar rows are in {rows.herdr_config_path()}")
        return 0
    print(f"feedbag: add these rows to [ui.sidebar.agents] rows in {rows.herdr_config_path()}, "
          "then run `herdr server reload-config`:")
    for name in missing:
        print(rows.row_line(name))
    return 0


def cmd_host(args):
    try:
        return Host(args).run()
    except KeyboardInterrupt:
        return 0


# ---------------------------------------------------------------- main


def main(argv=None):
    parser = argparse.ArgumentParser(prog="feedbag")
    parser.add_argument("command", choices=["ensure", "host", "refresh", "stop", "services", "services-ui", "rows"])
    parser.add_argument("--state", default=default_state_dir())
    parser.add_argument("--config", default=default_config_dir())
    parser.add_argument("--pane", default=os.environ.get("HERDR_PANE_ID"))
    args = parser.parse_args(argv)
    if args.config and not os.environ.get("HERDR_PLUGIN_CONFIG_DIR"):
        # host 는 pane 안에서 돌아 플러그인 환경을 받지 못한다. config.json 의 lang 을 읽도록 넘겨 준다.
        os.environ["HERDR_PLUGIN_CONFIG_DIR"] = args.config
        i18n.set_language(i18n.detect())
    commands = {
        "ensure": cmd_ensure, "host": cmd_host, "refresh": cmd_refresh, "stop": cmd_stop,
        "services": cmd_services, "services-ui": cmd_services_ui, "rows": cmd_rows,
    }
    try:
        return commands[args.command](args)
    except herdr_api.HerdrError as error:
        print(f"feedbag: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
