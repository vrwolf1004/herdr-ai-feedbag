# herdr-ai-feedbag

[**English**](README.md) | [한국어](README.ko.md)

🌐 UI languages: 🇺🇸 English (en) · 🇰🇷 한국어 (ko) · 🇷🇺 Русский (ru) · 🇫🇷 Français (fr) · 🇪🇸 Español (es) · 🇩🇪 Deutsch (de) · 🇯🇵 日本語 (ja)

Show usage for Claude Code, GitHub Copilot, OpenAI Codex, and Gemini CLI once in a shared block at the bottom of herdr's Agents sidebar.

## Dashboard design

The sidebar summarizes each service's usage; the `feedbag` pane shows detailed limits and reset times. Configure displayed services and sidebar rows in herdr's `config.toml`.

## Installation

```sh
herdr plugin install vrwolf1004/herdr-ai-feedbag
```

## Actions

| Action | What it does |
| --- | --- |
| `start` | Show the usage block |
| `refresh` | Refresh usage now |
| `stop` | Hide the usage block |
| `services` | Choose which services to show |
| `rows` | Check the required sidebar rows |

On Windows, append `-windows` to each action ID. Full setup and invocation instructions are in the [usage guide](docs/usage.md).

## Requirements

- Windows, Linux, or macOS
- herdr 0.9.0 or later
- Python 3.8 or later; standard library only

## Documentation

- [Usage and setup (English)](docs/usage.md)
- [사용법 (한국어)](docs/usage.ko.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Architecture](docs/architecture.md)
- [Development and tests](docs/development.md)
- [TODO](docs/todo.md)

## Development

```sh
python -m unittest discover -s tests
```

## License

[MIT](LICENSE)

## Support the project

If this project is useful to you, consider buying the developer a coffee.

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
