"""사용량 조회 (Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI). 각 서비스 CLI 가 이미 저장해 둔 로그인 정보를 읽기만 한다.

토큰을 갱신하거나 파일을 고쳐 쓰지 않는다. 그 토큰은 사용자의 에이전트 세션이 쓰는 것이라
여기서 갱신하면 에이전트 쪽 로그인이 깨질 수 있다. 만료됐으면 해당 CLI 를 한 번 쓰면 갱신된다.
예외로 Gemini 는 토큰이 1시간짜리라, 바뀌지 않는 refresh token 으로 새 access token 을 받아 메모리에만 둔다.

fetch_*() 는 Usage 를 돌려준다. 실패해도 예외 대신 Usage.error 에 이유 코드를 담는다.
코드는 화면에서 locales 의 error.<코드> 로 번역하고, detail 은 그 문장의 {detail} 에 들어간다.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

HTTP_TIMEOUT_SECONDS = 10
CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
COPILOT_USER_URL = "https://api.github.com/copilot_internal/user"
CODEX_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
GEMINI_API_URL = "https://cloudcode-pa.googleapis.com/v1internal"
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


def _get_json(url, headers, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    if data is not None:
        headers = {"Content-Type": "application/json", **headers}
    request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **headers})
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


def _windows_copilot_cli_tokens(account=None):
    """Copilot CLI 가 Windows 자격 증명 관리자에 저장한 토큰. target 은 '<account>.copilot-cli' 다.

    account 를 주면 그 계정 항목만 읽는다.
    """
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
    target = f"{account}.{COPILOT_CLI_SERVICE}" if account else f"*.{COPILOT_CLI_SERVICE}"
    if not advapi32.CredEnumerateW(target, 0, ctypes.byref(count), ctypes.byref(credentials)):
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


def copilot_cli_tokens(account=None):
    if sys.platform == "win32":
        return _windows_copilot_cli_tokens(account)
    if sys.platform == "darwin":
        extra = ["-a", account] if account else []
        return _command_secret(["security", "find-generic-password", "-s", COPILOT_CLI_SERVICE, *extra, "-w"])
    extra = ["username", account] if account else []
    return _command_secret(["secret-tool", "lookup", "service", COPILOT_CLI_SERVICE, *extra])


def copilot_tokens(config_dir):
    """시도할 토큰 후보. 우선순위: 환경 변수 → 플러그인 config 의 copilot-token 파일 → Copilot CLI 로그인.

    config.json 에 "copilot_account" 가 있으면 Copilot CLI 로그인 중 그 계정만 쓴다.
    """
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
    account = str(read_config(config_dir).get("copilot_account") or "").strip()
    return copilot_cli_tokens(account or None)


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


# ---------------------------------------------------------------- OpenAI Codex


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return None


def codex_auth_path():
    home = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
    return os.path.join(home, "auth.json")


def _epoch_iso(seconds):
    return datetime.fromtimestamp(float(seconds), timezone.utc).isoformat()


def parse_codex(data, now=None):
    limits = data.get("rate_limit") or {}
    windows = []
    for key, source, label in (("five_hour", "primary_window", "5h"), ("seven_day", "secondary_window", "wk")):
        block = limits.get(source)
        if not block:
            continue
        used = block.get("used_percent")
        if block.get("reset_at") is not None:
            resets = _epoch_iso(block["reset_at"])
        elif block.get("reset_after_seconds") is not None:
            resets = _epoch_iso((time.time() if now is None else now) +float(block["reset_after_seconds"]))
        else:
            resets = None
        windows.append(Window(key, label, None if used is None else float(used), resets))
    if not windows:
        return Usage("codex", error="no_quota_data")
    return Usage("codex", windows)


def fetch_codex():
    """ChatGPT 로그인(Codex CLI)의 5시간/주간 한도. API 키로 로그인했으면 한도 정보가 없다."""
    tokens = (_read_json(codex_auth_path()) or {}).get("tokens") or {}
    token = tokens.get("access_token")
    if not token:
        return Usage("codex", error="not_logged_in")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if tokens.get("account_id"):
        headers["ChatGPT-Account-Id"] = tokens["account_id"]
    try:
        data = _get_json(CODEX_USAGE_URL, headers)
    except urllib.error.HTTPError as error:
        return _http_error("codex", error)
    except (OSError, ValueError) as error:
        return Usage("codex", error="network", detail=str(error))
    return parse_codex(data)


# ---------------------------------------------------------------- Google Gemini CLI


def gemini_creds_path():
    return os.path.join(os.path.expanduser("~"), ".gemini", "oauth_creds.json")


def parse_gemini(data):
    """모델별 bucket 중 Pro, Flash 계열에서 가장 많이 쓴(남은 비율이 가장 낮은) 것을 고른다."""
    lowest = {}
    for bucket in data.get("buckets") or []:
        model = str(bucket.get("modelId", "")).lower()
        family = "pro" if "pro" in model else "flash" if "flash" in model else None
        remaining = bucket.get("remainingFraction")
        if family is None or remaining is None:
            continue
        if family not in lowest or float(remaining) < lowest[family][0]:
            lowest[family] = (float(remaining), bucket.get("resetTime"))
    windows = [
        Window(family, label, max(0.0, 100.0 - lowest[family][0] * 100), lowest[family][1])
        for family, label in (("pro", "pro"), ("flash", "fl"))
        if family in lowest
    ]
    if not windows:
        return Usage("gemini", error="no_quota_data")
    return Usage("gemini", windows)


GEMINI_TOKEN_URL = "https://oauth2.googleapis.com/token"
GEMINI_CLIENT_FILES = (
    # Gemini CLI 설치본에서 OAuth client id/secret 을 찾을 파일. 버전마다 위치가 달라 여러 곳을 본다.
    ("@google", "gemini-cli", "node_modules", "@google", "gemini-cli-core", "dist", "src", "code_assist", "oauth2.js"),
    ("@google", "gemini-cli-core", "dist", "src", "code_assist", "oauth2.js"),
    ("@google", "gemini-cli", "bundle", "gemini.js"),
)
_gemini_client = None    # (client_id, client_secret), 한 번 찾으면 기억한다
_gemini_memory = {}      # 메모리에서 갱신한 access token: {"refresh_token", "access_token", "expires_at"}


def _npm_roots():
    roots = []
    if os.environ.get("APPDATA"):
        roots.append(os.path.join(os.environ["APPDATA"], "npm", "node_modules"))
    roots += ["/usr/local/lib/node_modules", "/usr/lib/node_modules", "/opt/homebrew/lib/node_modules",
              os.path.expanduser("~/.npm-global/lib/node_modules")]
    try:
        npm = "npm.cmd" if sys.platform == "win32" else "npm"
        completed = subprocess.run([npm, "root", "-g"], capture_output=True, text=True, timeout=10)
        if completed.returncode == 0 and completed.stdout.strip():
            roots.insert(0, completed.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return roots


def gemini_client():
    """Gemini CLI 의 OAuth client. 환경 변수가 있으면 그것, 없으면 설치된 Gemini CLI 소스에서 읽는다."""
    global _gemini_client
    if os.environ.get("FEEDBAG_GEMINI_CLIENT_ID") and os.environ.get("FEEDBAG_GEMINI_CLIENT_SECRET"):
        return os.environ["FEEDBAG_GEMINI_CLIENT_ID"], os.environ["FEEDBAG_GEMINI_CLIENT_SECRET"]
    if _gemini_client is None:
        _gemini_client = ()
        for root in _npm_roots():
            for parts in GEMINI_CLIENT_FILES:
                try:
                    with open(os.path.join(root, *parts), encoding="utf-8", errors="ignore") as file:
                        source = file.read()
                except OSError:
                    continue
                client_id = re.search(r"OAUTH_CLIENT_ID\s*=\s*['\"]([^'\"]+)", source)
                secret = re.search(r"OAUTH_CLIENT_SECRET\s*=\s*['\"]([^'\"]+)", source)
                if client_id and secret:
                    _gemini_client = (client_id.group(1), secret.group(1))
                    return _gemini_client
    return _gemini_client or None


def _refresh_gemini(refresh_token):
    """refresh token 으로 새 access token 을 받아 메모리에만 둔다. 파일은 고쳐 쓰지 않는다.

    Google 은 refresh token 을 바꾸지 않으므로 Gemini CLI 쪽 로그인은 그대로 유효하다.
    """
    cached = _gemini_memory
    if cached.get("refresh_token") == refresh_token and cached.get("expires_at", 0) > time.time() + 60:
        return cached["access_token"]
    client = gemini_client()
    if not client:
        return None
    body = urllib.parse.urlencode({
        "client_id": client[0], "client_secret": client[1],
        "refresh_token": refresh_token, "grant_type": "refresh_token",
    }).encode("utf-8")
    request = urllib.request.Request(GEMINI_TOKEN_URL, data=body, headers={
        "User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        data = json.load(response)
    token = data.get("access_token")
    if token:
        _gemini_memory.update(refresh_token=refresh_token, access_token=token,
                              expires_at=time.time() + float(data.get("expires_in", 3600)))
    return token


def _gemini_expired(creds):
    expiry_ms = creds.get("expiry_date")
    return bool(expiry_ms) and float(expiry_ms) / 1000 < time.time() + 60


def fetch_gemini():
    """Gemini CLI 의 Google 로그인으로 일일 모델 한도를 본다.

    토큰이 1시간짜리라 만료됐으면 refresh token 으로 메모리에서만 새로 받는다(_refresh_gemini).
    """
    creds = _read_json(gemini_creds_path()) or {}
    token = creds.get("access_token")
    if not token:
        return Usage("gemini", error="not_logged_in")
    try:
        if _gemini_expired(creds):
            token = _refresh_gemini(creds["refresh_token"]) if creds.get("refresh_token") else None
            if not token:
                return Usage("gemini", error="login_expired")
    except urllib.error.HTTPError:
        return Usage("gemini", error="login_expired")
    except (OSError, ValueError) as error:
        return Usage("gemini", error="network", detail=str(error))
    headers = {"Authorization": f"Bearer {token}"}
    try:
        loaded = _get_json(f"{GEMINI_API_URL}:loadCodeAssist", headers,
                           {"metadata": {"ideType": "IDE_UNSPECIFIED", "pluginType": "GEMINI"}})
        project = loaded.get("cloudaicompanionProject")
        if isinstance(project, dict):
            project = project.get("id")
        data = _get_json(f"{GEMINI_API_URL}:retrieveUserQuota", headers, {"project": project} if project else {})
    except urllib.error.HTTPError as error:
        return _http_error("gemini", error)
    except (OSError, ValueError) as error:
        return Usage("gemini", error="network", detail=str(error))
    return parse_gemini(data)


# ---------------------------------------------------------------- 서비스 목록


ALL_PROVIDERS = ("claude", "copilot", "codex", "gemini")


def fetch(name, config_dir=None):
    if name == "claude":
        return fetch_claude()
    if name == "copilot":
        return fetch_copilot(config_dir)
    if name == "codex":
        return fetch_codex()
    if name == "gemini":
        return fetch_gemini()
    raise ValueError(f"unknown provider: {name}")


def config_path(config_dir):
    return os.path.join(config_dir, "config.json") if config_dir else None


def read_config(config_dir):
    path = config_path(config_dir)
    config = _read_json(path) if path else None
    return config if isinstance(config, dict) else {}


def login_status(name, config_dir=None):
    """서비스 선택 화면에 보여 줄 로그인 상태: ok, missing, expired. 네트워크 요청은 하지 않는다."""
    if name == "claude":
        return "ok" if claude_access_token() else "missing"
    if name == "copilot":
        return "ok" if copilot_tokens(config_dir) else "missing"
    if name == "codex":
        tokens = (_read_json(codex_auth_path()) or {}).get("tokens") or {}
        return "ok" if tokens.get("access_token") else "missing"
    if name == "gemini":
        creds = _read_json(gemini_creds_path()) or {}
        if not creds.get("access_token"):
            return "missing"
        if _gemini_expired(creds) and not (creds.get("refresh_token") and gemini_client()):
            return "expired"
        return "ok"
    raise ValueError(f"unknown provider: {name}")


def enabled_providers(config_dir=None):
    """보여 줄 서비스. config.json 의 "providers" 가 있으면 그 순서대로 쓰고,
    없으면 Claude, Copilot 은 항상, Codex, Gemini 는 로그인 파일이 있을 때만 보여 준다."""
    chosen = read_config(config_dir).get("providers")
    if isinstance(chosen, list):
        names = [name for name in chosen if name in ALL_PROVIDERS]
        if names:
            return list(dict.fromkeys(names))
    names = ["claude", "copilot"]
    if os.path.isfile(codex_auth_path()):
        names.append("codex")
    if os.path.isfile(gemini_creds_path()):
        names.append("gemini")
    return names
