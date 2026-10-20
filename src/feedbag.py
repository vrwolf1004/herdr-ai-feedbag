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
import time
from datetime import datetime

import herdr_api
import i18n
import providers
import render

PLUGIN_ID = "herdr-ai-feedbag"
SOURCE = f"plugin:{PLUGIN_ID}"
# 하단 고정 블록을 두는 공용 workspace. 다른 플러그인도 같은 이름을 찾아 pane 을 나눠 들어오면
# agents 패널에서 feedbag 과 함께 맨 아래에 모인다.
DOCK_LABEL = "herdr-dock"
LEGACY_WS_LABEL = "feedbag"
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
        with open(self.path(name), "w", encoding="utf-8") as file:
            file.write(value)

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


def find_workspace(workspaces):
    by_label = {w.get("label"): w["workspace_id"] for w in workspaces}
    if DOCK_LABEL in by_label:
        return by_label[DOCK_LABEL]
    legacy = by_label.get(LEGACY_WS_LABEL)
    if legacy:
        # 0.1.0 은 자기 전용 "feedbag" workspace 를 썼다. 공용 dock 으로 이름만 바꿔 이어 쓴다.
        herdr_api.cli("workspace", "rename", legacy, DOCK_LABEL, check=False)
    return legacy


def workspace_panes(workspace_id):
    panes = herdr_api.cli("pane", "list").get("panes", [])
    return [p for p in panes if p["workspace_id"] == workspace_id]


def is_sidebar(pane):
    return any(name.startswith(SIDEBAR_TOKEN_PREFIX) for name in (pane.get("tokens") or {}))


def claimed_by_others(state_dir):
    """같은 plugins 폴더의 다른 플러그인이 pane.id 로 찜해 둔 pane 목록. 그 pane 은 건드리지 않는다."""
    plugins_dir = os.path.dirname(os.path.abspath(state_dir))
    own = os.path.basename(os.path.abspath(state_dir))
    claimed = set()
    for name in os.listdir(plugins_dir) if os.path.isdir(plugins_dir) else []:
        if name == own:
            continue
        try:
            with open(os.path.join(plugins_dir, name, "pane.id"), encoding="utf-8") as f:
                claimed.add(f.read().strip())
        except OSError:
            pass
    return claimed


def pick_pane(panes, stored_pane, agent_panes, claimed=frozenset()):
    """dock 안에서 host 를 띄울 pane.

    기억해 둔 pane 이 살아 있고 다른 플러그인이 찜하지 않았으면 그것, 아니면 아무도 쓰지 않는 빈 pane
    (label·token·agent 없음, 다른 플러그인이 찜하지 않은 것). 다른 플러그인 블록이나 herdr-sidebar pane 은
    건드리지 않는다. 쓸 빈 pane 이 없으면 None 이고, 호출한 쪽이 split 해서 새로 만든다.
    """
    ids = [p["pane_id"] for p in panes]
    if stored_pane in ids and stored_pane not in claimed:
        return stored_pane
    free = [p["pane_id"] for p in panes
            if not p.get("label") and not p.get("tokens") and p["pane_id"] not in agent_panes
            and p["pane_id"] not in claimed]
    return free[0] if free else None


def ensure_workspace(state):
    """공용 dock workspace 와 그 안의 feedbag pane 을 확보한다. dock 이 있으면 pane 을 하나 나눠 들어간다."""
    workspaces = herdr_api.cli("workspace", "list").get("workspaces", [])
    workspace_id = find_workspace(workspaces)
    if workspace_id is None:
        # cwd 를 git 저장소가 아닌 state dir 로 두어 branch/git 표시가 비게 한다.
        created = herdr_api.cli("workspace", "create", "--label", DOCK_LABEL, "--cwd", state.directory, "--no-focus")
        workspace_id = created["workspace"]["workspace_id"]
        state.remove("pane.id")
    state.write("workspace.id", workspace_id)
    panes = workspace_panes(workspace_id)
    agent_panes = {a["pane_id"] for a in herdr_api.cli("agent", "list").get("agents", [])}
    pane_id = pick_pane(panes, state.read("pane.id"), agent_panes, claimed_by_others(state.directory))
    if pane_id is None:
        anchor = next((p["pane_id"] for p in panes if not is_sidebar(p)), None)
        if anchor is None:
            raise herdr_api.HerdrError(f"workspace {workspace_id} has no pane")
        split = herdr_api.cli("pane", "split", anchor, "--direction", "down", "--cwd", state.directory)
        pane_id = split["pane"]["pane_id"]
    state.write("pane.id", pane_id)
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


def cmd_ensure(args):
    state = State(args.state)
    if state.host_alive():
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
            fetched = providers.fetch(name, self.config_dir)
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

    def run(self):
        sys.stdout.write("\033[?25l")  # 커서 숨김
        self.state.remove("starting")
        tick = 0
        try:
            while self.state.read("stop") is None and self.socket_failures < MAX_SOCKET_FAILURES:
                self.state.touch_heartbeat()
                now = time.time()
                self.fetch_due(now)
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
