# herdr-ai-feedbag

[**English**](README.md) | [한국어](README.ko.md)

One feedbag for your herd: Claude Code and GitHub Copilot plan usage, shown **once** at the bottom of the herdr Agents sidebar instead of on every agent row.

- Windows, Linux, and macOS
- Python 3.8+; standard library only
- herdr 0.9.0+

Sidebar block (animated; `!` blinks at 80% or more):

```text
 ● claude   work · 1
 ● copilot  work · 1
 ○ feedbag
   ! cld ███▒▓█►░ 81% wk 24%
   ● cop ▒▓►░░░░░ 30% rst 11/01
```

Dashboard (the `feedbag` pane):

```text
 feedbag  AI usage for your herd

 Claude Code
   5h      ███▒▓█►░  81%  resets 10/15 13:59
   wk      ▓█►░░░░░  24%  resets 10/19 01:59

 GitHub Copilot
   premium ▒▓►░░░░░  30%  resets 11/01 09:00
   chat    unlimited
   inline  unlimited

 updated 13:23:25 · Ctrl+C to stop
```

## Install

```sh
herdr plugin install vrwolf1004/herdr-ai-feedbag
```

Then add the usage rows to herdr's `config.toml` — see the [usage guide](docs/usage.md#2-sidebar-rows).

## Documentation

- [Installation, sidebar rows, actions, and credentials](docs/usage.md)

Additional guides (Korean):

- [사용법](docs/usage.ko.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Architecture](docs/architecture.md)

## Development

```sh
python -m unittest discover -s tests
```

## License

[MIT](LICENSE)

---

## Support the project

If this project is useful to you, consider buying the developer a coffee.

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
