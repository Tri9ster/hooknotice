# hooknotice 仕様書

## 1. 概要

- **名称**: hooknotice（Claude Code 応答待ち通知）
- **目的**: Claude Codeが許可確認や質問で応答待ちのまま停止していることに、離席中や別画面作業中でも気づけるようにする。
- **対象OS**: macOS（Windows は対応コードのみで実機未確認。OS ごとの違いは `platform_support.py`、4章末）
- **対象ツール**: Claude Codeのみ
- **実装**: `hook_notify.py`（標準ライブラリのみ）+ `notify_window.py`（PySide6/Qt、`uv` 管理の venv）。
  常駐デーモンやプロセス間通信は持たず、通知1件につき使い捨てのプロセスを起動する。

## 2. 要件

| # | 要件 | 実現方法 |
| --- | --- | --- |
| 1 | 許可確認・質問待ちで停止時に音と通知を出す | `afplay` でシステムサウンド再生 + PySide6の独自ウィンドウ表示 |
| 2 | 通知は最前面に表示される | `Qt.WindowStaysOnTopHint` |
| 3 | ユーザーが操作するまで自動では消えない | タイマーによる自動クローズを行わない |
| 3a | 許可待ちに通知ウィンドウから直接回答できる | 同期Hookがウィンドウの OK / キャンセルを待ち、`decision` の JSON を返す（4章） |
| 4 | 発火元ウィンドウを前面化できる | クリックで `osascript`（`tell application id <bundle id> to activate`） |
| 5 | Claude Code本体の動作を妨げない | 許可待ち以外のHookは `async: true` で表示プロセスを切り離して起動。許可待ちは回答待ちでブロックするが、✕で即座に通常フローへ戻せる。`hook_notify.py` は常に exit 0 |
| 6 | 複数通知が重ならない | ファイルロックで排他制御する共有の段（スタック）割り当て（3章参照） |

### 割り切り事項

- ウィンドウ表示時にフォーカスは奪わない（`activate()` を呼ばないため、前面に出るが
  キーボードフォーカスは移らない）。
- 通知音は1回のみ再生（繰り返し再生なし）。
- 発火元の特定はアプリ単位（同一アプリの複数ウィンドウ/タブは区別しない）。
- 許可待ちの Hook は同期実行だが、Claude Code（VS Code 拡張で確認）の許可ダイアログは
  Hook の完了を待たず通知と同時に表示され、どちらで回答してもよい（2026-09-24 実機確認）。
  ターミナル側で先に回答しても Claude Code は Hook を終了させない（2026-09-27 実機確認）。そのため Hook が
  会話の記録（`transcript_path`）で回答済みかを確かめ、回答済みなら通知を出さない・表示中なら閉じる（4章）。
- 自動許可（auto）モード等で許可確認自体が行われない場合は、Hook も発火せず通知も出ない。
- 「このセッション中は常に許可」相当の回答（`updatedPermissions`）には対応しない。
- 「解説」は押すたびに Claude（Sonnet）を1回呼ぶため、Claude の利用枠を消費し、生成に10〜15秒ほどかかる。
  claude の実行ファイルが見つからない環境では解説ボタンを出さない。
- トレイメニュー等の設定UIは無い。カスタマイズは `notify_window.py` の定数を直接編集する。

## 3. 処理の流れ

```
Claude Code
  │ Hook発火 (PermissionRequest / Notification)、async実行
  ▼
hook_notify.py（標準ライブラリのみ）
  ├─ stdin の Hook ペイロード(JSON)から cwd を取得
  ├─ __CFBundleIdentifier / TERM_PROGRAM から発火元アプリの bundle id を推定
  ├─ .venv/bin/python3 notify_window.py --title ... --bundle-id ...
  │    （Bash の許可待ちは --description ... --command ...、それ以外は --body ...）
  ├─ 許可待ち以外: 切り離して起動し、すぐに exit 0       … subprocess.Popen(start_new_session=True)
  └─ 許可待ち: --actions を付けて起動し、終了を待つ         … subprocess.run(stdout=PIPE)
       ├─ stdout が allow → {"hookSpecificOutput": {..., "decision": {"behavior": "allow"}}} を出力
       ├─ stdout が deny  → {..., "decision": {"behavior": "deny", "message": ...}} を出力
       └─ dismiss 等      → 何も出力しない（通常の許可ダイアログに委ねる）。いずれも exit 0

notify_window.py（PySide6・使い捨てプロセス）
  ├─ 内容に合わせてカードの高さを決める
  ├─ 到着順リストの末尾に自分と高さを追加（ファイルロックで排他制御）し、以後定期的に読み直して詰める
  │    （~/Library/Application Support/hooknotice/stack_state.json）
  ├─ afplay でサウンド再生                                  … 切り離して起動
  ├─ アニメーションするグラデーション背景のカード型ウィンドウを画面右下に表示
  ├─ クリック時: osascript で発火元アプリを前面化 → ウィンドウを閉じる
  ├─ --actions 時: OK / キャンセル / ✕・クリックで allow / deny / dismiss を stdout に出力して閉じる
  └─ ウィンドウが閉じられたら Qt イベントループが終了し、スタック段を解放してプロセス終了
```

許可待ち以外では `hook_notify.py` 側は `subprocess.Popen(..., start_new_session=True)` で
子プロセスを切り離すため、Hook自体はウィンドウが閉じられるのを待たずに終了する。
許可待ちではウィンドウが閉じられるまで Hook が終了しない（同期Hook、`timeout: 600`）。

## 4. `hook_notify.py` の仕様

- 引数 `--event`: `permission_request` / `notification` / `stop` / `stop_failure`（Hook から）。
  `permission_prompt` / `question` / `idle` は手動テスト用に残している。
- 設定の `notify`（場面ごとのオン/オフ）を `scene_key` で引き、オフなら何もせず終了する（許可待ちは何も出力しない＝
  通常の許可ダイアログ）。場面は、許可待ちは tool_name で `question`（AskUserQuestion）/ `plan`（ExitPlanMode）/
  `permission_request`、Notification は `notification_type`、Stop は `stop`、StopFailure は `stop_failure`。
- 放置の判定: 場面がオンなら、待ち時間（`Config.delay_for`）だけ待ってから通知する（`needs_delay`）。
  - 待ち時間は、`delay_mode` が `fixed` なら `delay_seconds`（既定6秒）。`reading` なら
    `max(delay_seconds, ceil(文字数 × 60 ÷ reading_cpm))`（上限 `READING_DELAY_MAX` = 120 秒。`delay_seconds` が 0 ならすぐ）。
    文字数は、VS Code 側でユーザーが読む本文（`reading_text`）を空白・改行を除いて数える（`count_chars`）:
    計画・質問は `tool_markdown`、Bash は説明とコマンド、Edit / MultiEdit は `old_string` と `new_string`、
    Write は `content`、Stop / StopFailure / サブエージェント・タスクは通知の本文、それ以外は `build_body`。
  - 許可待ち（同期）は、待っている間 0.5 秒ごとに会話の記録を読み（`AnswerWatcher`）、ターミナル側で答えられたら
    何も出力せずに終了する。記録にそのツール呼び出し（`tool_use`）の結果（`tool_result`）が書かれたら回答済みとみなす
    （拒否はすぐ、許可はツールの実行後に書かれる）。呼び出しの書き込みは Hook の開始より遅れることがあるので、
    待つ間も探し続ける。同じ内容の過去の呼び出しは、回答済みのものを除いて最も古い未回答のものを対象にする。
    該当する呼び出しが見つからなければ、従来どおり待ち時間の後に通知する。
  - 通知の表示後も `ask` が同じ確認を続け、ターミナル側で答えられたら Hook を終了する（ウィンドウは起動元の
    終了に気づいて閉じる）。長く動くコマンドを許可した場合は、実行が終わった時点で閉じる。
  - それ以外（async）は、待っている間に同じセッションで `UserPromptSubmit` があれば出さない（`prompted_since`）。
  - Claude Code 自身が待ってから出す `NO_DELAY_NOTIFICATIONS`（`permission_prompt` / `idle_prompt` /
    `elicitation_dialog` / `elicitation_url_dialog`）は待たない。
- `prompt_submit`（UserPromptSubmit）: 状態ディレクトリの `prompts.json` に `{session_id: 送信時刻}` を記録して終了する
  （`locked_state` で排他。1日以上前の記録は書き込みのたびに消す）。
- `session_start`（SessionStart・同期・すぐ終わる。何も出力しない）: 準備が必要（`needs_sync`）なら `start_setup()` で
  `hook_notify.py --setup`（内部用）を切り離して起動する。**`uv sync` は自動では実行せず、ダイアログで了承を得る。**
  - venv の場所（`platform_support.venv_dir`）: プラグインとして動いているとき（環境変数 `CLAUDE_PLUGIN_DATA` がある）は
    `<DATA>/venv`、それ以外は hooknotice のフォルダの `.venv`。
  - 準備が必要（`needs_sync`）: venv の Python が無い、または `uv sync` したときの印ファイル `<venv>/.hooknotice-synced`
    に書いた `pyproject.toml` / `uv.lock` の中身のハッシュ（SHA-256）が、今のファイルと違う。プラグインは更新のたびに
    ファイルがコピーし直され更新日時が変わるため、日時ではなく中身で比べる。印ファイルが空（ハッシュを書く前の版）なら
    従来どおり更新日時で比べる。印ファイルが無い venv（pip で作ったもの、手動の `uv sync`）は更新を確認しない。
  - `--setup`: 状態ディレクトリの `setup.lock` を `try_lock`（待たない排他ロック）で取れたときだけ、OS のダイアログ
    （`platform_support.ask_dialog`。macOS は osascript の display dialog、Windows は MessageBox）を出す。
    - uv がある: 「今後確認しない / 今はしない / 実行する」。「実行する」なら `uv sync --frozen` を hooknotice のフォルダで
      実行し（`VIRTUAL_ENV` は外す。プラグインなら `UV_PROJECT_ENVIRONMENT=<DATA>/venv` を付ける。出力は `sync.log`）、
      成功したら印ファイル（ハッシュ入り）を作って完了を、失敗したら `sync.log` の場所を表示する。ダイアログには実行する
      コマンドをそのまま見せる（`sync_command`）。
    - uv が無い: uv の入れ方と pip で入れる手順（`python3 -m venv <venv>` → `<venv>/bin/pip install "PySide6-Essentials>=6.7"`）
      を表示する。ボタンは「今後確認しない / 閉じる / 手順をコピー」（`copy_to_clipboard`）。
    - 「今後確認しない」は `setup.declined` を置き、以後ダイアログを出さない。
  - uv は `platform_support.find_uv()` で探す（環境変数 `HOOKNOTICE_UV` → PATH → よくある置き場所）。
    uv 自体の自動インストールはしない。
- `notification`: タイトルは `NOTIFICATION_TITLES`（12種。未知の種類は「Claude Code: 通知」）、本文は `message`
  （無ければ `title`）。
- `stop_failure`: タイトル「Claude Code: エラーで停止」、本文は `stop_failure_markdown` がエラーの種類（`error`）・
  詳細（`error_details`）・エラー文（`last_assistant_message`）を Markdown にしたもの。
- `subagent_stop` / `task_completed` / `teammate_idle`: 本文は `agent_markdown`。サブエージェントは種類（`agent_type`、
  タイトルにも付ける）と最後の報告（`last_assistant_message`）、タスクは `task_subject`・`task_description`・`teammate_name`、
  チームの仲間は `teammate_name` と `team_name`。既定はいずれもオフ。
  ウィンドウのタイトルを決める（`EVENT_TITLES`）。
- Bash の許可待ち（`tool_name == "Bash"` かつ `tool_input.command` あり、`bash_command`）は、
  `tool_input.description`（Claude が書くコマンドの説明）を `--description`、コマンド全文を
  `--command` として渡す。説明が無ければ `--description` は空。
- `--command` に渡すコマンドは、読みやすいよう `format_command` で複数行に整形する（表示専用。
  「解説」に渡す内容と Claude Code に返す決定には影響しない）。変えるのは空白・改行・行継続の `\` だけで、
  シェルとしての意味は変わらない。
  - トップレベルの `;` は行末に残し、まとまりの間に空行を1行はさむ。
  - `&&` / `||` は常に行末に残して ` \` を付け、次の要素は行頭から始める。
  - 1要素（`&&`/`||` の間）が設定の `command_line_limit`（既定は幅から自動計算。600px で83文字）を超える場合のみ、先頭の環境変数の代入を1行ずつ
    （行末に ` \`）、本体を2文字字下げ、パイプの2段目以降を次の行に `  | …` で置く。
  - 引用符・`\` エスケープ・`$(…)`・`` `…` ``・括弧の中では区切らない。`2>&1`・`>|`・`&`（バックグラウンド）も区切らない。
  - ヒアドキュメント、既に複数行、閉じていない引用符・括弧、トップレベルのコメント、`;;`、`|&` は整形しない。
  - 整形結果は `/bin/bash -n`（構文チェックのみ。実行しない）で確かめ、通らなければ元のまま表示する。
- それ以外の本文（`build_body`）は Claude Code が尋ねている内容:
  - `permission_request`: `"<tool_name>: <要約>"`。要約は `tool_input` のうち
    `TOOL_INPUT_SUMMARY_KEYS`（`command`, `file_path`, `notebook_path`, `pattern`, `url`, `query`,
    `description`）で最初に見つかった値、無ければ `tool_input` のJSON。
  - `question` / `idle`: Notification ペイロードの `message`。
  - `stop`: Stop ペイロードの `last_assistant_message`（Claude の最後の応答）を `stop_markdown` で取り出し、
    `--markdown` で本文欄に表示する。空なら本文は「作業が完了しました」。
  - いずれも取れなければ `cwd`。前後の空白だけを除き、省略や改行の削除は行わない。
- 許可待ち（`ACTION_EVENTS` = `permission_request`）は `--actions` 付きでウィンドウを起動して終了を待ち、
  その stdout を `permission_decision` で PermissionRequest の決定 JSON に変換して出力する
  （`allow` → `behavior: "allow"`、`deny` → `behavior: "deny"` と `message`: `DENY_MESSAGE`、
  それ以外は出力なし＝通常フロー）。
- 選択肢の質問（`QUESTION_TOOL` = `AskUserQuestion`）は、`question_choices` で質問ごとの選択肢
  （`question` / `header` / `multiSelect` / `labels`）を JSON にして `--actions --questions` で起動する。
  結果が `answers {質問文: 選んだ選択肢}` なら、元の `tool_input` に `answers` を足した `updatedInput` と
  `behavior: "allow"` を返し、質問を出さずに回答済みとして進める（複数選択はカンマ区切り）。
  `dismiss` は出力なし（ターミナルで答える）。キャンセルボタンは出さない（拒否すると質問自体が失敗するため）。
  選択肢の無い質問が1つでもあるなど選択肢を組み立てられない場合は、`NO_ACTION_TOOLS` として
  ボタン無しの通知を切り離して表示するだけにする。
- 計画の承認待ち（`PLAN_TOOL` = `ExitPlanMode`）は `--actions --plan-actions` で起動し、結果を次のように変換する。
  承認は `PLAN_RESULT_MODES` で権限モードに対応づけ、`updatedPermissions` の `setMode`（`destination: "session"`）で
  承認と同時にモードを切り替える。
  - `plan_auto` → `auto`、`plan_accept_edits` → `acceptEdits`、`plan_default` → `default`（いずれも `behavior: "allow"`）。
    ExitPlanMode は allow だけでは採用されないため、Hook に渡された `tool_input`（`plan` / `planFilePath`）を
    そのまま `updatedInput` として付ける
  - `deny`（計画を続ける）→ `behavior: "deny"` と `message`: `PLAN_DENY_MESSAGE`
  - `dismiss` → 出力なし（ターミナルの承認ダイアログで答える）
- この2つの本文は、`tool_input` の JSON ではなく `tool_markdown` が組み立てた Markdown を `--markdown` で渡す
  （組み立てられなければ従来の `--body`）。タイトルも `TOOL_TITLES` で変える。
  - `AskUserQuestion`（「Claude Code: 質問待ち」）: 質問ごとに `**[header]** question`（`multiSelect` なら
    *(複数選択可)*）と、番号付きの選択肢 `**label** — description`。`preview` は選択肢の下にコードブロックで表示
    （preview 内のバッククォートより長いフェンスで囲む）。質問が複数なら `---` で区切る。
  - `ExitPlanMode`（「Claude Code: 計画の承認待ち」）: `tool_input.plan`（Markdown）をそのまま。
- 許可待ちでボタンを出すときは、「解説」用に `explain_input` で組み立てた操作内容（ツール名・作業ディレクトリ・
  `tool_input` の JSON）を `--explain-input` で渡す。`tool_input` が `EXPLAIN_INPUT_MAX_CHARS`（8000文字）を
  超える場合は切り詰めて、その旨を書き添える。
- venv の Python（`uv sync` で作成。macOS は `<venv>/bin/python3`、Windows は `<venv>\Scripts\python.exe`）が存在しない場合は
  `start_setup()` で準備の確認ダイアログを出し、今回の通知は出さずに終了する（許可待ちならターミナル側で答える）。
- 環境変数 `HOOKNOTICE_DISABLED=1`: 何もせず終了する。
- macOS・Windows 以外（`platform_support.SUPPORTED` が偽）では何もせず終了する。
- 標準入出力は Windows では UTF-8 に切り替える（`use_utf8_stdio`。既定の ANSI コードページでは日本語の JSON が化けるため）。
- stdin が空・不正なJSONでも、例外発生時でも、常に exit 0。

### 発火元アプリの推定

1. 環境変数 `__CFBundleIdentifier`（macOSがアプリから起動したプロセスに設定する。例:
   `com.apple.Terminal`, `com.googlecode.iterm2`, `com.microsoft.VSCode`）
2. 無ければ `TERM_PROGRAM` を `TERM_PROGRAM_BUNDLE_IDS` で bundle id に変換
3. いずれも得られなければ空文字を渡し、`notify_window.py` 側はクリックしても前面化を行わない

### OS ごとの違い（`platform_support.py`）

標準ライブラリのみ。`hook_notify.py` と `notify_window.py` の両方から使う。macOS の処理は従来のまま移した。

| 関数 | macOS | Windows |
| --- | --- | --- |
| `plugin_data_dir` / `venv_dir` | プラグインなら `CLAUDE_PLUGIN_DATA` / `<DATA>/venv`、それ以外は空 / `.venv` | 同じ |
| `venv_python` | `<venv>/bin/python3` | `<venv>\Scripts\python.exe`（コンソール窓は `CREATE_NO_WINDOW` で出さない） |
| `popen_flags(detach)` | 切り離し時 `start_new_session=True` | `CREATE_NO_WINDOW`（切り離し時は `CREATE_NEW_PROCESS_GROUP` も） |
| `bash_path` | `/bin/bash` | `PATH` 上の `bash`（Git Bash）。無ければコマンドを整形しない |
| `state_dir` | `~/Library/Application Support/hooknotice` | `%LOCALAPPDATA%\hooknotice` |
| `locked_state` | 状態ファイルを `fcntl.flock` | 別ファイル `stack_state.lock` を `msvcrt.locking`（強制ロックのため状態ファイル自体はロックしない） |
| `pid_alive` | `os.kill(pid, 0)` | `OpenProcess` + `GetExitCodeProcess`（Windows の `os.kill(pid, 0)` はプロセスを終了させるため使わない） |
| `parent_exited` | 親 pid が変わった、または 1 | 起動時の親 pid が生きていない（Windows は親が終了しても親 pid が変わらない） |
| `system_sound_dir` / `list_system_sounds` | `/System/Library/Sounds` の `.aiff` | `%SystemRoot%\Media` の `.wav` |
| `DEFAULT_SYSTEM_SOUND` | `Glass` | `Windows Notify System Generic` |
| `play_sound(path)` | `afplay <path>`（aiff / wav / mp3 / m4a / caf） | `winsound.PlaySound`（WAV のみ） |
| `activate_app` | `osascript` で bundle id のアプリを前面化 | 何もしない |
| `is_executable` | `os.access(X_OK)` | ファイルの存在のみ（`X_OK` が常に真のため） |
| `system_language` | `~/Library/Preferences/.GlobalPreferences.plist` の `AppleLanguages` 先頭（`plistlib`） | `GetUserDefaultUILanguage` の主言語 |
| `ask_dialog` | osascript の display dialog | MessageBox。ボタンの対応の書き添え（`button_hints`）は呼び出し側が今の言語で渡す |

`system_language` はどちらの OS でも、取れなければ `LC_ALL` / `LC_MESSAGES` / `LANG` を見る。日本語なら `ja`、それ以外は `en`。

### 設定ファイル（`config.json`）

`hooknotice_config.py`（標準ライブラリのみ）の `load_config()` が、`hook_notify.py` と `notify_window.py` の
両方から読む。ファイルが無い・JSON として読めない・型や範囲が不正な値は、例外を出さず既定値にする。

| キー | 既定 | 範囲 | 使う場所 |
| --- | --- | --- | --- |
| `language` | `auto` | `auto` / `ja` / `en` | `messages.py`（表示の言語。下の「多言語対応」） |
| `width` | 600 | 280〜800（px） | `notify_window.py` の `WIDTH` |
| `command_line_limit` | `null`（自動） | 20〜200（文字） | `hook_notify.py` の `format_command` |
| `notify` | `NOTIFY_DEFAULTS` | 場面ごとの bool | `hook_notify.py` の `main`（`Config.enabled`） |
| `sound` | `enabled: true`、`source: "system"`、`system`: OS の既定、`file: ""` | — | `notify_window.py`（`Config.sound_path`） |
| `delay_seconds` | 6 | 0〜60（秒） | `hook_notify.py` の `main`（放置の判定）。`reading` のときは最低の待ち時間 |
| `delay_mode` | `fixed` | `fixed` / `reading` | `Config.delay_for`（待ち時間の決め方） |
| `reading_cpm` | 600 | 100〜3000（文字/分） | `Config.delay_for`（`reading` のときの読む速さ） |

場面の一覧（キー・既定・分類）は `hooknotice_config.SCENES` に1か所で定義し、Hook と設定画面の両方が使う。
表示名・説明・分類の見出しは `messages.py` の `scene.<key>.label` / `scene.<key>.desc` / `group.<分類>`。
`save_config` は指定したキーだけを上書きし（`notify` は場面ごとにマージ）、知らないキーは残す。書きかけを読まれないよう
一時ファイルに書いてから `os.replace` で置き換える。

### 設定画面（`settings_window.py`）

- PySide6。「表示」（言語、横幅、改行する文字数と「幅に合わせて自動」、待ち時間）と「通知する場面」（`SCENES` を分類ごとにチェックボックスで）。
- 「通知音」: 鳴らすか、システムの音（`list_system_sounds` の一覧、フォルダを OS ごとに表示）か任意の音声ファイル
  （`QFileDialog`、`SOUND_FILE_SUFFIXES` で絞る）か。「試聴」で `play_sound`。任意のファイルが無いと保存しない。
- 「保存」で `save_config`。「テスト通知」は保存してから `notify_window.py` でサンプルを出す。未保存で閉じると確認する。
- 起動元: 通知のタイトル行の ⚙（`notify_window._open_settings`、切り離して起動。`CLAUDE_PLUGIN_DATA` は環境変数で引き継ぐ）と、
  プラグインのスキル `/hooknotice:settings`（`plugins/hooknotice/skills/settings/SKILL.md`。Bash ツールには
  `CLAUDE_PLUGIN_DATA` が渡らないため、スキル本文で置換される `${CLAUDE_PLUGIN_DATA}` を環境変数として付けて起動する。
  `--detach` で自分を切り離して起動し直し、すぐ戻る）。
- 状態ディレクトリの `settings.lock`（`QLockFile`）で二重に開かない。

### 多言語対応（`messages.py`）

- 画面・ダイアログの文言と、Claude に返す拒否の理由（`deny.permission` / `deny.plan`）を、標準ライブラリのみの
  `messages.py` の辞書 `MESSAGES`（`ja` / `en`）に集める。`tr(キー, **差し込む値)` で引き、キーが無い言語は英語、
  英語にも無ければキー名を返す。通知のタイトルは `title(キー)`（`"Claude Code: "` + 文言）。
- 使う言語は `language()` がプロセスごとに1回決める: `config.json` の `language` が `ja` / `en` ならそれ、`auto`
  （既定・不正な値）なら `platform_support.system_language()`。`hook_notify.py`・`notify_window.py`・`settings_window.py`
  はそれぞれ別プロセスで同じ規則で決めるので、設定を変えると次の通知から全体がそろって切り替わる。
- 「解説」のシステムプロンプト（`explain.prompt`）も言語ごとに持ち、解説文をその言語で書かせる。
- 翻訳しないもの: Claude Code から届く内容（Claude の応答・コマンド・計画・質問と選択肢）、ボタンの結果値
  （`allow` / `deny` / `plan_*` / `answers `）、`sync.log` の見出し行以外の uv の出力。
- 依存の向きは `messages` → `hooknotice_config` → `platform_support`。下の2つは文言を持たない。

自動計算 `auto_line_limit(width)` は、コマンド欄の Menlo 11px の1文字幅 6.61px（実測）と、カード幅のうち
文字に使えない 34px（余白 20・枠 8・スクロールバー 6）から `floor((width − 34) / 6.61) − 2` とする。

## 5. `notify_window.py` の仕様

- 引数 `--title` / `--body` / `--description` / `--command` / `--bundle-id` / `--actions` / `--explain-input` / `--markdown` / `--plan-actions` / `--questions`。
- `--markdown`: 本文ラベルの代わりに Markdown の本文欄（`QTextBrowser`、解説欄と同じ見た目と整形）を表示する。
  クリックはコマンド欄と同じく本体クリック扱い（発火元アプリを前面化して閉じる）で、ホイールでスクロールできる。
  画面に収まらない場合は最小 `EXPLAIN_MIN_HEIGHT` まで縮めてスクロールさせる。
- `--actions`: カード下部に「キャンセル」「OK」ボタンを右寄せで表示する。閉じる際に結果を
  stdout に1行で出力する（OK: `allow`、キャンセル: `deny`、✕: `dismiss`）。
  押し間違いで回答を逃さないよう、本体クリック（コマンド欄・本文欄の上を含む）では閉じない。
  起動元（待っている Hook）が終了したこと（`os.getppid()` の変化、または起動時点で pid 1）を
  スタックのポーリングと同じ周期で検知し、何も出力せずに閉じる。
- `--plan-actions`（`--actions` と併用）: 「キャンセル」「OK」の代わりに `PLAN_BUTTONS` を2列のグリッドで表示する
  （「計画を続ける」`deny`・「都度確認で承認」`plan_default`・「編集を自動許可で承認」`plan_accept_edits`・
  「自動モードで承認」`plan_auto`）。「解説」ボタンは出さない。
- `--questions`（`--actions` と併用）: 質問ごとに見出し（`header`、無ければ質問文）と、選択肢のトグルボタンを
  縦に並べる。単一選択は `QButtonGroup` の排他、`multiSelect` は複数オン可。すべての質問で1つ以上選ぶと
  「回答する」が押せるようになり、`answers ` に続けて `{質問文: 選択肢}` の JSON を1行で出力して閉じる。
  JSON の形が崩れていればボタン無しの表示にする。
- 「解説」ボタン: `--explain-input` があり、claude の実行ファイル（`CLAUDE_CODE_EXECPATH` → PATH 上の `claude`
  の順に探す）が見つかる場合のみ、ボタン行の左端に出す。押すと `QProcess` で非同期に
  `claude -p --model sonnet --tools "" --setting-sources "" --no-session-persistence --system-prompt <EXPLAIN_PROMPT> <操作内容>`
  を起動し、完了したら結果の Markdown をコマンド欄の下の解説欄（`QTextBrowser`）に表示する。
  - 再帰防止: `--setting-sources ""` でユーザー設定の Hook を読ませず、環境変数 `HOOKNOTICE_DISABLED=1` も付ける。
    `--tools ""` でツールは一切実行させない。作業中プロジェクトの CLAUDE.md を読ませないよう、作業ディレクトリは一時ディレクトリにする。
    （`--bare` は OAuth 認証を読まないため使わない。）
  - 生成中はボタンを「生成中…」で無効化する。失敗時は理由を解説欄に出し、もう一度押せるようにする。
    ウィンドウを閉じたときに生成中なら子プロセスを kill する。
  - 解説欄はクリックしても閉じない（文字の選択・スクロールができる）。Qt の Markdown 表示を狭いカード向けに整える
    （見出しを小さく、コードを Menlo にして背景を付け、コードブロックも折り返す）。
  - 解説を表示したらカードの高さを測り直し、`StackSlot.update_height` で `stack_state.json` の自分の高さを
    更新する（下の通知はポーリングで下へずれる）。画面に収まらない分は、解説欄（最小 `EXPLAIN_MIN_HEIGHT`）→
    コマンド欄の順に縮めてスクロールさせる。
- 本文: `--description` があれば通常の文字で、`--command` があれば等幅フォントの背景付きブロック
  （`QTextEdit`、空白の無い長い文字列も途中で折り返す）で、上から順に表示する。どちらも無ければ `--body`。
- 幅: 設定の `width`（既定 600px）。起動時に1回だけ読み、表示中は変わらない。設定を変えた直後に
  幅の違う通知が並ぶと、スタックの列の位置は各通知の幅で計算するため一時的にずれることがある。
- 高さ: 高さは内容に合わせて決め、`HEIGHT`（110）を最小、
  「画面の利用可能な高さ − 2×`MARGIN`」を最大とする。最大を超える場合はコマンド欄をスクロールさせる
  （省略はしない）。コマンド欄の上でのクリックも本体クリックとして扱う（ホイールでのスクロールは可能）。
- ウィンドウ: フレームレス・角丸・常に最前面（`Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint`）。
  `Qt.Tool` を指定し、通知1件=1プロセスでもDockアイコンが乱立しないようにしている。
- 背景: `QLinearGradient` による2色のアニメーションするグラデーション。色相・角度に
  ランダムなジッターを加え、通知ごとに微妙に見た目が変わる。
- 配色: macOS の外観設定（`QApplication.styleHints().colorScheme()`）に従い、`THEMES` の
  `dark` / `light` を切り替える（判定できない場合は `dark`）。背景のベース色・ハイライトの彩度/明度の範囲・
  文字やボタンの色（`STYLE_SHEET` に差し込む）をテーマごとに持つ。`light` では輪郭が白い背景に
  溶けないよう薄い縁取りを描く。表示中に外観が切り替わった場合も `colorSchemeChanged` で追従する。
- 閉じるボタン、またはウィンドウ本体クリックで閉じる（`--actions` のときは閉じるボタンのみ）。どちらも中心を保ったまま
  `CLICK_SHRINK_RATIO`（94%）まで `CLICK_ANIMATION_MS`（120ms）かけて縮むアニメーションの後に閉じる。
  本体クリック時のみ、アニメーション完了後に発火元アプリを `osascript` で前面化する。
- スタック配置: `~/Library/Application Support/hooknotice/stack_state.json` に
  表示中の通知を到着順に `[{"pid": <pid>, "height": <高さ>}, ...]` で保持し、`fcntl.flock` で
  排他制御する（`height` の無い旧形式は `HEIGHT` とみなす）。起動時に末尾へ追加し、最新の通知から自分までの
  高さを下から順に積んだ位置に表示する（最新の通知が常に右下）。画面上端を超える場合は1列左に折り返す。
  各通知は `STACK_POLL_INTERVAL_MS`（250ms）ごとに読み直し、新しい通知が来たら上へ、下の通知が閉じられたら
  下へ `MOVE_ANIMATION_MS`（200ms）かけて移動する。`os.kill(pid, 0)` で生存確認し、異常終了したプロセスの記録は
  自動的に回収する。
- サウンド: 設定の `sound` から `Config.sound_path()` で鳴らすファイルを決め、`platform_support.play_sound` で鳴らす
  （鳴らさない設定なら無音。任意のファイルが無ければシステムの音）。

## 6. Claude Code側の連携仕様

プラグインの `plugins/hooknotice/hooks/hooks.json` で以下のHookを登録する（いずれも `type: "command"`, `async: true`）。
通知するかどうかは hooknotice の設定（`config.json` の `notify`）で決めるため、対象のイベントはすべて登録しておく。
コマンドは `python3 "${CLAUDE_PLUGIN_ROOT}/hook_notify.py" --event <種別>`。ユーザーのプラグインとして全プロジェクトで有効。
Hook のプロセスには `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA` が環境変数で渡り、`notify_window.py` などにも引き継がれる。
ただし `PermissionRequest` は決定を返すため `async` を付けず同期で登録し、`timeout: 600` を明記する
（async の Hook の出力は無視されるため）。

| Hookイベント | マッチャー | `--event` | 用途 |
| --- | --- | --- | --- |
| `PermissionRequest` | `*` | `permission_request` | ツール実行等の許可確認（同期、OK / キャンセルで回答） |
| `Notification` | （なし＝全12種） | `notification` | 種類は `notification_type` で判断 |
| `Stop` | （なし） | `stop` | 作業完了（Claude が応答を終えるたびに発火。ユーザーの中断時は発火しない） |
| `StopFailure` | （なし） | `stop_failure` | API エラーなどで応答が途中で終わった |
| `UserPromptSubmit` | （なし） | `prompt_submit` | プロンプトの送信時刻を記録するだけ（放置の判定に使う。通知はしない） |
| `SessionStart` | （なし） | `session_start` | venv を確認し、準備が必要なら `uv sync` を実行してよいかダイアログで確認する（同期 Hook・timeout 10。通知はしない） |
| `SubagentStop` | （なし） | `subagent_stop` | サブエージェントの完了 |
| `TaskCompleted` | （なし） | `task_completed` | タスク一覧のタスクの完了 |
| `TeammateIdle` | （なし） | `teammate_idle` | エージェントチームの仲間が待機に入る |

この3つは作業を止められる（block できる）イベントだが、通知だけなので async で登録し、何も出力しない。
`SubagentStart` と `TaskCreated` は、起動・作成のたびに出て回答も要らないため登録しない。

`Notification` の `permission_prompt`（許可待ちと重複）と `idle_prompt`（作業完了と重複）は、登録はするが
設定の既定をオフにして通知しない。

## 7. 対象範囲・非対応事項

- Windows / Linux は非対応。
- Cline / Roo Code は対象外。
- トレイメニュー等の設定UIは無い。

## 8. 変更履歴

### 2026-09-28（2回目）: Claude Code プラグインとして配布する

- **理由**: 共有が zip の手渡しと Hook の手動マージで手間がかかった。公開リポジトリ `Tri9ster/hooknotice` を
  プラグイン兼マーケットプレイスにし、`/plugin marketplace add` と `/plugin install` の2コマンドで導入・更新できるようにする。
- **変更内容**: リポジトリを `.claude-plugin/marketplace.json` と `plugins/hooknotice/`（`.claude-plugin/plugin.json`、
  `hooks/hooks.json`、`skills/settings/`、Python 一式）の構成にした。本体（`CLAUDE_PLUGIN_ROOT`）は更新のたびに入れ替わるため、
  venv と `config.json` は `CLAUDE_PLUGIN_DATA`（`~/.claude/plugins/data/hooknotice-hooknotice/`）に置く（4章）。
  `uv sync` の印ファイルには依存ファイルの中身のハッシュを書き、更新日時ではなく中身で比べるようにした。
  設定画面のスキルは `/hooknotice-settings` から `/hooknotice:settings` になった。docs は `docs/` にまとめた。
  `pyproject.toml` の `license-files` はプラグインのフォルダに LICENSE が無いため外した（`license = "MIT"` は残す）。

### 2026-09-28: 英語・日本語の多言語対応

- **理由**: 公開・プラグイン化に向けて、日本語以外の利用者にも使えるようにする。
- **変更内容**: 文言を `messages.py` に集め、`config.json` の `language`（`auto` / `ja` / `en`、既定 `auto`）で切り替える
  （4章「多言語対応」）。設定画面に「言語」を追加。「解説」の解説文と、キャンセル時に Claude に返す拒否の理由も
  選んだ言語にする。`SCENES` から表示名・説明を外し、分類はキーにした。README は英語（`README.md`）と日本語（`README.ja.md`）の2本にした。

### 2026-09-27（5回目）: 待ち時間を本文の文字数から決められるようにする

- **理由**: 計画・質問・長いコマンド・Claude の長い返答は、VS Code 側で読み終わる前に6秒が過ぎ、読んでいる途中で
  通知が出ていた。
- **変更内容**: 設定 `delay_mode`（`fixed` / `reading`）と `reading_cpm`（1分あたりに読む文字数）を追加した。
  `reading` では本文の文字数から待ち時間を決め、`delay_seconds` は最低の待ち時間になる（4章・5章）。
  設定画面に「固定 / 文字数から自動」と「読む速さ」の欄を追加した。既定は従来どおり `fixed`。

### 2026-09-27（4回目）: 許可待ちに6秒以内に答えたら通知を出さない

- **理由**: 許可待ちに VS Code 側ですぐ答えても、約6秒後に通知が出ていた。「待つ間に答えられると Claude Code が
  Hook を終了させる」という前提が実際には成り立たなかった（F-21）。
- **変更内容**: 許可待ちは待つ間も会話の記録で回答済みかを確かめ、回答済みなら通知を出さない。表示後に答えられた
  場合も通知を閉じる（4章）。

### 2026-09-27（3回目）: 準備（uv sync）が必要なときに確認ダイアログを出す

- **理由**: README を読まずに入れた人は `uv sync` を実行せず、`.venv` が無いと通知が黙って出なかった。
  依存を更新したときも同期されなかった。ただし `uv sync` の自動実行は避けたい（ユーザーの判断）。
- **変更内容**: `SessionStart` を登録し、venv が無いときや `pyproject.toml` / `uv.lock` が更新されたときに、
  `uv sync --frozen` を実行してよいかを OS のダイアログで確認する（4章・6章）。uv が無いときは uv の入れ方と
  pip で入れる手順を表示する。README の準備手順は手動の `uv sync` のままとし、pip の手順を追記した。

### 2026-09-27（2回目）: 名称を hooknotice に変更

- **理由**: 配布を予定しており、Anthropic は「Claude Code」「Anthropic」の名前を製品名の一部に使うことを禁じている。
  予定していた `claude-notifier` は同名の既存リポジトリもあった。PyPI・npm・GitHub・.com で未使用の `hooknotice` にした。
- **変更内容**: フォルダ `~/.claude/notifier` → `~/.claude/hooknotice`、`notifier_config.py` → `hooknotice_config.py`、
  スキル `/notifier-settings` → `/hooknotice-settings`、環境変数 `CLAUDE_NOTIFIER_DISABLED` → `HOOKNOTICE_DISABLED`、
  状態ファイルのフォルダ `claude-notifier` → `hooknotice`、pyproject の name、設定画面のタイトル、Hook のコマンドのパス。
  この変更履歴の過去の項目と開発記録は、当時の名前のまま残す。
- ライセンスを MIT にした（`LICENSE`）。依存を `PySide6` から `PySide6-Essentials` に絞った（使うのは QtCore・QtGui・QtWidgets のみ）。

### 2026-09-27: StopFailure と Notification 全12種への対応、設定画面の追加

- **理由**: API エラーでの停止や、バックグラウンド作業・利用上限まわりの通知が出なかった。また通知する場面や幅を
  変えるには settings.json / config.json を手で編集する必要があった。
- **変更内容**: `StopFailure` を登録し、`Notification` を種類を問わず1本で登録した（6章）。`config.json` に
  場面ごとのオン/オフ `notify` を追加し、Hook 側で判断するようにした（4章）。設定画面 `settings_window.py` と、
  起動元の ⚙ ボタン・スラッシュコマンド `/notifier-settings` を追加した。
  - 通知音を設定画面で選べるようにした（鳴らすか、OS ごとのシステムの音か任意のファイルか）。
    `notify_window.py` の定数 `SOUND_NAME` は廃止し、`config.json` の `sound` にした（5章）。
  - サブエージェント・タスク系の `SubagentStop` / `TaskCompleted` / `TeammateIdle` を追加した（既定オフ。4章・6章）。
  - すべての通知を、約6秒（`delay_seconds`）放置されたときだけ出すようにした。画面を見てすぐ答えられる場面で
    通知が出て煩わしかったため。`UserPromptSubmit` を登録して送信時刻を記録する（4章・6章）。
    検討した「長くかかった作業のときだけ作業完了を通知する」案は、シンプルさを優先して取り下げた。

### 2026-09-26（3回目）: 計画承認の通知で承認ボタンが効かない不具合を修正

- **理由**: 計画承認の通知で承認ボタン（自動モード・都度確認・編集を自動許可）を押しても、Claude Code が先に進まなかった。
  一時ログで調べると、クリックは届き、Hook も allow を出力していたが、Claude Code が採用していなかった
  （拒否の「計画を続ける」は効いていた）。
- **原因**: ExitPlanMode（と AskUserQuestion）は、allow に `updatedInput` を組にしないと採用されない。
- **変更内容**: 計画承認の allow に、元の `tool_input` を `updatedInput` として付けた（4章）。実機で
  「自動モードで承認」から計画モードを抜けられることを確認した。

### 2026-09-26（2回目）: 作業完了の通知を追加し、応答待ちの通知を置き換える

- **理由**: 応答が終わったことを知らせるのは `idle_prompt`（約60秒放置し、端末から離れていると判定されたときだけ）
  のみで、作業が終わってもすぐには気づけなかった。
- **変更内容**: `Stop` Hook（async）を登録し、`--event stop` で「Claude Code: 作業完了」の通知を出すようにした。
  本文は `last_assistant_message` を Markdown で表示する（4章）。同じ完了で2回通知しないよう `idle_prompt` の
  登録を外した（6章）。

### 2026-09-26: 右下から積む配置と、計画の承認待ち・選択肢の質問へのボタン追加

- **理由**: 通知が右上から積まれ、新しい通知ほど下（目線から遠い位置）に出ていた。また計画の承認待ち
  （ExitPlanMode）はボタン無しの通知で、承認するにはターミナルに戻る必要があった。
- **変更内容**:
  - スタック配置を右下からに変え、最新の通知が常に右下、古い通知ほど上に並ぶようにした（5章）。
  - 計画の承認待ちに「計画を続ける」と、承認後の権限モード別の承認ボタン3つを出すようにした（4章・5章）。
    承認時は PermissionRequest の `updatedPermissions`（`setMode`）でモードも切り替える。
    計画を続ける場合、修正指示の文章は通知から入力できないため固定のメッセージで拒否する。
  - 選択肢の質問（AskUserQuestion）に選択肢ボタンと「回答する」を出し、PermissionRequest の
    `updatedInput`（元の質問 + `answers`）で回答を返すようにした（4章・5章）。自由記述（その他）は通知からは入力できない。
  - ボタン付きの通知（`--actions`）は、ボタン以外を押して意図せず閉じてしまうことがあったため、
    本体クリックでは閉じず、✕ でのみ閉じるようにした（5章）。
  - 既定の幅を 420px から 600px に変更した（文字数は自動で 56 → 83）。
  - Windows 対応の準備として、OS ごとに違う処理を `platform_support.py` に切り出し、Windows の分岐を実装した
    （4章）。macOS の動作は変えていない。Windows は実機で未確認。等幅フォントに Consolas を追加した。

### 2026-09-25（4回目）: 質問・計画の承認待ちの通知を Markdown で表示

- **理由**: AskUserQuestion / ExitPlanMode の通知本文が `tool_input` の JSON そのままで、何を聞かれているか読みにくかった。
- **変更内容**: `hook_notify.py` に `tool_markdown` を追加し、質問と選択肢（preview を含む）・計画を Markdown に
  して `--markdown` で渡すようにした（4章）。`notify_window.py` は本文欄として Markdown を表示する（5章）。
  あわせて Markdown の整形で、見出しの文字サイズの段階を打ち消し、コードの文字を 11px にそろえた。

### 2026-09-25（3回目）: 通知の横幅と改行する文字数を設定ファイルで変えられるようにする

- **理由**: 横幅（`WIDTH`）と長いコマンドを改行する文字数（`FORMAT_LINE_LIMIT`）がコードに直書きだった。
- **変更内容**: `notifier/config.json`（`width`、`command_line_limit`）を追加し、`notifier_config.py` で読み込むようにした。
  文字数は `null` なら幅から自動計算する（`floor((width − 34) / 6.61) − 2`。340px → 44）。
  設定画面は作らない（通知は1件ごとに起動するので、ファイルの変更が次の通知から反映される）。
  実機で試した結果、既定の幅を 340px から 420px に変更した（文字数は自動で 44 → 56）。

### 2026-09-25（2回目）: コマンド欄のワンライナーを整形して表示

- **理由**: `;`・`&&`・パイプ・環境変数の前置きがつながった長いワンライナーが1行のまま表示され、読みにくかった。
- **変更内容**: `hook_notify.py` に `format_command` を追加し、Bash の許可待ちのコマンド欄を、意味を変えずに
  複数行へ整形して表示するようにした（4章）。

### 2026-09-25: 許可待ちの通知に「解説」ボタンを追加

- **理由**: 長いワンライナーなどは、何をする操作なのか読み解くのに時間がかかり、許可の判断がしにくかった。
- **変更内容**: 許可待ちの通知に「解説」ボタンを追加し、押すと Claude（Sonnet、`claude -p`）が操作の解説を
  Markdown で書き、通知カードを下に伸ばして表示するようにした（4章・5章）。すべての許可待ち
  （Bash 以外のツールも含む）が対象。

### 2026-09-24（2回目）: 配色を macOS の外観設定（ライト/ダーク）に従わせる

- **理由**: ダーク配色で固定されており、ライトモードでは周囲から浮いて見えた。
- **変更内容**: 色の定義を `THEMES`（`dark` / `light`）と `STYLE_SHEET` のテンプレートにまとめ、
  起動時と外観の切り替え時に適用するようにした（5章）。ダーク側の見た目は変更前と同じ。

### 2026-09-24: 許可待ちの通知から OK / キャンセルで回答できるようにする

- **理由**: 通知に気づいてもターミナルに戻らないと許可できず、手間だった。
- **変更内容**:
  - `PermissionRequest` の Hook を同期実行（`async` を外し `timeout: 600`）に変更し、
    `hook_notify.py` がウィンドウの回答を待って `decision`（allow / deny）の JSON を返すようにした（4章・6章）。
  - `notify_window.py` に `--actions` を追加し、「キャンセル」「OK」ボタンと結果の stdout 出力、
    起動元の Hook 終了時の自動クローズを実装した（5章）。
  - ✕・本体クリックは決定を返さず、通常の許可ダイアログに委ねる。
  - `AskUserQuestion` / `ExitPlanMode` も PermissionRequest を通るため、キャンセルで質問自体が
    拒否される不具合があった。これらはボタン無しの通知のみとした（`NO_ACTION_TOOLS`）。
  - 実機（manual モード）で OK → 実行、キャンセル → 拒否、✕ → ターミナルのダイアログで回答、を確認。

### 2026-09-23（2回目）: 通知内容を省略しない・コマンドに説明を付ける

- **理由**: 本文を120字で切り、カードの高さも固定だったため、長いコマンドや複数行のコマンドが
  読み取れなかった。また、コマンドだけでは何をしようとしているのか分かりにくかった。
- **変更内容**:
  - 本文の切り詰めと改行の削除をやめた（4章）。
  - Bash の許可待ちでは、Claude が書く `tool_input.description` を説明として上に、コマンド全文を
    等幅ブロックで下に表示するようにした（5章）。説明を日本語にするため、グローバルの CLAUDE.md に
    Bash の description を日本語で書くルールを追加した。
  - カードの高さを内容に合わせて可変にし（`HEIGHT` は最小値）、`stack_state.json` に各通知の高さを
    記録して、高さを積み上げる方式でスタック位置を計算するようにした（5章）。

### 2026-09-23: 質問内容の表示・スタックの詰め直し・クリック時の縮小アニメーション

- **理由**: 本文が `cwd` だけで何を聞かれているか分からない、閉じた通知の跡に隙間が残る、
  クリックしても押した手応えが無い、という使い勝手の問題に対応。
- **変更内容**:
  - 本文を Hook ペイロードの `tool_name` / `tool_input` / `message` から組み立てるようにした（4章）。
  - `stack_state.json` を「空いた最小の段番号」から「到着順のリスト」に変更し、各通知が
    定期的に自分の順位を読み直して上へ詰めるようにした。常駐プロセスは引き続き持たない（5章）。
  - クリック（✕ボタン含む）時に少し縮んでから閉じるアニメーションを追加。前面化は縮小後に行う。
  - 本文が複数行になるため `HEIGHT` を 96 → 110 に変更。

### 2026-09-22（3回目）: ~/.claude/notifier へ移設し、全プロジェクトで有効化

- **理由**: StudyOfStreamlit の `.claude/settings.json`（プロジェクト設定）に登録していたため、
  そのプロジェクトでしか通知が出なかった。
- **変更内容**: 一式を `~/.claude/notifier/` に移し、Hookをユーザー設定 `~/.claude/settings.json` に
  登録した。`~/.claude` は非公開リポジトリ（claude-config）で Git 管理する。StudyOfStreamlit 側の
  notifier・Hook登録・説明用skillは削除（Git履歴に残る）。

### 2026-09-22（2回目）: PySide6製カード型ウィンドウとスタック配置を復元

- **理由**: `osascript display dialog` は標準ライブラリのみで動く反面、見た目が標準OSダイアログに
  限定され、複数通知のスタック配置も失われていた。オリジナルで作り込んだアニメーション背景の
  カード型ウィンドウとスタック配置を、常駐デーモン化はせずに復元したい、という要望に対応。
- **変更内容**: 表示部分を `notify_window.py`（PySide6）に分離し、`hook_notify.py` は
  スタックの `.venv/bin/python3` を直接起動する薄いアダプタのままとした。常駐デーモンや
  TCP IPCは復活させず、通知1件=使い捨てプロセスの構成を維持。複数プロセス間のスタック配置は、
  デーモンによる一元管理の代わりに `stack_state.json` への排他制御付きアクセスで実現した。
  依存関係の管理には `uv`（`pyproject.toml` / `uv.lock`）を導入し、`notifier/` 配下に
  閉じた venv を持つ。
- **前回からの変更点（差分）**:
  - `SOUND_NAME` 定数は `hook_notify.py` から `notify_window.py` に移動。
  - フォーカスを奪わない（`activate()` を呼ばない）点は前回のosascript版と異なる改善点。
  - スタック配置は「空いた最小の段」に割り当てるのみで、通知が閉じられても既存通知の詰め直しは
    行わない（常駐デーモンが無いため）。旧デーモン方式は毎回全通知を再配置していた。

### 2026-09-22: 常駐デーモン方式を廃止し、ダイアログ方式へ移行

- **理由**: 常駐デーモン化の根拠は「同期実行のHookをQtアプリの起動でブロックしないため」
  だったが、Hookは全て `async: true` で登録されており根拠が失われていた。また、デーモンが
  停止していると通知が一切届かない（実際に 2026-08-12 以降停止していた）、依存パッケージ
  （PySide6, psutil, pyobjc）とvenvの維持が必要、など保守コストが高かった。
- **変更内容**: `notifier/` パッケージ（デーモン・TCP IPC・通知ウィンドウ・スタック配置・トレイUI）、
  `packaging/`、`requirements.txt` を削除し、`hook_notify.py` 単体で `afplay` + `osascript` の
  ダイアログを表示する方式に変更。`Notification` の `permission_prompt` Hook の登録を削除。
- **失った機能**: 通知のスタック配置、フォーカスを奪わない表示、トレイメニューからの設定変更、
  通知音の繰り返し再生、Windows対応。（スタック配置とフォーカスを奪わない表示は、上記
  「2026-09-22（2回目）」で復元済み。）
- 旧デーモン方式の仕様・変更履歴はコミット `89d5382` 時点の本ファイルを参照。
