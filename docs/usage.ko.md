# 사용법

## 1. 설치

### GitHub에서 설치

```sh
herdr plugin install vrwolf1004/herdr-ai-feedbag
```

### 로컬 폴더 연결 (개발용)

```sh
git clone https://github.com/vrwolf1004/herdr-ai-feedbag.git
herdr plugin link ./herdr-ai-feedbag
```

### 플러그인 관리

```sh
herdr plugin list
herdr plugin update herdr-ai-feedbag
herdr plugin uninstall herdr-ai-feedbag
```

## 2. 사이드바 줄 추가

herdr는 사이드바 레이아웃에 들어 있는 토큰만 그립니다. herdr `config.toml`의 `[ui.sidebar.agents]`에 아래 줄을 넣고 `herdr server reload-config`를 실행하세요.

```toml
[ui.sidebar.agents]
rows = [
  ["state_icon", "machine", { token = "workspace", rules = [{ equals = "herdr-dock", hide = true }] }, "tab"],
  ["agent"],
  [{ token = "$fb_claude", fg = "#d97757", rules = [{ starts_with = "!", fg = "#ff5f5f", bold = true }] }],
  [{ token = "$fb_copilot", fg = "#a371f7", rules = [{ starts_with = "!", fg = "#ff5f5f", bold = true }] }],
]
```

- `$fb_claude`, `$fb_copilot`은 feedbag 블록에만 보고되므로 다른 agent에서는 이 줄이 사라집니다.
- `workspace` rule은 블록 첫 줄에 dock workspace 이름(`herdr-dock`)이 나오지 않게 숨깁니다.
- `!` rule은 경고 기준을 넘은 줄을 빨간색으로 바꿉니다. 색은 원하는 대로 바꿔도 됩니다.
- `ui.agent_panel_sort`는 기본값 `"spaces"`로 두세요. `"priority"`에서는 맨 아래에 고정되지 않습니다.

## 3. 액션

herdr 서버가 시작될 때와 workspace가 만들어질 때 자동으로 시작됩니다. 직접 제어하려면:

| 액션 | 설명 |
| --- | --- |
| `start` | 블록이 없으면 만들고 host를 시작 |
| `refresh` | 지금 바로 다시 조회 |
| `stop` | host를 멈추고 feedbag pane을 닫음 (dock에 다른 블록이 없으면 workspace도 닫음) |

Windows에서는 액션 id 뒤에 `-windows`가 붙습니다.

```sh
herdr plugin action invoke start-windows --plugin herdr-ai-feedbag   # windows
herdr plugin action invoke start --plugin herdr-ai-feedbag           # linux / macos
```

feedbag pane을 Ctrl+C로 닫았으면 herdr 명령 팔레트에서 "feedbag: show usage block"을 실행하거나, 위 명령을 실행하거나, workspace를 하나 만들면 다시 뜹니다. 셸에 `start`만 치면 PowerShell의 `Start-Process`가 실행되니 주의하세요.

## 4. 표시 내용

| 줄 | 막대 | 막대 뒤 |
| --- | --- | --- |
| `cld` | Claude 5시간 세션 한도 | `wk` = 7일 한도 |
| `cop` | Copilot 월간 premium request | `rst` = 리셋 날짜 |

- 막대는 **사용한** 비율입니다. 채워진 부분을 따라 반짝임이 2초에 한 칸씩 흘러갑니다.
- 어느 창이든 80% 이상이면 앞의 `●`가 깜빡이는 `!`로 바뀝니다. 앞 표시는 항상 한 칸이라 줄이 밀리지 않습니다.
- 이모지 없이 클래식 박스 문자(`█▓▒░►`)만 씁니다.
- `feedbag` pane에는 Copilot chat, inline을 포함한 모든 창과 리셋 시각이 보입니다.

조회 주기: Claude 5분, Copilot 10분. 아직 숫자가 없을 때 실패하면 30초 뒤 다시 시도합니다. rate limit에 걸리면 주기의 3배로 늦춥니다.

## 5. 로그인 정보

읽기만 하고 토큰을 갱신하거나 고쳐 쓰지 않습니다. 로그인이 만료됐으면 해당 CLI를 한 번 쓰면 다음 조회부터 새 토큰을 씁니다.

| 서비스 | 위치 (먼저 찾은 것 사용) |
| --- | --- |
| Claude Code | `~/.claude/.credentials.json` (`CLAUDE_CONFIG_DIR` 지원) |
| GitHub Copilot | `FEEDBAG_COPILOT_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN` → 플러그인 config 폴더의 `copilot-token` 파일 → Copilot CLI 로그인 (Windows 자격 증명 관리자, macOS 키체인, Linux `secret-tool`) |

플러그인 config 폴더는 `herdr plugin config-dir herdr-ai-feedbag`로 확인합니다.

## 6. 표시 언어

대시보드와 오류 문구는 `en`, `ko`, `ru`, `fr`, `es`, `de`, `ja`를 지원합니다. 언어는 다음 순서로 정합니다.

1. 환경 변수 `HERDR_FEEDBAG_LANG`
2. 플러그인 config 폴더의 `config.json`에 있는 `"lang"` (예: `{"lang": "ko"}`)
3. OS 언어 (Windows는 표시 언어, Linux/macOS는 `LC_ALL`, `LC_MESSAGES`, `LANG` 순)
4. 지원하지 않거나 알 수 없으면 영어(`en`)

사이드바의 짧은 표시(`cld`, `cop`, `wk`, `rst`)는 줄 폭이 바뀌지 않도록 모든 언어에서 그대로 둡니다. 번역이 없는 문구는 영어로 나옵니다.

## 7. herdr-sidebar와 함께 쓸 때

[herdr-sidebar](https://github.com/alexarthurs/herdr-sidebar)는 포커스된 모든 탭에 탐색기를 띄우므로 `herdr-dock` workspace에도 뜹니다. feedbag이 이를 발견하면 1초 뒤 그 사이드바의 숨기기 키(`b`)를 보냅니다. herdr-sidebar가 그 탭을 기억하고 다시 열지 않습니다.
