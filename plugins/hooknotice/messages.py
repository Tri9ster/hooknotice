"""hooknotice の画面・ダイアログ・Claude に返すメッセージの文言（標準ライブラリのみ）。

言語は config.json の language（auto / ja / en）で決める。auto は OS の言語が日本語なら ja、それ以外は en。
文言は tr("キー", 差し込む値=...) で引く。キーが無い言語は英語、英語にも無ければキー名をそのまま返す。
新しい言語を足すときは、MESSAGES に言語コードの辞書を足し、hooknotice_config.LANGUAGES と
platform_support.system_language() の判定に加える（詳細は DevDocs/architecture.md 4.10）。
"""
from __future__ import annotations

from hooknotice_config import load_config
from platform_support import system_language

SUPPORTED_LANGUAGES = ("ja", "en")

_EXPLAIN_PROMPT_JA = """\
あなたは、Claude Code がこれから実行しようとしている操作を、許可するかどうか判断するユーザー向けに
日本語で解説します。入力として、ツール名・作業ディレクトリ・ツールへの入力（JSON）が渡されます。
次の構成の Markdown だけを出力してください（前置きや締めの挨拶は不要です）。

1. 冒頭に、この操作が全体として何をするものかを1〜2文で書く。コマンドが `&&`・`;`・`|` などで
   連結されていれば、その意味も一言添える。
2. `---` の後に `### ステップ別の詳細解説` を置き、区切りごとに `#### 1. <見出し>` を立て、
   該当部分をコードブロックで示し、各要素（コマンド・オプション・変数など）の働きを箇条書きで説明する。
   Bash 以外のツールでは、何を・どこに・どう作用するか（対象ファイル、変更内容、アクセス先など）を
   ステップに分けて説明する。
3. 削除・上書き・外部への送信・権限の変更・取り消せない操作など注意すべき点があれば、
   `### 注意点` に箇条書きで書く。無ければこの節は省く。
4. `---` の後に `### まとめ` を置き、この操作全体の目的を太字を使って1〜2文で書く。

あなたは何も実行しません。入力から読み取れないことを推測で書く場合は、推測であると明記してください。
"""

_EXPLAIN_PROMPT_EN = """\
You explain, in English, an operation that Claude Code is about to perform, for a user who must decide
whether to allow it. The input is the tool name, the working directory, and the tool input (JSON).
Output only Markdown with the following structure (no preamble or closing remarks).

1. Start with one or two sentences on what the operation does as a whole. If commands are chained
   with `&&`, `;`, `|` and so on, briefly say what the chaining means.
2. After `---`, add `### Step-by-step details`. For each part, add `#### 1. <heading>`, show the
   relevant part in a code block, and explain what each element (command, option, variable, etc.)
   does as a bulleted list. For tools other than Bash, split into steps what it acts on, where, and
   how (target files, changes, destinations, etc.).
3. If there is anything to be careful about, such as deleting, overwriting, sending data out,
   changing permissions, or anything that cannot be undone, list it under `### Cautions`.
   Omit this section if there is nothing.
4. After `---`, add `### Summary` and state the purpose of the whole operation in one or two
   sentences, using bold.

You do not run anything. If you write something that cannot be read from the input, say clearly
that it is a guess.
"""

MESSAGES: dict[str, dict[str, str]] = {
    "ja": {
        # 通知のタイトル（先頭に "Claude Code: " を付けて使う）
        "title.permission": "許可待ち",
        "title.question": "質問待ち",
        "title.plan": "計画の承認待ち",
        "title.idle": "応答待ち",
        "title.stop": "作業完了",
        "title.stop_failure": "エラーで停止",
        "title.subagent_stop": "サブエージェントの完了",
        "title.subagent_suffix": "（{agent}）",
        "title.task_completed": "タスクの完了",
        "title.teammate_idle": "チームの仲間が待機",
        "title.auth_success": "認証完了",
        "title.elicitation_dialog": "入力待ち（MCP）",
        "title.elicitation_url_dialog": "URL を開く依頼（MCP）",
        "title.elicitation_complete": "入力の完了（MCP）",
        "title.elicitation_response": "回答を送信（MCP）",
        "title.agent_needs_input": "入力待ち（バックグラウンド）",
        "title.agent_completed": "バックグラウンド作業の完了",
        "title.quota_auto_resume_fired": "利用上限の解除後に再開",
        "title.quota_auto_resume_stale": "再開待ち（Enter で再開）",
        "title.quota_auto_resume_disabled": "利用上限の待機を終了",
        "title.notification": "通知",
        "title.test": "テスト通知",
        # 通知の本文の定型句
        "body.stop_default": "作業が完了しました",
        "body.multi_select_md": "*(複数選択可)*",
        "body.error_type": "**エラーの種類**: `{error}`",
        "body.error_details": "**詳細**: {details}",
        "body.error_default": "エラーで応答が途中で終わりました",
        "body.agent_type": "**種類**: {agent}",
        "body.subagent_default": "サブエージェントが作業を終えました",
        "body.task_default": "タスク",
        "body.task_owner": "担当: {name}",
        "body.teammate_default": "チームの仲間",
        "body.teammate_idle": "{name} が作業を終えて待機に入りました",
        "body.teammate_team": "（チーム {team}）",
        "body.test": "横幅 {width}px のテスト通知です。クリックすると閉じます。",
        # Claude に返す拒否の理由
        "deny.permission": "通知ウィンドウでユーザーが拒否しました",
        "deny.plan": "通知ウィンドウでユーザーが計画を承認せず、計画モードを続けることを選びました",
        # 通知のボタン
        "button.explain": "解説",
        "button.explaining": "生成中…",
        "button.cancel": "キャンセル",
        "button.ok": "OK",
        "button.submit": "回答する",
        "button.plan_continue": "計画を続ける",
        "button.plan_default": "都度確認で承認",
        "button.plan_accept_edits": "編集を自動許可で承認",
        "button.plan_auto": "自動モードで承認",
        "window.multi_select": "（複数選択可）",
        "window.settings_tooltip": "通知の設定",
        # 「解説」
        "explain.prompt": _EXPLAIN_PROMPT_JA,
        "explain.input": "ツール: {tool}\n作業ディレクトリ: {cwd}\n入力:\n```json\n{input}\n```",
        "explain.unknown_tool": "不明",
        "explain.truncated": "\n…（長いため以降を省略）",
        "explain.generating": "解説を生成中…（10秒ほどかかります）",
        "explain.failed": "解説を生成できませんでした: {reason}",
        "explain.exit_code": "終了コード {code}",
        "explain.start_failed": "claude を起動できませんでした",
        # 準備（uv sync）の確認ダイアログ
        "setup.title": "hooknotice の準備",
        "setup.decline": "今後確認しない",
        "setup.close": "閉じる",
        "setup.copy_steps": "手順をコピー",
        "setup.not_now": "今はしない",
        "setup.run": "実行する",
        "setup.need_library": "通知ウィンドウを出すには、必要なライブラリ（PySide6-Essentials）のインストールが必要です。",
        "setup.updated": "依存ライブラリ（pyproject.toml / uv.lock）が更新されています。",
        "setup.uv_missing": "{need}\nuv が見つかりませんでした。次のどちらかで入れてください。\n\n{steps}",
        "setup.confirm": "{reason}\n次のコマンドを実行してよいですか？（PyPI からダウンロードします）\n\n"
                         "{command}",
        "setup.done": "準備が完了しました。次の通知から表示されます。",
        "setup.failed": "uv sync に失敗しました。出力を確認してください:\n{log}",
        "setup.exit_code": "終了コード: {code}",
        "setup.steps_mac": "【uv を入れる（推奨）】ターミナルで次のどれか:\n"
                           "  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
                           "  brew install uv\n"
                           "  pip3 install uv\n"
                           "  入れた後、Claude Code を起動し直すと、もう一度確認します。\n\n"
                           "【uv を使わずに pip で入れる】\n"
                           "  python3 -m venv \"{venv}\"\n"
                           "  \"{venv}/bin/pip\" install \"{req}\"",
        "setup.steps_win": "【uv を入れる（推奨）】PowerShell で:\n"
                           "  powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"\n"
                           "  入れた後、Claude Code を起動し直すと、もう一度確認します。\n\n"
                           "【uv を使わずに pip で入れる】\n"
                           "  py -3 -m venv \"{venv}\"\n"
                           "  \"{venv}\\Scripts\\pip\" install \"{req}\"",
        # Windows の MessageBox に書き添えるボタンの対応（{0} から順にボタンの名前）
        "dialog.hint2": "（OK = {1} / キャンセル = {0}）",
        "dialog.hint3": "（はい = {2} / いいえ = {1} / キャンセル = {0}）",
        # 設定画面
        "settings.window_title": "hooknotice の設定",
        "settings.group_display": "表示",
        "settings.language": "言語",
        "settings.language_auto": "自動（OS の言語）",
        "settings.language_hint": "次の通知から反映。この画面は開き直すと切り替わります",
        "settings.width": "通知の横幅（既定 {default}）",
        "settings.auto_limit": "幅に合わせて自動",
        "settings.chars_suffix": " 文字",
        "settings.line_limit": "長いコマンドを改行する文字数",
        "settings.delay_fixed": "固定",
        "settings.delay_reading": "文字数から自動",
        "settings.delay_mode": "通知を出すまでの待ち時間の決め方",
        "settings.seconds_suffix": " 秒",
        "settings.delay": "待ち時間（既定 {default}）",
        "settings.delay_hint_reading": "自動でもこれより短くしない。0 ですぐ表示",
        "settings.delay_hint_fixed": "この間に操作があれば出さない。0 ですぐ表示",
        "settings.cpm_suffix": " 文字/分",
        "settings.cpm": "読む速さ（既定 {default}）",
        "settings.cpm_hint": "1分に読む文字数。例: 300字 → {example}秒（上限 {max}秒）",
        "settings.suppress_focused_label": "アプリが前面のとき",
        "settings.suppress_focused": "Claude Code を起動したアプリが最前面なら通知しない",
        "settings.suppress_focused_hint": "ターミナルや VS Code などを見ているときは出さない（macOS のみ）。許可待ちは通常のダイアログで答える",
        "settings.group_sound": "通知音",
        "settings.sound_enabled": "通知音を鳴らす",
        "settings.sound_system": "システムの音（{dir}）",
        "settings.sound_file": "任意の音声ファイル",
        "settings.sound_file_placeholder": "ファイルを選択してください",
        "settings.browse": "選択…",
        "settings.preview": "試聴",
        "settings.sound_formats": "対応形式: {formats}",
        "settings.choose_sound": "通知音のファイルを選択",
        "settings.sound_filter": "音声ファイル ({pattern})",
        "settings.preview_failed": "試聴できません",
        "settings.file_not_found": "ファイルが見つかりません:\n{path}",
        "settings.not_selected": "（未選択）",
        "settings.group_scenes": "通知する場面",
        "settings.test": "テスト通知",
        "settings.test_tooltip": "今の幅でサンプルの通知を出します（保存してから出します）",
        "settings.save": "保存",
        "settings.close": "閉じる",
        "settings.save_failed": "保存できませんでした",
        "settings.sound_file_missing": "任意の音声ファイルが見つかりません。ファイルを選び直してください。",
        "settings.saved": "保存しました（次の通知から反映）",
        "settings.unsaved_title": "未保存の変更",
        "settings.unsaved": "変更が保存されていません。保存しますか？",
        # 通知する場面の分類
        "group.answer": "回答が必要",
        "group.milestone": "作業の区切り",
        "group.mcp": "MCP",
        "group.background": "バックグラウンド",
        "group.quota": "利用上限",
        "group.agent": "サブエージェント・タスク",
        "group.other": "その他",
        # 通知する場面（設定画面の表示名と説明）
        "scene.permission_request.label": "許可待ち",
        "scene.permission_request.desc": "ツールの実行の許可を求められたとき（OK / キャンセルで回答）",
        "scene.question.label": "選択肢の質問",
        "scene.question.desc": "Claude が選択肢で質問したとき（選択肢ボタンで回答）",
        "scene.plan.label": "計画の承認",
        "scene.plan.desc": "計画モードの計画の承認を求められたとき（承認ボタンで回答）",
        "scene.permission_prompt.label": "許可ダイアログの放置",
        "scene.permission_prompt.desc": "許可ダイアログが約6秒放置されたとき（「許可待ち」と重複するため既定オフ）",
        "scene.stop.label": "作業完了",
        "scene.stop.desc": "Claude が応答を終えたとき（最後の応答を表示）",
        "scene.stop_failure.label": "エラーで停止",
        "scene.stop_failure.desc": "API エラーなどで応答が途中で終わったとき",
        "scene.idle_prompt.label": "応答待ちの放置",
        "scene.idle_prompt.desc": "応答の終了から約60秒、入力が無いとき（「作業完了」と重複するため既定オフ）",
        "scene.elicitation_dialog.label": "入力フォーム",
        "scene.elicitation_dialog.desc": "MCP サーバーが入力フォームを出して約6秒たったとき",
        "scene.elicitation_url_dialog.label": "URL を開く依頼",
        "scene.elicitation_url_dialog.desc": "MCP サーバーがブラウザで URL を開くよう求めたとき",
        "scene.elicitation_complete.label": "入力の完了",
        "scene.elicitation_complete.desc": "URL 方式の入力要求が完了したとき",
        "scene.elicitation_response.label": "回答の送信",
        "scene.elicitation_response.desc": "MCP の入力要求への回答を送ったとき",
        "scene.agent_needs_input.label": "入力待ち",
        "scene.agent_needs_input.desc": "バックグラウンドのセッションが入力を待ち始めたとき",
        "scene.agent_completed.label": "作業の完了",
        "scene.agent_completed.desc": "バックグラウンドのセッションが終わった・失敗したとき",
        "scene.quota_auto_resume_fired.label": "自動で再開",
        "scene.quota_auto_resume_fired.desc": "利用上限の解除後に作業が自動で再開したとき",
        "scene.quota_auto_resume_stale.label": "再開待ち",
        "scene.quota_auto_resume_stale.desc": "スリープ中に上限が解除され、Enter での再開を待っているとき",
        "scene.quota_auto_resume_disabled.label": "待機の終了",
        "scene.quota_auto_resume_disabled.desc": "利用上限の待機を、自動再開せずに終えたとき",
        "scene.subagent_stop.label": "サブエージェントの完了",
        "scene.subagent_stop.desc": "サブエージェントが作業を終えたとき（種類と最後の報告を表示。頻繁に出るため既定オフ）",
        "scene.task_completed.label": "タスクの完了",
        "scene.task_completed.desc": "タスク一覧のタスクが完了したとき",
        "scene.teammate_idle.label": "チームの仲間が待機",
        "scene.teammate_idle.desc": "エージェントチームの仲間が作業を終えて待機に入るとき",
        "scene.auth_success.label": "認証完了",
        "scene.auth_success.desc": "認証が完了したとき",
    },
    "en": {
        "title.permission": "Permission needed",
        "title.question": "Question",
        "title.plan": "Plan approval",
        "title.idle": "Waiting for input",
        "title.stop": "Done",
        "title.stop_failure": "Stopped by an error",
        "title.subagent_stop": "Subagent finished",
        "title.subagent_suffix": " ({agent})",
        "title.task_completed": "Task completed",
        "title.teammate_idle": "Teammate idle",
        "title.auth_success": "Signed in",
        "title.elicitation_dialog": "Input needed (MCP)",
        "title.elicitation_url_dialog": "Request to open a URL (MCP)",
        "title.elicitation_complete": "Input completed (MCP)",
        "title.elicitation_response": "Response sent (MCP)",
        "title.agent_needs_input": "Input needed (background)",
        "title.agent_completed": "Background task finished",
        "title.quota_auto_resume_fired": "Resumed after the usage limit reset",
        "title.quota_auto_resume_stale": "Ready to resume (press Enter)",
        "title.quota_auto_resume_disabled": "Stopped waiting for the usage limit",
        "title.notification": "Notification",
        "title.test": "Test notification",
        "body.stop_default": "Claude has finished.",
        "body.multi_select_md": "*(select all that apply)*",
        "body.error_type": "**Error type**: `{error}`",
        "body.error_details": "**Details**: {details}",
        "body.error_default": "The response ended early because of an error.",
        "body.agent_type": "**Type**: {agent}",
        "body.subagent_default": "The subagent has finished.",
        "body.task_default": "Task",
        "body.task_owner": "Owner: {name}",
        "body.teammate_default": "A teammate",
        "body.teammate_idle": "{name} has finished and is now idle",
        "body.teammate_team": " (team {team})",
        "body.test": "This is a test notification, {width}px wide. Click to close it.",
        "deny.permission": "The user denied this in the notification window.",
        "deny.plan": "The user did not approve the plan in the notification window and chose to keep planning.",
        "button.explain": "Explain",
        "button.explaining": "Generating…",
        "button.cancel": "Cancel",
        "button.ok": "OK",
        "button.submit": "Submit",
        "button.plan_continue": "Keep planning",
        "button.plan_default": "Approve, ask each time",
        "button.plan_accept_edits": "Approve, auto-accept edits",
        "button.plan_auto": "Approve in auto mode",
        "window.multi_select": " (select all that apply)",
        "window.settings_tooltip": "Notification settings",
        "explain.prompt": _EXPLAIN_PROMPT_EN,
        "explain.input": "Tool: {tool}\nWorking directory: {cwd}\nInput:\n```json\n{input}\n```",
        "explain.unknown_tool": "unknown",
        "explain.truncated": "\n… (the rest is omitted because it is long)",
        "explain.generating": "Generating an explanation… (takes about 10 seconds)",
        "explain.failed": "Could not generate an explanation: {reason}",
        "explain.exit_code": "exit code {code}",
        "explain.start_failed": "Could not start claude",
        "setup.title": "hooknotice setup",
        "setup.decline": "Don't ask again",
        "setup.close": "Close",
        "setup.copy_steps": "Copy steps",
        "setup.not_now": "Not now",
        "setup.run": "Run",
        "setup.need_library": "To show notification windows, hooknotice needs a library (PySide6-Essentials) to be installed.",
        "setup.updated": "The dependencies (pyproject.toml / uv.lock) have been updated.",
        "setup.uv_missing": "{need}\nuv was not found. Install it in one of the following ways.\n\n{steps}",
        "setup.confirm": "{reason}\nRun the following command? (It downloads packages from PyPI.)\n\n"
                         "{command}",
        "setup.done": "Setup is complete. Notifications will appear from the next one.",
        "setup.failed": "uv sync failed. Check the output:\n{log}",
        "setup.exit_code": "Exit code: {code}",
        "setup.steps_mac": "[Install uv (recommended)] Run one of these in a terminal:\n"
                           "  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
                           "  brew install uv\n"
                           "  pip3 install uv\n"
                           "  After installing, restart Claude Code and hooknotice will ask again.\n\n"
                           "[Install with pip instead of uv]\n"
                           "  python3 -m venv \"{venv}\"\n"
                           "  \"{venv}/bin/pip\" install \"{req}\"",
        "setup.steps_win": "[Install uv (recommended)] In PowerShell:\n"
                           "  powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"\n"
                           "  After installing, restart Claude Code and hooknotice will ask again.\n\n"
                           "[Install with pip instead of uv]\n"
                           "  py -3 -m venv \"{venv}\"\n"
                           "  \"{venv}\\Scripts\\pip\" install \"{req}\"",
        "dialog.hint2": "(OK = {1} / Cancel = {0})",
        "dialog.hint3": "(Yes = {2} / No = {1} / Cancel = {0})",
        "settings.window_title": "hooknotice settings",
        "settings.group_display": "Display",
        "settings.language": "Language",
        "settings.language_auto": "Automatic (OS language)",
        "settings.language_hint": "Applies from the next notification. Reopen this window to switch its language",
        "settings.width": "Notification width (default {default})",
        "settings.auto_limit": "Fit to width",
        "settings.chars_suffix": " chars",
        "settings.line_limit": "Wrap long commands at",
        "settings.delay_fixed": "Fixed",
        "settings.delay_reading": "From text length",
        "settings.delay_mode": "How to decide the delay before notifying",
        "settings.seconds_suffix": " s",
        "settings.delay": "Delay (default {default})",
        "settings.delay_hint_reading": "The automatic delay is never shorter than this. 0 shows it at once",
        "settings.delay_hint_fixed": "Nothing is shown if you respond within this time. 0 shows it at once",
        "settings.cpm_suffix": " chars/min",
        "settings.cpm": "Reading speed (default {default})",
        "settings.cpm_hint": "Characters read per minute. E.g. 300 chars → {example} s (max {max} s)",
        "settings.suppress_focused_label": "When the app is in front",
        "settings.suppress_focused": "Do not notify while the app running Claude Code is frontmost",
        "settings.suppress_focused_hint": "Nothing is shown while you are looking at your terminal or VS Code (macOS only). Permission requests are answered in the usual dialog",
        "settings.group_sound": "Sound",
        "settings.sound_enabled": "Play a sound",
        "settings.sound_system": "System sound ({dir})",
        "settings.sound_file": "Custom sound file",
        "settings.sound_file_placeholder": "Choose a file",
        "settings.browse": "Browse…",
        "settings.preview": "Play",
        "settings.sound_formats": "Supported formats: {formats}",
        "settings.choose_sound": "Choose a sound file",
        "settings.sound_filter": "Sound files ({pattern})",
        "settings.preview_failed": "Cannot play the sound",
        "settings.file_not_found": "File not found:\n{path}",
        "settings.not_selected": "(none selected)",
        "settings.group_scenes": "When to notify",
        "settings.test": "Test notification",
        "settings.test_tooltip": "Shows a sample notification at the current width (saves first)",
        "settings.save": "Save",
        "settings.close": "Close",
        "settings.save_failed": "Could not save",
        "settings.sound_file_missing": "The custom sound file was not found. Choose the file again.",
        "settings.saved": "Saved (applies from the next notification)",
        "settings.unsaved_title": "Unsaved changes",
        "settings.unsaved": "Your changes have not been saved. Save them?",
        "group.answer": "Needs your answer",
        "group.milestone": "Progress",
        "group.mcp": "MCP",
        "group.background": "Background",
        "group.quota": "Usage limit",
        "group.agent": "Subagents and tasks",
        "group.other": "Other",
        "scene.permission_request.label": "Permission needed",
        "scene.permission_request.desc": "When a tool asks for permission to run (answer with OK / Cancel)",
        "scene.question.label": "Multiple-choice question",
        "scene.question.desc": "When Claude asks a multiple-choice question (answer with the choice buttons)",
        "scene.plan.label": "Plan approval",
        "scene.plan.desc": "When a plan from plan mode needs approval (answer with the approval buttons)",
        "scene.permission_prompt.label": "Permission dialog left open",
        "scene.permission_prompt.desc": "When a permission dialog has been left for about 6 seconds "
                                        "(off by default because it overlaps with \"Permission needed\")",
        "scene.stop.label": "Done",
        "scene.stop.desc": "When Claude finishes responding (shows the last response)",
        "scene.stop_failure.label": "Stopped by an error",
        "scene.stop_failure.desc": "When a response ends early because of an API error or similar",
        "scene.idle_prompt.label": "Idle after a response",
        "scene.idle_prompt.desc": "When there is no input for about 60 seconds after a response "
                                  "(off by default because it overlaps with \"Done\")",
        "scene.elicitation_dialog.label": "Input form",
        "scene.elicitation_dialog.desc": "About 6 seconds after an MCP server shows an input form",
        "scene.elicitation_url_dialog.label": "Request to open a URL",
        "scene.elicitation_url_dialog.desc": "When an MCP server asks you to open a URL in the browser",
        "scene.elicitation_complete.label": "Input completed",
        "scene.elicitation_complete.desc": "When a URL-based input request is completed",
        "scene.elicitation_response.label": "Response sent",
        "scene.elicitation_response.desc": "When a response to an MCP input request is sent",
        "scene.agent_needs_input.label": "Input needed",
        "scene.agent_needs_input.desc": "When a background session starts waiting for input",
        "scene.agent_completed.label": "Finished",
        "scene.agent_completed.desc": "When a background session finishes or fails",
        "scene.quota_auto_resume_fired.label": "Resumed automatically",
        "scene.quota_auto_resume_fired.desc": "When work resumes automatically after the usage limit resets",
        "scene.quota_auto_resume_stale.label": "Ready to resume",
        "scene.quota_auto_resume_stale.desc": "When the limit reset during sleep and it is waiting for Enter to resume",
        "scene.quota_auto_resume_disabled.label": "Stopped waiting",
        "scene.quota_auto_resume_disabled.desc": "When waiting for the usage limit ends without resuming automatically",
        "scene.subagent_stop.label": "Subagent finished",
        "scene.subagent_stop.desc": "When a subagent finishes (shows its type and final report; "
                                    "off by default because it is frequent)",
        "scene.task_completed.label": "Task completed",
        "scene.task_completed.desc": "When a task in the task list is completed",
        "scene.teammate_idle.label": "Teammate idle",
        "scene.teammate_idle.desc": "When an agent team member finishes and goes idle",
        "scene.auth_success.label": "Signed in",
        "scene.auth_success.desc": "When authentication completes",
    },
}

_language: str | None = None


def resolve_language(setting: str) -> str:
    """設定値（auto / ja / en）を、実際に使う言語（ja / en）にする。"""
    return setting if setting in SUPPORTED_LANGUAGES else system_language()


def language() -> str:
    """今のプロセスで使う言語。最初に呼ばれたときに config.json と OS の言語から決め、以後は同じ値を返す。"""
    global _language
    if _language is None:
        _language = resolve_language(load_config().language)
    return _language


def tr(key: str, **kwargs) -> str:
    """キーに対応する文言を返す。kwargs があれば str.format で差し込む。"""
    text = MESSAGES.get(language(), {}).get(key) or MESSAGES["en"].get(key) or key
    return text.format(**kwargs) if kwargs else text


def title(key: str) -> str:
    """通知のタイトル（"Claude Code: " + 文言）。"""
    return "Claude Code: " + tr(key)
