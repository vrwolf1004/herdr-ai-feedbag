# Usage

## 1. Install

### Install from GitHub

```sh
herdr plugin install vrwolf1004/herdr-ai-feedbag
```

### Link a local folder (development)

```sh
git clone https://github.com/vrwolf1004/herdr-ai-feedbag.git
herdr plugin link ./herdr-ai-feedbag
```

### Manage the plugin

```sh
herdr plugin list
herdr plugin update herdr-ai-feedbag
herdr plugin uninstall herdr-ai-feedbag
```

## 2. Sidebar rows

herdr only renders custom tokens that appear in your sidebar layout. Add these rows to `[ui.sidebar.agents]` in herdr's `config.toml`, then run `herdr server reload-config`:

```toml
[ui.sidebar.agents]
rows = [
  ["state_icon", "machine", { token = "workspace", rules = [{ equals = "herdr-dock", hide = true }] }, "tab"],
  ["agent"],
  [{ token = "$fb_claude", fg = "#d97757", rules = [{ starts_with = "!", fg = "#ff5f5f", bold = true }] }],
  [{ token = "$fb_copilot", fg = "#a371f7", rules = [{ starts_with = "!", fg = "#ff5f5f", bold = true }] }],
  [{ token = "$fb_codex", fg = "#10a37f", rules = [{ starts_with = "!", fg = "#ff5f5f", bold = true }] }],
  [{ token = "$fb_gemini", fg = "#4285f4", rules = [{ starts_with = "!", fg = "#ff5f5f", bold = true }] }],
]
```

- Keep only the rows for the services you use, or keep all four: a row whose service is off simply stays empty (see [section 5](#5-choosing-services)). The `rows` action prints any that are missing.
- `$fb_*` tokens are reported only on the feedbag block, so these rows disappear on every other agent.
- The `workspace` rule hides the dock workspace name (`herdr-dock`) on the block's first row.
- The `!` rule turns a line red while it is over the warning threshold. Change the colors as you like.
- Keep `ui.agent_panel_sort` at `"spaces"` (the default). With `"priority"` the block is not pinned to the bottom.

## 3. Actions

The block starts automatically when the herdr server starts and when a workspace is created. To control it by hand:

| Action | Description |
| --- | --- |
| `start` | Create the block if missing and start the host |
| `refresh` | Fetch usage now |
| `stop` | Stop the host and close the feedbag pane (and the dock workspace if nothing else is in it) |
| `services` | Open the service picker ([section 5](#5-choosing-services)) |
| `rows` | Print the `$fb_*` sidebar rows missing from herdr's `config.toml` (see `herdr plugin log list --plugin herdr-ai-feedbag`). The file is never edited |

On Windows the action ids end with `-windows`:

```sh
herdr plugin action invoke start-windows --plugin herdr-ai-feedbag   # windows
herdr plugin action invoke start --plugin herdr-ai-feedbag           # linux / macos
```

If you closed the feedbag pane with Ctrl+C, run "feedbag: show usage block" from the herdr command palette, run the command above, or create any workspace to bring it back. Typing just `start` in a shell does not work (in PowerShell it is `Start-Process`).

Bind one to a key if you use it often:

```toml
[[keys.command]]
key = "prefix+u"
type = "plugin_action"
command = "herdr-ai-feedbag.refresh-windows"
description = "refresh AI usage"
```

## 4. What is shown

| Line | Bar | After the bar |
| --- | --- | --- |
| `cld` | Claude 5-hour session window | `wk` = 7-day window |
| `cop` | Copilot monthly premium requests | `rst` = reset date |
| `cdx` | Codex 5-hour window (ChatGPT login) | `wk` = weekly window |
| `gem` | Gemini CLI daily Pro model quota | `fl` = Flash models |

- The bar is the **used** share. A shine runs through the filled part, one cell every 2 seconds.
- At 80% or more in any window, the leading `●` becomes a blinking `!`. The mark is always one cell wide, so the line never shifts.
- Only classic box-drawing characters (`█▓▒░►`) are used, no emoji.
- The `feedbag` pane shows every window with its reset time, including Copilot chat and inline completions.

Refresh intervals: Claude and Codex every 5 minutes, Copilot and Gemini every 10 minutes. When there are no numbers yet, a failed fetch is retried after 30 seconds. Rate limits back off to 3× the interval.

## 5. Choosing services

By default feedbag shows Claude and Copilot always, plus Codex and Gemini when their login file exists (`~/.codex/auth.json`, `~/.gemini/oauth_creds.json`).

### Service picker

Run **feedbag: choose services** from the herdr command palette (or `herdr plugin action invoke services-windows --plugin herdr-ai-feedbag`; `services` on Linux/macOS). An overlay opens:

```text
 feedbag  choose services

 [x] Claude Code      logged in
 [x] GitHub Copilot   logged in
 [ ] OpenAI Codex     not logged in
 [ ] Gemini CLI       not logged in

 ↑↓ move · Space on/off · Enter save · q cancel
```

- Enter saves to `config.json` and the block updates within a second; no restart needed. At least one service must stay on.
- If a chosen service has no `$fb_<name>` row in herdr's `config.toml`, the picker lists the rows to add. It does not edit `config.toml` (it holds your other settings). Tip: add all four rows from [section 2](#2-sidebar-rows) once; rows for services that are off stay empty and invisible.

### By hand

The picker writes `providers` in `config.json` in the plugin config dir. Other keys are kept.

```json
{ "providers": ["claude", "codex", "gemini"], "copilot_account": "octocat" }
```

- `providers`: valid names `claude`, `copilot`, `codex`, `gemini`, in sidebar order. Unknown names are ignored. Changes are picked up within a second.
- `copilot_account`: when Copilot CLI is logged in to several GitHub accounts, use only this one (Windows, macOS; Linux best effort). Without it, the first account that answers is used.

## 6. Credentials

Read-only. Credential files are never rewritten — they belong to your agent sessions. If a login expires, use that CLI once; the next refresh picks up the new token.

| Provider | Source (first match wins) |
| --- | --- |
| Claude Code | `~/.claude/.credentials.json` (`CLAUDE_CONFIG_DIR` respected) |
| GitHub Copilot | `FEEDBAG_COPILOT_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN` → `copilot-token` file in the plugin config dir → Copilot CLI login (Windows Credential Manager, macOS Keychain, Linux `secret-tool`) |
| OpenAI Codex | `$CODEX_HOME/auth.json` or `~/.codex/auth.json` — ChatGPT login only; API-key logins have no plan limits |
| Gemini CLI | `~/.gemini/oauth_creds.json` (Google login). The access token lasts about an hour. When it has expired, feedbag gets a fresh one with the refresh token and keeps it **in memory only** — the file is not touched and Google does not rotate the refresh token, so Gemini CLI stays logged in. This needs Gemini CLI's OAuth client, read from the installed `@google/gemini-cli` package (or `FEEDBAG_GEMINI_CLIENT_ID` / `FEEDBAG_GEMINI_CLIENT_SECRET`); if it cannot be found the line shows `login expired` until you run `gemini` again |

Codex and Gemini numbers come from undocumented endpoints (`chatgpt.com/backend-api/wham/usage`, `cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota`) and may break if the vendors change them.

The plugin config dir is printed by `herdr plugin config-dir herdr-ai-feedbag`.

## 7. Display language

The dashboard and error messages support `en`, `ko`, `ru`, `fr`, `es`, `de`, and `ja`. The language is selected in this order:

1. `HERDR_FEEDBAG_LANG` environment variable
2. `"lang"` in `config.json` in the plugin config dir, e.g. `{"lang": "ko"}`
3. OS language (Windows user-interface language, or `LC_ALL`, `LC_MESSAGES`, then `LANG` on Linux/macOS)
4. English (`en`) if the OS language is unsupported or cannot be detected

The short sidebar labels (`cld`, `cop`, `wk`, `rst`) stay the same in every language so the line width never changes. Missing translations fall back to English.

## 8. Using it with herdr-sidebar

[herdr-sidebar](https://github.com/alexarthurs/herdr-sidebar) docks its explorer into every focused tab, including the `herdr-dock` workspace. feedbag notices it and sends the sidebar's own hide key (`b`) after one second. herdr-sidebar then remembers that tab and stops reopening it.
