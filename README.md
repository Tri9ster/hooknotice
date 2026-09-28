# hooknotice

**English** | [日本語](README.ja.md)

When Claude Code stops to ask for permission or to ask you a question, hooknotice plays a sound and shows a
card-style window with an animated gradient background. It is a Claude Code plugin made of hooks plus two files,
`hook_notify.py` and `notify_window.py`. No resident daemon or inter-process communication is needed.
The detailed specification, technical notes, the development log, and the record of failures for developers are in
[docs/](docs/README.md) (in Japanese).

## Features

- When Claude Code is waiting for permission or an answer, and when it finishes working, a sound plays and a card
  with an animated gradient background appears at the bottom right of the screen.
- The body shows **what Claude Code is asking**, without truncation.
  - For permission to run a command, the description Claude wrote is shown on top, and the full command is shown
    below in a monospaced font (only the command if there is no description).
  - Long one-liners are split into lines at `;` and `&&`, and environment variable prefixes and pipes are put on
    their own lines. Only whitespace and line breaks change, so the meaning of the command stays the same
    (anything that cannot be parsed is shown as is).
  - Other permission requests show the tool name and target, such as `Edit: <file path>`. Questions show the
    notification message.
  - When Claude finishes ("Claude Code: Done"), Claude's last response is formatted and shown ("Claude has
    finished." if there is no response text). It appears right after each response.
- The text is available in **English and Japanese**. By default it follows the OS language (see "Language" below).
- The colors follow the macOS appearance setting (light / dark), including changes while a card is shown.
- The card grows to fit its content. Commands too long for the screen can be scrolled with the mouse wheel.
- **Permission notifications have "Cancel" and "OK" buttons, so you can answer right there.**
  - **OK**: returns "allow" to Claude Code, and the tool runs.
  - **Cancel**: returns "deny". Claude is told that you denied it and continues working.
  - **✕**: closes without deciding. Answer in the terminal's permission dialog as usual.
  - Notifications with buttons do not close when you click the body (anywhere other than the buttons), so a
    misclick does not lose your answer.
  - The terminal's permission dialog is shown at the same time, so you can answer in either place.
  - Operations that match a `deny` rule in settings are not allowed even if you press OK.
  - When no permission check happens, such as in auto mode, no notification appears either.
  - For plan approval (ExitPlanMode), four buttons appear instead of OK / Cancel: "Keep planning",
    "Approve, ask each time", "Approve, auto-accept edits", and "Approve in auto mode". Each approve button
    also switches the permission mode to default / acceptEdits / auto. To give feedback on the plan in writing,
    close with ✕ and answer in the terminal.
  - For multiple-choice questions (AskUserQuestion), the questions and options (with previews) are formatted in
    the body, with a button for each option below. After choosing an answer for every question, press
    "Submit" to continue with those answers (questions that allow several answers let you turn on several).
    To answer in free text, close with ✕ and answer in the terminal. If a question has no options, the
    notification has no buttons, and clicking it brings VS Code (or your terminal) to the front.
- Press the **"Explain" button** and Claude writes an explanation of the operation it is asking to run (command,
  edit, and so on), shown inside the notification. It takes about 10–15 seconds and uses your Claude usage each
  time. After reading it, you can answer with OK / Cancel right away. The explanation is written in the
  display language.
- Notifications appear **only after being left for about 6 seconds** (change the delay in the settings window;
  0 shows them at once). Choose "From text length" in the settings window to wait longer for longer plans and
  responses (set the reading speed in characters per minute).
  - For permission, multiple-choice questions, and plan approval, no notification appears if you answer in the
    terminal (VS Code) during the delay. If you leave it, a notification with buttons appears after about
    6 seconds, and you can answer there.
  - For "Done" and similar notifications, no notification appears if you send the next prompt during the delay.
    If you only look at the screen without doing anything, it appears.
  - Notifications that Claude Code itself shows after waiting (permission dialog left open, idle after a
    response, MCP input form / URL) are shown at once, without the extra delay.
- The window **does not close by itself until you press the close button or click it** (permission
  notifications close automatically when you answer in the terminal first, or when the hook times out after
  600 seconds).
- Clicking it shrinks it slightly and then closes it. If you click anywhere other than the close button, the app
  that triggered it (the terminal or VS Code running Claude Code) is also brought to the front.
- When several notifications appear at once, they **stack vertically instead of overlapping**. When you close
  one in the middle, the ones above move down (the newest always appears at the bottom right).
- Supported OS: **macOS**. **Windows support code is included but has not been tested on a real machine** (see
  "Using on Windows" below). `hook_notify.py` uses only the standard library, and `notify_window.py` uses
  PySide6 (Qt) managed with [uv](https://docs.astral.sh/uv/). OS differences are collected in
  `platform_support.py`.

## Setup

Requirements: macOS, `python3` (the one bundled with macOS is fine), and [uv](https://docs.astral.sh/uv/)
(recommended; pip also works, see below).

In Claude Code, add the marketplace and install the plugin:

```
/plugin marketplace add Tri9ster/hooknotice
/plugin install hooknotice@hooknotice
```

(From a shell: `claude plugin marketplace add Tri9ster/hooknotice` and `claude plugin install hooknotice@hooknotice`.)
Then restart Claude Code (in VS Code, reload the window). The hooks are registered by the plugin, so hooknotice is
enabled for all projects, and you do not need to edit `settings.json`.

**First start: the setup dialog.** The notification window needs PySide6 (Qt for Python). hooknotice never
downloads it on its own. When you start Claude Code for the first time after installing, a "hooknotice setup"
dialog asks whether it may run `uv sync --frozen` (the same happens when a plugin update changes
`pyproject.toml` / `uv.lock`).

- **Run**: runs `uv sync --frozen` right away and shows the result when it finishes. Notifications appear from the
  next one.
- **Not now**: does nothing. It asks again the next time you start Claude Code.
- **Don't ask again**: never shows this dialog again (to undo, delete `setup.declined` in the state folder).

The environment (`venv`) is created in the plugin's data folder, `~/.claude/plugins/data/hooknotice-hooknotice/venv`,
which is kept across plugin updates. No notifications are shown until the setup is done.

If uv is not found, the dialog shows how to install uv, and how to set up with pip instead ("Copy steps" copies
them to the clipboard):

- **Install uv (recommended)**: run `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `brew install uv`,
  `pip3 install uv`), then restart Claude Code and choose "Run".
- **Install with pip instead of uv**:

  ```bash
  python3 -m venv ~/.claude/plugins/data/hooknotice-hooknotice/venv
  ~/.claude/plugins/data/hooknotice-hooknotice/venv/bin/pip install "PySide6-Essentials>=6.7"
  ```

  With Python 3.10 or later you get the latest version. With the Python 3.9 bundled with macOS you get a version
  that supports 3.9 (the 6.10 series).

### Updating and uninstalling

- **Update**: open `/plugin`, and update hooknotice from the "Installed" tab (or run
  `claude plugin update hooknotice@hooknotice`), then restart Claude Code.
- **Uninstall**: `/plugin uninstall hooknotice@hooknotice` (or `claude plugin uninstall hooknotice@hooknotice`).
  This also deletes the data folder (`venv` and `config.json`). The state folder
  (`~/Library/Application Support/hooknotice/`) is left; delete it yourself if you like.

### Using on Windows (untested)

The Windows support code is included but has not been tested on a real machine.

1. Install [uv](https://docs.astral.sh/uv/) (in PowerShell:
   `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`), and choose "Run" in the
   setup dialog (this creates `venv\Scripts\python.exe` in the data folder,
   `%USERPROFILE%\.claude\plugins\data\hooknotice-hooknotice`).
   The setup dialog is a standard Windows message box (the buttons are mapped to "Yes / No / Cancel").
2. The plugin's hooks run `python3`. Claude Code runs hooks with Git Bash on Windows, but many environments have no
   `python3`. If notifications do not appear, check that `python3` works in Git Bash.
3. Differences from macOS:
   - System sounds are chosen from the WAV files in `%SystemRoot%\Media` (usually `C:\Windows\Media`). Custom
     sound files must also be WAV.
   - Clicking the body does not bring the triggering app (VS Code, etc.) to the front.
   - The list of shown notifications is kept in `%LOCALAPPDATA%\hooknotice\stack_state.json`.
   - Long commands are checked with Git Bash's `bash` before formatting. If it is not found, commands are shown
     without formatting.
   - The monospaced font is Consolas. The automatic line length is still calculated from Menlo's character
     width, so if the wrapping looks off, adjust `command_line_limit` in `config.json`.

## Customization

- **Settings window**: press **⚙** at the top right of a notification, or type **`/hooknotice:settings`** in
  Claude Code. You can change the display language, turn each kind of notification on or off, and change the delay
  before notifying, the sound, the notification width, and the line length for long commands.
  Press "Save" and the change applies from the next notification (no need to restart Claude Code). "Test
  notification" lets you check the current width.
- Kinds of notifications and their defaults (all notifications are supported, including the 12 Notification types
  of Claude Code and StopFailure):

  | Category | Kind (`notify` key) | Default |
  | --- | --- | --- |
  | Needs your answer | Permission needed `permission_request`, multiple-choice question `question`, plan approval `plan` | On |
  | Needs your answer | Permission dialog left open `permission_prompt` (overlaps with permission needed) | Off |
  | Progress | Done `stop`, stopped by an error `stop_failure` | On |
  | Progress | Idle after a response `idle_prompt` (overlaps with done) | Off |
  | MCP | Input form `elicitation_dialog`, request to open a URL `elicitation_url_dialog` | On |
  | MCP | Input completed `elicitation_complete`, response sent `elicitation_response` | Off |
  | Background | Input needed `agent_needs_input`, finished `agent_completed` | On |
  | Usage limit | Resumed automatically `quota_auto_resume_fired`, ready to resume `quota_auto_resume_stale`, stopped waiting `quota_auto_resume_disabled` | On |
  | Subagents and tasks | Subagent finished `subagent_stop`, task completed `task_completed`, teammate idle `teammate_idle` | Off |
  | Other | Signed in `auth_success` | Off |

- The settings are stored in `~/.claude/plugins/data/hooknotice-hooknotice/config.json` (kept across plugin
  updates), which you can also edit directly.

  ```json
  {
    "language": "en",
    "width": 600,
    "command_line_limit": null,
    "notify": { "permission_prompt": false, "agent_completed": true }
  }
  ```

  | Key | Default | Range | Meaning |
  | --- | --- | --- | --- |
  | `language` | `auto` | `auto` / `ja` / `en` | Display language. `auto` uses Japanese if the OS language is Japanese, and English otherwise (see "Language" below) |
  | `width` | 600 | 280–800 (px) | Width of the notification card |
  | `command_line_limit` | `null` | 20–200 (chars) | Line length at which long commands are split. `null` calculates it from the width (600px → 83 chars, 340px → 44 chars) |
  | `notify` | Table above | `true` / `false` per kind | Kinds not listed use their defaults |
  | `delay_seconds` | 6 | 0–60 (s) | Delay before notifying. Nothing is shown if you act during this time. 0 shows it at once. When `delay_mode` is `reading`, this is the minimum delay |
  | `delay_mode` | `fixed` | `fixed` / `reading` | How to decide the delay. `fixed` uses `delay_seconds` as is. `reading` uses the length of the notification body (command, plan, question, Claude's response, etc.; whitespace and line breaks are not counted; max 120 s) |
  | `reading_cpm` | 600 | 100–3000 (chars/min) | Reading speed for `reading`. For example, with 600, 300 characters take 30 s |
  | `sound` | `{"enabled": true, "source": "system", "system": "Glass", "file": ""}` | — | Sound. `source` is `system` (a system sound named in `system`) or `file` (a path in `file`) |

  If the file is missing, cannot be read as JSON, or has out-of-range values, the defaults are used.
- **Language**: notifications, buttons, the settings window, the setup dialog, the explanation Claude writes with
  "Explain", and the reason for denial returned to Claude when you press Cancel all use the chosen language.
  `auto` (the default) uses the first entry in "Preferred Languages" under System Settings > General >
  Language & Region on macOS, and the display language on Windows (falling back to environment variables such
  as `LANG`). A change in the settings window applies from the next notification (the settings window itself
  switches when you reopen it). Content coming from Claude Code, such as Claude's responses, commands, and plans,
  is shown as is (it is not translated).
  If you use "From text length" in English, a reading speed of about 1000–1200 characters per minute is a good
  starting point (whitespace is not counted).
- **Change the sound**: under "Sound" in the settings window, choose whether to play a sound, and pick a system
  sound (from `/System/Library/Sounds` on macOS, `%SystemRoot%\Media` on Windows) or any sound file. "Play" lets
  you listen to it. If the chosen file can no longer be found, the selected system sound plays instead.
- **Pause notifications temporarily**: start Claude Code with the environment variable `HOOKNOTICE_DISABLED=1`.
- **Change other positions and sizes**: edit `HEIGHT` (minimum height) / `MARGIN` / `GAP` in `notify_window.py`
  (in a clone of this repository; see "Development" below).

## Checking that it works

- Open the settings window (`/hooknotice:settings`) and press "Test notification". A sound plays, and a card with a
  gradient background appears at the bottom right.
- Ask Claude to run a command that needs permission (for example "run `ls` in a new shell"), and do not answer for
  about 6 seconds. A permission notification with "Cancel" / "OK" appears.
- Run the same kind of request several times: the windows stack vertically without overlapping. Click a window
  (anywhere other than the close button): it shrinks slightly, closes, and VS Code or your terminal comes to the
  front. Notifications above it move down.

## Troubleshooting

- **No window appears**:
  - Check that the plugin is enabled (`/plugin`, "Installed" tab) and that you restarted Claude Code after installing.
  - Check that `~/.claude/plugins/data/hooknotice-hooknotice/venv` exists. If not, restart Claude Code and choose
    "Run" in the setup dialog (see "Setup").
  - If `uv sync` run from the setup dialog failed, check `sync.log` (the last output) in the state folder.
  - If the setup dialog does not appear, check whether you chose "Don't ask again" (`setup.declined` in the state
    folder).
  - If you installed uv somewhere outside `PATH`, set the environment variable `HOOKNOTICE_UV` to its path.
- **Pressing OK does not allow it (the dialog in VS Code / the terminal stays)**:
  OK in the notification does not press the dialog's button. It returns "allow" to Claude Code from the hook.
  First check whether the tool (command) ran after you pressed OK.
  - **If it ran**: the permission worked. The dialog is just still shown.
  - **If it did not run**: check the following in order.
    1. You restarted Claude Code (in VS Code, reload the window) after installing or updating the plugin. Hooks
       are read at startup.
    2. Open `/hooks` in Claude Code and check that hooknotice is registered only once under `PermissionRequest`
       (if you used an older, hand-installed version, remove its hooks from `~/.claude/settings.json`). Other
       `PermissionRequest` hooks, and operations that match `deny` / `ask` rules in settings, may not be allowed
       even if you press OK.
- **No "Explain" button**: the explanation uses the Claude Code executable. The button is not shown if neither the
  `CLAUDE_CODE_EXECPATH` environment variable passed to the hook nor `claude` on `PATH` can be found.
- **The explanation says "Could not generate an explanation"**: check the reason shown. You may not be logged in to
  Claude Code, or you may have reached your usage limit. Press "Explain" again to retry.
- **Clicking does not bring the app to the front**: the triggering app is guessed from the environment variable
  `__CFBundleIdentifier` (or `TERM_PROGRAM` if that is missing). If neither is available, nothing is brought to
  the front. To add the app you use, add it to `TERM_PROGRAM_BUNDLE_IDS` in `hook_notify.py`.
- **Too many or too few notifications**: turn each kind on or off in the settings window (⚙ or
  `/hooknotice:settings`). If you turn off permission notifications, you answer only in the terminal's dialog,
  without notifications.
- **The stack position stays wrong**: `~/Library/Application Support/hooknotice/stack_state.json` records the
  order of the shown notifications. Records of processes that exited abnormally are cleaned up at the next start,
  but if the problem continues, you can safely delete this file.

## Data handling

The hooknotice code itself does not communicate over the network. External communication happens only in these
two cases.

- **When you choose "Run" in the setup dialog**: `uv sync` runs, and uv downloads PySide6-Essentials and shiboken6
  from PyPI. Only the package download requests are sent (the same happens when you run `uv sync` or
  `pip install` yourself).
- **When you press the "Explain" button**: the content of the operation being requested (the tool name, the path
  of the working directory, and the input such as the command; up to 8,000 characters) is passed to the `claude`
  command you are logged in to. It is sent to Anthropic through `claude` and uses your Claude usage (or API
  charges). It is handled under Anthropic's terms and privacy policy. Nothing is sent unless you press the button.
- **Files saved locally** (none of them are sent anywhere):

  | File | Contents |
  | --- | --- |
  | `config.json` (data folder) | The settings chosen in the settings window |
  | `prompts.json` (state folder) | Session IDs and the time the last prompt was sent (removed after one day) |
  | `stack_state.json` (state folder) | Process IDs and heights of the shown notifications (to stack them) |
  | `settings.lock` (state folder) | A marker so the settings window is not opened twice |
  | `sync.log` (state folder) | The output of `uv sync` run from the setup dialog |
  | `setup.lock` / `setup.declined` (state folder) | A marker so the setup dialog is not shown twice, and the "Don't ask again" marker |

  The data folder is `~/.claude/plugins/data/hooknotice-hooknotice/` (it also holds the `venv`, and is deleted when
  you uninstall the plugin). The state folder is `~/Library/Application Support/hooknotice/` on macOS and
  `%LOCALAPPDATA%\hooknotice\` on Windows. Commands and Claude's responses shown in notifications are not saved to files.
- **Files read**: while waiting for permission, hooknotice reads the end of the Claude Code conversation log
  (`transcript_path`) to check whether you already answered in the terminal. It only reads it; it never modifies,
  saves, or sends it. On macOS, it also reads the language setting (`~/Library/Preferences/.GlobalPreferences.plist`)
  when `language` is `auto`.

## Known limitations

hooknotice uses the following environment variables, which are not in the official documentation. If a future
version of Claude Code or macOS stops providing them, notifications and permission buttons keep working, and only
the related feature stops working.

| Environment variable | Set by | Used for | If unavailable |
| --- | --- | --- | --- |
| `CLAUDE_CODE_EXECPATH` | Claude Code | Calling `claude` for "Explain" | Uses `claude` on `PATH`. If not found, the "Explain" button is not shown |
| `__CFBundleIdentifier` | macOS | Bringing the original app to the front on click | Guessed from `TERM_PROGRAM`. If that fails, nothing is brought to the front |

Also, whether you answered a permission request in the terminal first is determined by reading the Claude Code
conversation log (`transcript_path` passed to the hook). The format of the log is not officially documented, so if
it changes, a notification may appear after the delay (6 seconds by default) even though you already answered
(closing it with ✕ has no side effects).

## Development

The plugin itself is in [plugins/hooknotice/](plugins/hooknotice/). To try local changes, load it directly
(this replaces the installed version for that session):

```bash
claude --plugin-dir ./plugins/hooknotice
```

To send a test notification without Claude Code, set up the environment once with `uv sync` in
`plugins/hooknotice` (this creates `.venv` there; it is used when `CLAUDE_PLUGIN_DATA` is not set), then:

```bash
cd plugins/hooknotice
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | python3 hook_notify.py --event permission_request
```

The command waits until the window is closed, prints the allow JSON on OK or the deny JSON on Cancel, and exits;
on ✕ it exits without printing anything. The rules for developing this repository are in [CLAUDE.md](CLAUDE.md).

## License

[MIT License](LICENSE) (Copyright (c) 2026 Tri9ster). No warranty. You are responsible for the results of operations
you allow or answer with the notification buttons.

The dependency [PySide6-Essentials](https://pypi.org/project/PySide6-Essentials/) (the core modules of Qt for
Python) and [shiboken6](https://pypi.org/project/shiboken6/) (which connects Python and Qt) are both provided under
LGPLv3 / GPLv2 / GPLv3 (or a commercial license). hooknotice does not bundle them. You install them into your own
environment from PyPI when you choose "Run" in the setup dialog (or run `pip install` yourself).

hooknotice is an unofficial tool for Claude Code and is not affiliated with Anthropic.
