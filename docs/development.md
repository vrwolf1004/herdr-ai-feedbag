# 개발

코드 구조, 테스트 방법, 문구와 서비스를 추가할 때 함께 고칠 곳을 정리합니다. 동작 방식과 socket, herdr-dock 규칙은 [architecture.md](architecture.md)에 있습니다.

## 파일 구조

```text
herdr-ai-feedbag/
├── README.md, README.ko.md      짧은 소개 (영문, 한글)
├── herdr-plugin.toml            herdr 매니페스트: 시작 훅, 액션, services pane (OS별)
├── LICENSE
├── docs/                        사용법, 문제 해결, 구조, 개발, 할 일
├── src/
│   ├── feedbag.py               명령(ensure, host, refresh, stop, services, rows)과 host 루프
│   ├── herdr_api.py             herdr CLI, socket (Unix socket / named pipe)
│   ├── providers.py             Claude, Copilot, Codex, Gemini 사용량 조회, 로그인 정보 읽기
│   ├── render.py                사이드바 토큰, 애니메이션 막대, 상세 화면 (순수 함수)
│   ├── services.py              서비스 선택 화면 (overlay pane, config.json 저장)
│   ├── rows.py                  config.toml에 빠진 $fb_* 줄 검사 (읽기만 함)
│   ├── i18n.py                  언어 결정과 t(key, **values)
│   └── locales/<언어>.json      화면 문구 (en, ko, ru, fr, es, de, ja)
└── tests/                       unittest 테스트
    ├── support.py               테스트 공용 도구
    ├── test_host.py             host 동작, atomic 상태 쓰기, pane 확인/선택, 조회 주기, 토큰 정리
    ├── test_i18n.py             언어 파일의 키와 자리표시자 검사
    ├── test_providers.py        사용량 응답 파싱
    ├── test_render.py           사이드바 줄 폭과 애니메이션
    └── test_services.py         서비스 선택과 저장
```

## 테스트 실행

플러그인 폴더에서 실행합니다.

```sh
python -m unittest discover -s tests
```

테스트는 표준 라이브러리 `unittest`만 씁니다. 사용량 응답은 실제 서버 대신 가짜 데이터로 파싱을 확인합니다. 실제 Codex와 Gemini 응답은 아직 확인하지 못했습니다([할 일](todo.md) 참고).
`test_host.py`는 원자적 상태 파일 교체와 교체 실패 시 기존 값 보존, 닫힌 pane 감지, 서비스 비활성화 시 토큰 즉시 삭제도 확인합니다. 실제 herdr UI에서 소개 pane과 블록 배치는 별도로 확인해야 합니다.

## 문구를 추가하거나 바꿀 때

1. 모든 언어 파일(`src/locales/*.json`)에 같은 키를 넣습니다. `test_i18n.py`가 키 차이를 잡습니다.
2. 자리표시자는 영문과 같아야 합니다. `test_i18n.py`의 `test_placeholders_match_english`가 확인합니다.
3. 사이드바 줄의 짧은 이름(`cld`, `cop`, `wk`, `rst`)은 언어와 상관없이 고정입니다. 줄 폭이 바뀌지 않게 하기 위해서입니다.

## 새 서비스를 추가할 때

서비스 하나는 `fb_<이름>` 토큰 한 줄입니다. 절차는 [architecture.md](architecture.md)의 "새 서비스 추가"에 있고, 여기서는 체크리스트만 적습니다.

1. `src/providers.py`: `fetch_<이름>()`, `parse_<이름>()`을 추가하고 `ALL_PROVIDERS`, `fetch()`, `enabled_providers`에 넣습니다.
2. `src/feedbag.py`: `FETCH_SECONDS`에 조회 주기를 넣습니다.
3. `src/render.py`: `SHORT_NAMES`(사이드바용 세 글자), `TITLES`(상세 화면 제목)를 넣습니다.
4. `src/locales/*.json` 7개에 새 창 이름 키(`window.<key>`)를 넣습니다.
5. `tests/test_providers.py`에 `parse_<이름>` 테스트를 추가합니다.
6. `docs/usage.md`와 `docs/usage.ko.md`의 사이드바 줄 예시, 표시 내용, 로그인 정보 표를 고칩니다.

## 문서 맞추기

- `usage.md`(영문)와 `usage.ko.md`(한국어)는 같은 내용을 가져야 합니다. 한쪽을 고치면 다른 쪽도 고칩니다.
- 사이드바 줄 예시(`config.toml`)를 바꾸면 `rows` 액션이 찾는 토큰 이름도 맞는지 확인합니다.
- 사용자가 겪는 증상이 바뀌면 [문제 해결](troubleshooting.md)을 고칩니다.

## 커밋 전 확인

- `python -m unittest discover -s tests`가 통과하는지 확인합니다.
- 사이드바나 상세 화면을 바꿨다면 실제 herdr에서 블록이 맞게 그려지는지 봅니다. 줄 폭과 애니메이션은 자동 테스트로 전부 확인되지 않습니다.
