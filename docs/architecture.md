# 구조 및 동작 방식

## 왜 가짜 agent인가

계정 사용량은 계정 단위인데 기존 플러그인들은 agent pane마다 토큰을 붙여서, Claude pane이 셋이면 같은 숫자가 세 번 보였습니다. herdr 사이드바에는 "맨 아래 고정 영역"이 없으므로 다음처럼 만듭니다.

1. 공용 `herdr-dock` workspace에 pane을 하나 두고 가짜 agent(`feedbag`)로 등록합니다 (`pane.report_agent`). dock이 없으면 만들고, 다른 플러그인이 이미 만들었으면 dock 안의 빈 자리(2×2 격자)에 pane을 나눠 들어갑니다.
2. agents 패널은 기본적으로 spaces 순서로 정렬되므로, 이 workspace를 항상 맨 뒤로 옮기면 블록이 맨 아래에 옵니다 (`workspace.move`).
3. 사용량은 이 pane에만 `$fb_claude`, `$fb_copilot`, `$fb_codex`, `$fb_gemini` 토큰으로 붙입니다 (`pane.report_metadata`). 값을 보고하지 않은 토큰과 그 줄은 herdr가 그리지 않으므로 다른 agent 행에는 나오지 않습니다.

`rows_by_agent`는 공식 agent id에만 적용되고 직접 등록한 agent는 기본 `rows`를 쓰기 때문에, 기본 `rows`에 줄을 추가하는 방식을 씁니다.

## 프로세스

```text
startup / workspace.created hook ── ensure ──┐
start / refresh / stop action ───────────────┤
                                             ▼
                          herdr-dock workspace 의 feedbag pane
                          └─ host 루프 (1초마다)
                               ├─ heartbeat 기록
                               ├─ 주기가 된 서비스 조회 (Claude·Codex 5분, Copilot·Gemini 10분)
                               ├─ 사이드바 토큰 갱신 (socket, ttl 15초)
                               ├─ 상세 화면 다시 그리기
                               ├─ 5초마다: agent 재등록, 맨 아래 위치 확인
                               └─ herdr-sidebar 사이드바가 끼어들면 숨기기 키 전송
```

- host는 feedbag pane 안에서 돕니다. 따로 떨어진 백그라운드 프로세스가 없어서 pane을 닫으면 같이 끝납니다.
- hook은 heartbeat가 10초 안에 갱신됐으면 아무것도 하지 않습니다. 시작 직후 hook이 겹쳐 두 번 실행되지 않도록 `starting` 표시를 둡니다.
- host가 죽으면 토큰 ttl(15초)이 지나 사이드바 숫자가 사라집니다.

## socket

1초마다 보내는 요청(토큰 갱신)과 CLI가 없는 요청(`workspace.move`)은 프로세스를 띄우지 않고 socket으로 직접 보냅니다.

- Linux/macOS: Unix domain socket
- Windows: 같은 경로 이름의 named pipe (`\\.\pipe\C:\...\herdr.sock`). 이름에 `:`가 있어 `open()`으로는 열 수 없어서 `CreateFileW`를 씁니다.

## herdr-dock 공용 규칙

다른 플러그인도 하단 고정 블록을 두려면 같은 규칙을 따르면 됩니다.

1. label이 `herdr-dock`인 workspace를 찾습니다. 없으면 `workspace create --label herdr-dock --no-focus`로 만듭니다.
2. 그 안에서 label·token·agent가 없는 빈 pane이 있으면 쓰고, 없으면 dock 안에서 자리를 골라 `pane split`으로 나눠 자기 pane을 만듭니다. 자리는 왼쪽 위, 오른쪽 위, 왼쪽 아래, 오른쪽 아래 순서이고, 이미 있는 pane 옆이나 아래에 나눕니다(`grid_split`). 다른 블록의 pane이나 herdr-sidebar pane은 건드리지 않습니다.
3. 그 pane을 가짜 agent로 등록하고 토큰을 붙입니다. dock을 맨 뒤로 옮기는 일은 누가 해도 결과가 같습니다.
4. 끝낼 때는 자기 pane만 닫고, dock에 herdr-sidebar 말고 남은 pane이 없을 때만 workspace를 닫습니다.

0.1.0이 쓰던 `feedbag` workspace가 남아 있으면 이름을 `herdr-dock`으로 바꿔 이어 씁니다.

## 새 서비스 추가

서비스 하나는 `fb_<이름>` 토큰 한 줄입니다. 예를 들어 `foo`를 추가하려면:

1. `src/providers.py`
   - `fetch_foo()`: 로그인 정보를 **읽기만** 해서 사용량을 조회하고 `Usage("foo", windows)`를 돌려줍니다. 실패하면 예외 대신 `Usage("foo", error=...)`를 돌려줍니다(오류 코드는 `Usage` 주석 참고, HTTP 오류는 `_http_error`).
   - `parse_foo(data)`: 응답 → `Window(key, label, used_pct, resets_at)` 목록. 첫 창이 사이드바 막대, 두 번째 창이 막대 뒤 숫자가 됩니다. `used_pct`는 **사용한** 비율(0~100)입니다.
   - `ALL_PROVIDERS`, `fetch()`에 이름을 넣습니다. 기본으로 켤지(`enabled_providers`)도 정합니다.
2. `src/feedbag.py`: `FETCH_SECONDS`에 조회 주기.
3. `src/render.py`: `SHORT_NAMES`(사이드바용 세 글자), `TITLES`(상세 화면 제목).
4. `src/locales/*.json` 7개: 새 창 key가 있으면 `window.<key>`.
5. `tests/test_providers.py`: `parse_foo` 테스트.
6. 문서: `docs/usage*.md`의 사이드바 줄 예시, 표시 내용, 로그인 정보 표.

사용자는 config `config.toml`에 `$fb_foo` 줄을 넣고 `config.json`의 `providers`로 켜고 끕니다.

## 상태 파일

`HERDR_PLUGIN_STATE_DIR` 아래에 둡니다.

| 파일 | 내용 |
| --- | --- |
| `workspace.id`, `pane.id` | herdr-dock workspace와 host pane |
| `heartbeat` | host 생존 확인 시각 |
| `starting` | ensure 중복 실행 방지 |
| `refresh`, `stop` | 액션 → host 신호. 서비스 선택 화면도 저장 후 `refresh`를 남겨 목록을 다시 읽게 함 |

## 파일

| 파일 | 역할 |
| --- | --- |
| `src/feedbag.py` | 명령(ensure, host, refresh, stop, services, rows)와 host 루프 |
| `src/herdr_api.py` | herdr CLI, socket(Unix socket / named pipe) |
| `src/providers.py` | Claude, Copilot, Codex, Gemini 사용량 조회, 로그인 정보 읽기, 켤 서비스 목록 |
| `src/render.py` | 사이드바 토큰, 애니메이션 막대, 상세 화면 (herdr 호출 없는 순수 함수) |
| `src/services.py` | 서비스 선택 화면 (overlay pane, `config.json`의 `providers` 저장) |
| `src/rows.py` | herdr `config.toml`에 빠진 `$fb_*` 줄 검사 (읽기만 함) |
