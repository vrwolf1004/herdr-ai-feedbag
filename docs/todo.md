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

- [ ] **서비스 선택 화면 (인터랙티브)**
  - `services` 액션을 실행하면 pane에 체크 목록이 나옵니다.
  - 방향키와 스페이스로 켜고 끄면 `config.json`의 `providers`에 저장합니다.
  - 각 서비스 옆에 로그인 상태(있음 / 없음 / 만료)를 보여 줍니다.
  - 저장하면 host 에 바로 반영합니다(아래 "목록 다시 읽기" 필요).
  - herdr `config.toml`의 사이드바 줄은 다른 설정과 섞인 파일이라 자동으로 고치지 않습니다. 문서에는 "네 줄을 모두 넣어 두면 꺼진 서비스 줄은 비어서 안 보인다"고 안내합니다.
- [ ] **서비스 목록 다시 읽기**: 지금은 host 가 시작할 때만 `providers`를 읽습니다. `refresh` 액션이나 `config.json` 변경 시각을 보고 다시 읽게 합니다.
- [ ] **사이드바 줄 안내 액션**: `config.toml`에 `$fb_*` 줄이 빠졌는지 검사하고, 넣을 줄을 출력합니다. 파일은 고치지 않습니다.
- [ ] **Gemini 토큰 만료 대응**: 토큰이 1시간이면 만료되어 `gemini`를 안 쓰면 "로그인 만료"만 보입니다.
  - 메모리에서만 갱신하고 파일에는 쓰지 않는 방법이 있습니다. 다만 Gemini CLI 설치본에서 client id/secret 을 읽어야 해서 깨지기 쉽습니다.
  - "읽기만 한다" 원칙과도 맞는지 판단이 필요합니다.
- [ ] **Copilot 계정 선택**: 계정이 여러 개면 처음 응답한 토큰을 씁니다. `config.json`에서 계정을 고를 수 있게 합니다.

## 안정성

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
