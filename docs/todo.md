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
- [x] **서비스를 끈 직후 줄 정리**: 끈 서비스의 `fb_*` 토큰을 `pane report-metadata --clear-token`으로 바로 지웁니다. 명령 인자 순서(pane ID 먼저)는 실제 herdr 로 확인했습니다.
- [ ] **Gemini client 탐색 확인**: 설치본에서 `OAUTH_CLIENT_ID`/`SECRET`을 찾는 경로를 실제 설치본으로 확인하지 못했습니다(개발 PC에 Gemini CLI 없음).
- [ ] **Linux Copilot 계정 선택**: `secret-tool`의 `username` 속성 이름이 맞는지 확인하지 못했습니다.

## 안정성

- [x] **제공자 오류 격리 및 상태 파일 원자적 기록** (`tests/test_host.py`로 검증)
  - `Host.fetch_due()`의 제공자 호출에서 예상하지 못한 응답 형식 오류가 host 루프까지 전파될 수 있다. 제공자별 실패를 기록하고 직전 값을 유지하는 테스트를 추가한다.
  - heartbeat 및 refresh 상태 파일은 바로 덮어쓰므로 중단 시 부분 JSON이 남을 수 있다. 임시 파일에 기록한 뒤 원자적으로 교체하고 복구 동작을 검증한다.
- [x] **조회를 별도 스레드로** (`fetch_forever` 워커가 조회하고, 루프는 결과만 읽습니다)
  - 지금은 1초 루프 안에서 HTTP 조회를 바로 합니다. 타임아웃이 10초이고 Gemini는 요청을 두 번 보냅니다.
  - 네트워크가 느리면 그동안 애니메이션과 heartbeat 가 멈춥니다. 최악이면 토큰 ttl(15초)이 지나 사이드바 줄이 잠깐 사라집니다.
  - 조회를 스레드로 돌리고 루프는 결과만 읽게 바꿉니다.
- [x] **dock pane 재사용**: 자기(`fb_*`) 토큰만 남은 pane 은 빈 pane 으로 봅니다 (`foreign_tokens`).
- [x] **host 로직 테스트**: `tests/test_host.py`에 재시도 간격, 오류 격리, 끈 서비스 토큰 지우기 테스트를 넣었습니다. `pick_pane`, `find_workspace` 는 공용 모듈로 대체하고 지웠습니다(0.5.6).

## 공용 dock (herdr-dock)

- [x] **dock 규칙 정리**: 자리 배정과 정리는 `herdr-dock-grid` 공용 모듈이 맡습니다(`architecture.md`의 "herdr-dock 공용 규칙"). 다른 플러그인이 참고할 짧은 예제는 그 문서에 있습니다.
- [x] **feedbag 이 없을 때 순서**: radio, timekit, simple-git 도 `keep_at_bottom`을 호출합니다. stockpulse 는 아직 호출하지 않습니다 (확인 필요, 별도 작업).
- [x] **블록이 줄었을 때 소개 칸**: 블록을 끄면(`cmd_stop`) 자기 pane을 닫은 뒤 빈 칸에 소개를 띄웁니다. simple-git 에서 실제로 확인했습니다.
- [ ] **2x2 배치 공용화**: radio, feedbag, timekit, simple-git, stockpulse 가 같은 `grid_split` 과 `ensure_intro` 를 각자 갖고 있습니다. 한 규칙으로 맞추고 중복을 줄입니다. 칸 규칙은 1개는 전체, 2개는 좌우, 3개는 좌상·우상·좌하, 4개는 2x2 입니다.
- [x] **소개 칸 문구 관리**: 기준 파일은 herdr-stockpulse `src/intro.py`이고, `tools/sync_dock_intro.py`로 복사하거나 `--check`로 같은지 확인합니다.

## 문서, 배포

- [x] **버전**: 현재 0.5.1 입니다. 다음 기능 릴리스 때 올립니다.
- [ ] **README 미리보기**: 블록 예시에 Claude, Copilot 만 있습니다. Codex, Gemini 줄을 넣습니다.
- [x] **GitHub 저장소 설정**: topic `herdr-plugin`과 설명이 이미 있는 것을 GitHub API로 확인했습니다 (gh CLI 없이 확인).
- [x] **줄바꿈 경고**: `.gitattributes`(`* text=auto eol=lf`)를 추가했습니다. 기존 CRLF 작업 파일은 다음 체크아웃부터 LF 로 바뀝니다.

## 실행 확인에서 찾은 개선점 (2026-10-21)

- [x] **ensure 가 heartbeat 만 보고 일찍 끝남** (pane 존재 확인 추가. `PaneAliveTest`) (`cmd_ensure`): radio 와 같은 문제다. pane 존재 확인을 추가한다.
- [ ] **starting 표식이 남으면 시작이 막힘**: 프로세스가 죽은 뒤 표식이 남으면 수동으로 지워야 했다. 표식에 pid 를 같이 적거나 host 가 살아 있는지 함께 본다.
- [ ] **끈 뒤 소개 칸 생성 확인 필요**: `cmd_stop` 에 소개 칸 확인을 넣었지만 feedbag 에서는 실행으로 확인하지 않았다 (simple-git 에서만 확인).
