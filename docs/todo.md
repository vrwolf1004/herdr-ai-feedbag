# TODO

개선할 점 목록입니다. 위에 있을수록 먼저 할 일입니다.

## 확인 필요

- [ ] **Codex, Gemini 실제 조회 확인**
  - 개발 PC에 두 CLI가 없어서, 공개된 응답 형식으로 만든 가짜 데이터로만 테스트했습니다.
  - 확인할 것
    - Codex 응답 필드: `rate_limit.primary_window.used_percent`, `reset_at`(초), `reset_after_seconds`
    - Codex 헤더 `ChatGPT-Account-Id`가 필요한지
    - Gemini 응답의 `buckets[].remainingFraction`, `resetTime`, `modelId`
    - Gemini `loadCodeAssist`에서 project 를 가져오는 방식
  - 응답이 다르면 `parse_codex`, `parse_gemini`와 테스트를 고칩니다.

## 기능

- [x] **서비스 선택 화면**: `services` 액션 → overlay pane 체크 목록, 로그인 상태 표시, Enter 로 `config.json` 저장 후 바로 반영. 빠진 사이드바 줄은 보여 주기만 합니다.
- [x] **서비스 목록 다시 읽기**: `config.json` 변경 시각이나 `refresh` 신호를 보고 host 가 1초 안에 다시 읽습니다.
- [x] **사이드바 줄 안내 액션**: `rows` 액션이 빠진 `$fb_*` 줄을 출력합니다. `config.toml`은 고치지 않습니다.
- [x] **Gemini 토큰 만료 대응**: refresh token 으로 메모리에서만 새로 받습니다. client id/secret 은 Gemini CLI 설치본이나 환경 변수에서 읽습니다.
- [x] **Copilot 계정 선택**: `config.json`의 `copilot_account`.
- [ ] **서비스를 끈 직후 줄 정리**: 끈 서비스 토큰이 ttl(15초) 동안 남습니다. 바로 지우려면 토큰 clear 를 보냅니다.
- [ ] **Gemini client 탐색 확인**: 설치본에서 `OAUTH_CLIENT_ID`/`SECRET`을 찾는 경로를 실제 설치본으로 확인하지 못했습니다(개발 PC에 Gemini CLI 없음).
- [ ] **Linux Copilot 계정 선택**: `secret-tool`의 `username` 속성 이름이 맞는지 확인하지 못했습니다.

## 안정성

- [ ] **제공자 오류 격리 및 상태 파일 원자적 기록**
  - `Host.fetch_due()`의 제공자 호출에서 예상하지 못한 응답 형식 오류가 host 루프까지 전파될 수 있다. 제공자별 실패를 기록하고 직전 값을 유지하는 테스트를 추가한다.
  - heartbeat 및 refresh 상태 파일은 바로 덮어쓰므로 중단 시 부분 JSON이 남을 수 있다. 임시 파일에 기록한 뒤 원자적으로 교체하고 복구 동작을 검증한다.
- [ ] **조회를 별도 스레드로**
  - 지금은 1초 루프 안에서 HTTP 조회를 바로 합니다. 타임아웃이 10초이고 Gemini는 요청을 두 번 보냅니다.
  - 네트워크가 느리면 그동안 애니메이션과 heartbeat 가 멈춥니다. 최악이면 토큰 ttl(15초)이 지나 사이드바 줄이 잠깐 사라집니다.
  - 조회를 스레드로 돌리고 루프는 결과만 읽게 바꿉니다.
- [ ] **dock pane 재사용**: 이전 pane 에 ttl 이 남은 토큰이 있으면 빈 pane 으로 보지 않아서, 재사용하지 않고 새로 split 합니다. 토큰 source 가 자기 것이면 재사용하도록 `pick_pane`을 보완합니다.
- [ ] **host 로직 테스트**: `pick_pane`, `find_workspace`, `fetch_due`(실패 시 이전 숫자 유지, 재시도 간격)에 테스트가 없습니다.

## 공용 dock (herdr-dock)

- [ ] **dock 규칙 정리**: dock 을 찾고 만들고 맨 아래로 옮기는 코드를 feedbag 과 stockpulse 가 각자 갖고 있습니다. 규칙 문서(`architecture.md`의 "herdr-dock 공용 규칙")를 기준으로 맞추고, 다른 플러그인이 참고할 짧은 예제를 둡니다.
- [ ] **feedbag 이 없을 때 순서**: dock 을 맨 아래로 옮기는 일은 feedbag host 만 합니다. 다른 블록만 있을 때도 아래에 있게 하려면 각 플러그인이 같은 일을 해야 합니다.

## 문서, 배포

- [ ] **버전**: Codex, Gemini 추가 후에도 0.3.0 입니다. 0.4.0 으로 올립니다.
- [ ] **README 미리보기**: 블록 예시에 Claude, Copilot 만 있습니다. Codex, Gemini 줄을 넣습니다.
- [ ] **GitHub 저장소 설정**: 웹에서 topic `herdr-plugin`과 설명을 넣습니다 (gh CLI 미설치).
- [ ] **줄바꿈 경고**: 커밋마다 `LF will be replaced by CRLF` 경고가 납니다. `.gitattributes`(`* text=auto eol=lf`)를 추가합니다.
