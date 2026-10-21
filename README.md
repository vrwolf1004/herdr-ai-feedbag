# herdr-ai-feedbag

[**English**](README.md) | [한국어](README.ko.md)

UI languages: English · Korean · Russian · French · Spanish · German · Japanese

Show usage for Claude Code, GitHub Copilot, OpenAI Codex, and Gemini CLI once in a shared block at the bottom of herdr's Agents sidebar.

## Dashboard design

Agents sidebar:

```text
 ● claude   work · 1
 ● copilot  work · 1
 ○ feedbag
   ! cld ███▒▓█►░ 81% wk 24%
   ● cop ▒▓►░░░░░ 30% rst 11/01
    ● cdx ██►░░░░░ 25% wk 33%
    ● gem ███►░░░░ 37% fl 12%
```

Dashboard (`feedbag` pane):

```text
╭──────────────────────────────────────────────╮
│           🐺  herdr-ai-feedbag  🌕           │
├──────────────────────────────────────────────┤
│  Claude Code                                 │
│    5h      ▓█████►░  81%  resets 10/15 13:59 │
│    week    ▓█►░░░░░  24%  resets 10/19 01:59 │
│                                              │
│  GitHub Copilot                              │
│    premium ▓█►░░░░░  30%  resets 11/01 09:00 │
│    chat    unlimited                         │
│    inline  unlimited                         │
│                                              │
│  OpenAI Codex                                │
│    5h      ██►░░░░░  25%  resets 10/16 13:59 │
│    week    ▓▓►░░░░░  33%  resets 10/19 01:59 │
│                                              │
│  Gemini CLI                                  │
│    Pro     ███►░░░░  37%  resets 10/22 09:00 │
│    Flash   ▓►░░░░░░  12%  resets 10/22 09:00 │
├──────────────────────────────────────────────┤
│  updated 13:23:25   [Ctrl+C] stop            │
╰──────────────────────────────────────────────╯
```

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
