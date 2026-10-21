# herdr-ai-feedbag

[English](README.md) | [**한국어**](README.ko.md)

🌐 UI 언어: 🇺🇸 English (en) · 🇰🇷 한국어 (ko) · 🇷🇺 Русский (ru) · 🇫🇷 Français (fr) · 🇪🇸 Español (es) · 🇩🇪 Deutsch (de) · 🇯🇵 日本語 (ja)

Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI 사용량을 herdr Agents 사이드바 맨 아래 공용 블록에 한 번만 보여 줍니다.

## 대시보드 디자인

사이드바에서 서비스별 사용량을 간단히 확인하고, `feedbag` pane에서 한도와 초기화 시각을 자세히 볼 수 있습니다. 표시할 서비스와 사이드바 줄은 herdr `config.toml`에서 설정합니다.

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
