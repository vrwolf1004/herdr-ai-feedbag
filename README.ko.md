# herdr-ai-feedbag

[English](README.md) | [**한국어**](README.ko.md)

지원 언어: 영어 · 한국어 · 러시아어 · 프랑스어 · 스페인어 · 독일어 · 일본어

Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI 사용량을 herdr Agents 사이드바 맨 아래 공용 블록에 한 번만 보여 줍니다.

## 대시보드 디자인

Agents 사이드바:

```text
 ● claude   work · 1
 ● copilot  work · 1
 ○ feedbag
   ! cld ███▒▓█►░ 81% wk 24%
   ● cop ▒▓►░░░░░ 30% rst 11/01
   ● cdx ██►░░░░░ 25% wk 33%
   ● gem ███►░░░░ 37% fl 12%
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
│                                             │
│  OpenAI Codex                               │
│    5시간    ██►░░░░░  25%  10/16 13:59 리셋 │
│    주간     ▓▓►░░░░░  33%  10/19 01:59 리셋 │
│                                             │
│  Gemini CLI                                 │
│    Pro      ███►░░░░  37%  10/22 09:00 리셋 │
│    Flash    ▓►░░░░░░  12%  10/22 09:00 리셋 │
├─────────────────────────────────────────────┤
│  13:23:25 갱신   [Ctrl+C] 중지              │
╰─────────────────────────────────────────────╯
```

공용 dock에 블록이 세 개 있고 빈 칸이 없으면 네 번째 칸에 소개 pane이 생기며, 다른 블록이 그 칸을 쓰면 자리를 내줍니다.

## 설치

```sh
herdr plugin install vrwolf1004/herdr-ai-feedbag
```

## 액션

| 액션 | 기능 |
| --- | --- |
| `start` | 사용량 블록 표시 |
| `refresh` | 사용량 즉시 갱신 |
| `stop` | 사용량 블록 숨기기 |
| `services` | 표시할 서비스 선택 |
| `rows` | 필요한 사이드바 줄 확인 |

Windows에서는 각 액션 ID 뒤에 `-windows`를 붙입니다. 자세한 설정과 실행 방법은 [사용법](docs/usage.ko.md)을 참고하세요.
`start`는 host heartbeat뿐 아니라 feedbag pane의 실제 존재 여부도 확인하므로 pane을 닫았으면 블록을 다시 만듭니다.

## 요구 사항

- Windows, Linux, macOS
- herdr 0.9.0 이상
- Python 3.8 이상, 표준 라이브러리만 사용

## 문서

- [사용법 (한국어)](docs/usage.ko.md)
- [Usage and setup (English)](docs/usage.md)
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

## 프로젝트 응원하기

프로젝트가 도움이 되셨다면 커피 한 잔으로 개발을 응원해 주세요.

[![Ko-fi에서 응원하기](https://img.shields.io/badge/Ko--fi-%EC%9D%91%EC%9B%90%ED%95%98%EA%B8%B0-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
