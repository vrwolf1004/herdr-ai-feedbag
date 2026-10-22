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
