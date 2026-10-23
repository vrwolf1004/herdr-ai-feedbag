# 문제 해결

먼저 `herdr-dock` workspace의 feedbag pane을 열어 보세요. 서비스별 오류가 그대로 보입니다.

## 사이드바에 블록이 안 보인다

1. `config.toml`에 `$fb_claude`, `$fb_copilot`(쓰는 경우 `$fb_codex`, `$fb_gemini`) 줄이 있는지 확인하고 `herdr server reload-config`를 실행합니다. ([사용법 2장](usage.ko.md#2-사이드바-줄-추가))
2. Spaces 목록에 `herdr-dock` workspace가 있는지 확인합니다. 없으면 `start` 액션을 실행합니다.
3. 플러그인 로그를 봅니다.

   ```sh
   herdr plugin log list --plugin herdr-ai-feedbag
   ```

## 블록이 맨 아래에 있지 않다

`ui.agent_panel_sort`가 `"priority"`면 상태 순으로 정렬되어 고정되지 않습니다. 기본값 `"spaces"`로 두세요. 새 workspace가 생기면 5초 안에 다시 맨 아래로 옮겨집니다.

## `not logged in` / `login expired`

- Claude: Claude Code를 한 번 실행하면 토큰이 갱신됩니다. `~/.claude/.credentials.json`이 있는지 확인하세요.
- Codex: `codex login`으로 ChatGPT 계정에 로그인합니다. API 키 로그인은 한도 정보가 없습니다.
- Gemini: 토큰이 만료되면 refresh token으로 메모리에서 새로 받습니다. 그래도 `login expired`면 Gemini CLI 설치본에서 OAuth client를 찾지 못한 것이니 `gemini`를 한 번 실행하거나 `FEEDBAG_GEMINI_CLIENT_ID`, `FEEDBAG_GEMINI_CLIENT_SECRET`를 설정하세요.
- Copilot: Copilot CLI에서 `/login` 하거나, `FEEDBAG_COPILOT_TOKEN` 환경 변수나 config 폴더의 `copilot-token` 파일에 토큰을 넣으세요.

  **Windows에서 `copilot-token` 파일을 저장할 때 주의**: PowerShell 5.1의 `Out-File -Encoding utf8`은 파일 앞에 BOM(`﻿`)을 붙여 `network: 'latin-1' codec can't encode character '﻿'` 오류가 납니다. 다음 방법으로 BOM 없이 저장하세요.

  ```powershell
  [System.IO.File]::WriteAllText("$env:APPDATA\herdr\plugins\config\herdr-ai-feedbag\copilot-token", (gh auth token).Trim())
  ```

## `network: ...` 오류

일시적인 네트워크 문제면 숫자가 없을 때는 30초, 있을 때는 다음 주기에 다시 시도합니다. 바로 다시 조회하려면 `refresh` 액션을 실행합니다.

`not logged in`, `login expired`는 일시적인 실패가 아닙니다. 숫자가 없어도 30초마다 다시 보지 않고 일반 주기에 맞춰 확인합니다. 로그인을 고친 뒤에는 `refresh` 액션을 실행하세요.

## `unexpected error`

예상하지 못한 오류가 나면 화면에 `unexpected error`(한국어 화면은 `예상하지 못한 오류`)만 보입니다. 원인 이름은 화면에 나오지 않으며, `refresh` 액션으로 다시 조회할 수 있습니다.

## `rate limited`

조회 주기를 3배로 늘려 자동으로 물러섭니다. 그대로 두면 됩니다.

## feedbag pane을 실수로 닫았다 / Ctrl+C로 멈췄다

herdr 명령 팔레트에서 "feedbag: show usage block"을 실행하거나, workspace를 하나 만들면 자동으로 다시 뜹니다. `start`는 heartbeat와 함께 pane의 실제 존재도 확인하므로, pane을 닫은 직후처럼 heartbeat가 아직 남아 있어도 다시 엽니다. host가 멈추면 사이드바 숫자는 15초 뒤 사라집니다.

터미널에서는 액션 id를 먼저 쓰고 플러그인을 `--plugin`으로 지정합니다.

```sh
herdr plugin action invoke start-windows --plugin herdr-ai-feedbag   # windows
herdr plugin action invoke start --plugin herdr-ai-feedbag           # linux / macos
```

`herdr plugin action invoke herdr-ai-feedbag start-windows`처럼 플러그인 id를 앞에 쓰면 `unknown option` 오류가 납니다. 셸에 `start`만 치면 PowerShell의 `Start-Process`가 실행됩니다.

## Copilot 숫자가 이상하다

Copilot 사용량은 GitHub 내부 엔드포인트(`copilot_internal/user`)에서 가져옵니다. GitHub가 형식을 바꾸면 `no quota data`가 나올 수 있습니다. 이슈로 알려 주세요.
