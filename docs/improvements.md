# 개선 문서

- 작성 기준: 2026-10-22, 커밋 `327a8ca` (`git log -1 --format=%h`)
- 공용 도크 모듈: `src/dock_layout.py` 는 복사본. `load_dock_layout()`(`src/feedbag.py:30`)이 설치된 herdr-dock-grid 원본을 먼저 찾고, 없으면 이 복사본을 쓴다. 복사본은 herdr-dock-grid 0.7.1 원본과 내용이 같다(diff 확인).
- 할 일 목록: [todo.md](todo.md). 이미 적힌 항목은 옮기지 않고 거기서 관리한다.
- 표기: "확인됨" = 현재 코드에서 직접 본 내용. "확인 필요" = 코드로 추정만 했고 실행해 보지 않음.

## 개선 항목

- **[중간] 공용 herdr CLI 호출에 시간 제한이 없음** (확인 필요)
  - 근거: `src/herdr_api.py:42`(`cli()`), `src/herdr_api.py:140`(`installed_plugin_path()`)
  - herdr 가 응답하지 않으면 host 루프가 멈출 수 있다. 고칠 때는 herdr-dock-grid 원본을 먼저 바꾸고 복사본을 맞춘다(공용 모듈 규칙).

- **[낮음] `foreign_tokens()` 는 정의만 있고 쓰이지 않는다** (확인됨)
  - 근거: `src/feedbag.py:142-144`. 저장소 안에서 호출하는 곳이 없다.
  - [todo.md](todo.md)(`docs/todo.md:36`)는 "dock pane 재사용"에 이 함수를 쓴다고 적었지만, 실제 재사용은 공용 `ensure_dock_pane` 이 한다. 함수를 지우거나, todo 의 설명을 실제 동작에 맞게 고친다.

- **[낮음] 저장소에 CI가 없음** (확인됨)
  - 근거: 저장소 루트에 `.github/` 가 없다. herdr-stockpulse 의 `.github/workflows/test.yml` 을 참고할 수 있다. 이 저장소는 `tests/` 에 단위 테스트 5개 파일이 있다.

## 관련 기존 항목 (todo.md)

- 2x2 배치 공용화, `ensure_intro` 중복: [todo.md](todo.md) 의 "공용 dock" 절
- 끈 뒤 소개 칸 생성 확인: [todo.md](todo.md) 의 "실행 확인에서 찾은 개선점" 절
- Linux Copilot 계정 선택, Gemini 탐색 확인: [todo.md](todo.md) 의 "확인 필요" 절

## 개선 제안 (2026-10-23)

### 1. 예상하지 못한 오류가 번역 키 이름으로 화면에 나옴

- **현상**: 제공자 조회 중 처리하지 않은 예외가 나면 예외 클래스 이름을 `Usage.error` 에 넣는다(`src/feedbag.py:301-302`). 화면은 `error.<이름>` 키를 찾는다. 등록된 키는 `not_logged_in`, `login_expired`, `rate_limited`, `network`, `http`, `no_quota_data`, `loading` 뿐이다(`src/locales/en.json:13-19`). 없는 키는 키 이름 그대로 나온다(`src/i18n.py:99`). 예: `error.KeyError`. 화면 표시는 `src/render.py:67-68`, `:78`, `:176` 에서 나온다.
- **개선안**: 알 수 없는 예외는 `error.unexpected` 같은 공통 키로 바꾸고, 원래 이름은 `detail` 이나 로그에 남긴다. 모든 언어 파일에 키를 추가한다.
- **범위**: `src/feedbag.py` (조회 루프), `src/render.py` (`error_text`), `src/locales/*.json`
- **확인**: 제공자 조회가 `KeyError` 를 던지도록 가짜 응답을 넣은 뒤 화면 문구를 본다. 실행하지 않았다(확인 필요).
→ 완료: 알 수 없는 오류는 일반 문구로 보인다.

### 2. 사용량 조회 실패 뒤 재시도 간격이 실패 종류와 무관하게 같음 (완료)

- **현상**: 숫자가 없는 실패는 `RETRY_SECONDS`(30초) 뒤에 다시 시도한다(`src/feedbag.py:310-313`). 로그인 만료나 계정 없음처럼 사람이 고쳐야 하는 실패도 같은 30초마다 같은 조회를 보낸다. 이 실패들은 로그인 파일이 바뀌지 않으면 계속 실패한다.
- **개선안**: `not_logged_in` 이나 `login_expired` 는 재시도 간격을 늘리거나, 로그인 파일의 수정 시각이 바뀔 때만 다시 조회한다.
- **범위**: `src/feedbag.py` (재시도 간격 계산), `src/providers.py` (로그인 파일 확인)
- **확인**: 로그인 파일이 없는 상태에서 조회 호출 횟수를 세어 본다. 실행하지 않았다. 이 항목은 의도한 동작인지 먼저 확인한다.


→ 완료: 로그인 필요 실패는 일반 주기로, 일시 실패는 30초로 다시 본다.