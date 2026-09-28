---
name: settings
description: Open the hooknotice settings window (which notifications to show, width, sound, wait time, language). The user runs it as /hooknotice:settings.
disable-model-invocation: true
---

# Open the hooknotice settings window

Run the following command **exactly once, as is** (the settings window is started detached, so the command returns immediately).

macOS:

```bash
CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA}" "${CLAUDE_PLUGIN_DATA}/venv/bin/python3" "${CLAUDE_PLUGIN_ROOT}/settings_window.py" --detach
```

Windows (Git Bash):

```bash
CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA}" "${CLAUDE_PLUGIN_DATA}/venv/Scripts/python.exe" "${CLAUDE_PLUGIN_ROOT}/settings_window.py" --detach
```

- On success, only tell the user (in their language) that the hooknotice settings window is open and that saved changes apply from the next notification.
- If the error says the Python in `venv` does not exist, tell the user that setup is not done yet: restart Claude Code and choose "Run" in the "hooknotice setup" dialog. Do not run `uv sync` yourself.
- If the settings window is already open, do not open another one (tell the user to use the existing window).
