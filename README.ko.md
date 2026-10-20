# herdr-ai-feedbag

[English](README.md) | **한국어**

Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI 사용량을 herdr Agents 사이드바 맨 아래에 **한 번만** 보여 주는 플러그인입니다. agent 행마다 같은 숫자가 반복되지 않습니다.

- Windows, Linux, macOS 지원
- Python 3.8 이상, 표준 라이브러리만 사용
- herdr 0.9.0 이상
- `services` 액션으로 보여 줄 서비스를 고를 수 있습니다
- 7개 언어 지원: 영어, 한국어, 러시아어, 프랑스어, 스페인어, 독일어, 일본어

사이드바 블록 (애니메이션, 80% 이상이면 `!`가 깜빡임):

```text
 ● claude   work · 1
 ● copilot  work · 1
 ○ feedbag
   ! cld ███▒▓█►░ 81% wk 24%
   ● cop ▒▓►░░░░░ 30% rst 11/01
```

대시보드 (`feedbag` pane):

```text
╭─────────────────────────────────────────────╮
│          🐺  herdr-ai-feedbag  🌕           │
├─────────────────────────────────────────────┤
│  Claude Code                                │
│    5시간    ▓█████►░  81%  10/15 13:59 리셋 │
│    주간     ▓█►░░░░░  24%  10/19 01:59 리셋 │
│                                             │
│  GitHub Copilot                             │
│    프리미엄 ▓█►░░░░░  30%  11/01 09:00 리셋 │
│    채팅     무제한                          │
│    자동완성 무제한                          │
├─────────────────────────────────────────────┤
│  13:23:25 갱신   [Ctrl+C] 중지              │
╰─────────────────────────────────────────────╯
```

## 설치

```sh
herdr plugin install vrwolf1004/herdr-ai-feedbag
```

설치 후 herdr `config.toml`에 사용량 줄을 추가하세요. [사용법](docs/usage.ko.md#2-사이드바-줄-추가)을 참고하세요.

## 문서

- [설치, 사이드바 설정, 액션, 로그인 정보](docs/usage.ko.md)
- [Usage guide (English)](docs/usage.md)
- [문제 해결](docs/troubleshooting.md)
- [구조 및 동작 방식](docs/architecture.md)
- [개발과 테스트](docs/development.md)
- [할 일](docs/todo.md)

## 개발

```sh
python -m unittest discover -s tests
```

## 라이선스

[MIT](LICENSE)

---

## 프로젝트 응원하기

프로젝트가 도움이 되셨다면 커피 한 잔으로 개발을 응원해 주세요.

[![Ko-fi에서 응원하기](https://img.shields.io/badge/Ko--fi-%EC%9D%91%EC%9B%90%ED%95%98%EA%B8%B0-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
