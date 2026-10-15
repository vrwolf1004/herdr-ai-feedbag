"""사용량 조회. 각 서비스 CLI 가 이미 저장해 둔 로그인 정보를 읽기만 한다.

토큰을 갱신하거나 파일을 고쳐 쓰지 않는다. 그 토큰은 사용자의 에이전트 세션이 쓰는 것이라
여기서 갱신하면 에이전트 쪽 로그인이 깨질 수 있다. 만료됐으면 해당 CLI 를 한 번 쓰면 갱신된다.

fetch_*() 는 Usage 를 돌려준다. 실패해도 예외 대신 Usage.error 에 이유 코드를 담는다.
코드는 화면에서 locales 의 error.<코드> 로 번역하고, detail 은 그 문장의 {detail} 에 들어간다.
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional

HTTP_TIMEOUT_SECONDS = 10
CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
COPILOT_USER_URL = "https://api.github.com/copilot_internal/user"
USER_AGENT = "herdr-ai-feedbag"


@dataclass
class Window:
    """사용량 창 하나. used_pct 는 사용한 비율(0~100), None 이면 무제한/정보 없음."""

    key: str
    label: str
    used_pct: Optional[float]
    resets_at: Optional[str] = None


@dataclass
class Usage:
    provider: str
    windows: List[Window] = field(default_factory=list)
    error: Optional[str] = None  # not_logged_in, login_expired, rate_limited, network, http, no_quota_data
    detail: str = ""
    rate_limited: bool = False


def _get_json(url, headers):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return json.load(response)


def _http_error(provider, error):
    if error.code == 429:
        return Usage(provider, error="rate_limited", rate_limited=True)
    if error.code in (401, 403):
        return Usage(provider, error="login_expired")
    return Usage(provider, error="http", detail=str(error.code))


# ---------------------------------------------------------------- Claude


def claude_credentials_path():
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(config_dir, ".credentials.json")


def claude_access_token():
    try:
        with open(claude_credentials_path(), encoding="utf-8") as file:
            credentials = json.load(file)
    except (OSError, ValueError):
        return None
    return (credentials.get("claudeAiOauth") or {}).get("accessToken")


def parse_claude(data):
    windows = []
    for key, label in (("five_hour", "5h"), ("seven_day", "wk")):
        block = data.get(key) or {}
        used = block.get("utilization")
        windows.append(Window(key, label, None if used is None else float(used), block.get("resets_at")))
    return Usage("claude", windows)


def fetch_claude():
    token = claude_access_token()
    if not token:
        return Usage("claude", error="not_logged_in")
    try:
        data = _get_json(CLAUDE_USAGE_URL, {
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
        })
    except urllib.error.HTTPError as error:
        return _http_error("claude", error)
    except (OSError, ValueError) as error:
        return Usage("claude", error="network", detail=str(error))
    return parse_claude(data)


# ---------------------------------------------------------------- GitHub Copilot


COPILOT_CLI_SERVICE = "copilot-cli"


def _decode_secret(blob):
    # keyring 구현에 따라 UTF-16LE 또는 UTF-8 로 저장된다.
    if len(blob) >= 2 and len(blob) % 2 == 0 and blob[1:2] == b"\x00":
        return blob.decode("utf-16-le", errors="ignore").strip("\x00").strip()
    return blob.decode("utf-8", errors="ignore").strip()


def _windows_copilot_cli_tokens():
    """Copilot CLI 가 Windows 자격 증명 관리자에 저장한 토큰. target 은 '<account>.copilot-cli' 다."""
    import ctypes
    from ctypes import wintypes

    class Credential(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
        ]

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    count = wintypes.DWORD()
    credentials = ctypes.POINTER(ctypes.POINTER(Credential))()
    if not advapi32.CredEnumerateW(f"*.{COPILOT_CLI_SERVICE}", 0, ctypes.byref(count), ctypes.byref(credentials)):
        return []
    tokens = []
    try:
        for index in range(count.value):
            credential = credentials[index].contents
            blob = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
            token = _decode_secret(blob)
            if token:
                tokens.append(token)
    finally:
        advapi32.CredFree(credentials)
    return tokens


def _command_secret(command):
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return []
    value = completed.stdout.strip() if completed.returncode == 0 else ""
    return [value] if value else []


def copilot_cli_tokens():
    if sys.platform == "win32":
        return _windows_copilot_cli_tokens()
    if sys.platform == "darwin":
        return _command_secret(["security", "find-generic-password", "-s", COPILOT_CLI_SERVICE, "-w"])
    return _command_secret(["secret-tool", "lookup", "service", COPILOT_CLI_SERVICE])


def copilot_tokens(config_dir):
    """시도할 토큰 후보. 우선순위: 환경 변수 → 플러그인 config 의 copilot-token 파일 → Copilot CLI 로그인."""
    for name in ("FEEDBAG_COPILOT_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return [value]
    if config_dir:
        try:
            with open(os.path.join(config_dir, "copilot-token"), encoding="utf-8") as file:
                value = file.read().strip()
            if value:
                return [value]
        except OSError:
            pass
    return copilot_cli_tokens()


def parse_copilot(data):
    snapshots = data.get("quota_snapshots") or {}
    reset = data.get("quota_reset_date_utc") or data.get("quota_reset_date")
    windows = []
    for key, label in (("premium_interactions", "premium"), ("chat", "chat"), ("completions", "inline")):
        snapshot = snapshots.get(key)
        if not snapshot:
            continue
        if snapshot.get("unlimited"):
            used = None
        else:
            remaining = snapshot.get("percent_remaining")
            used = None if remaining is None else max(0.0, 100.0 - float(remaining))
        windows.append(Window(key, label, used, reset))
    if not windows:
        return Usage("copilot", error="no_quota_data")
    return Usage("copilot", windows)


def fetch_copilot(config_dir=None):
    tokens = copilot_tokens(config_dir)
    if not tokens:
        return Usage("copilot", error="not_logged_in")
    failure = None
    # Copilot CLI 는 계정마다 항목을 남긴다. 처음으로 응답하는 토큰을 쓴다.
    for token in tokens:
        try:
            data = _get_json(COPILOT_USER_URL, {
                "Authorization": f"token {token}",
                "Accept": "application/json",
            })
        except urllib.error.HTTPError as error:
            failure = _http_error("copilot", error)
            if error.code == 429:
                return failure
            continue
        except (OSError, ValueError) as error:
            return Usage("copilot", error="network", detail=str(error))
        return parse_copilot(data)
    return failure
