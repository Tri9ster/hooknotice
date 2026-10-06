# 技術解説

2026-09-25 時点（質問・計画の Markdown 表示追加後）の実装に基づく。多言語対応（4.10）は 2026-09-28 に追記。

## 1. 全体像

hooknotice は、Claude Code が許可確認や質問で止まったときに、画面右下にカード型の通知ウィンドウを出す
macOS 用のツールです（Windows は対応コードのみで未検証）。構成要素は次のとおりで、常駐プロセスは持ちません。

| 要素 | 役割 | 依存 |
| --- | --- | --- |
| プラグインの `hooks/hooks.json` | Claude Code から `hook_notify.py` を呼ぶ（`${CLAUDE_PLUGIN_ROOT}` で本体の場所を指す） | — |
| `hook_notify.py` | Hook のペイロードを読み、ウィンドウを起動する薄いアダプタ。許可待ちでは回答を待って Claude Code に返す | 標準ライブラリのみ（システムの Python で動く。`python3` → `python` → `py -3` の順に試す） |
| `notify_window.py` | 通知ウィンドウ本体。通知1件につき1プロセス | PySide6（パッケージは `PySide6-Essentials`。`uv` で管理する venv。プラグインなら `<DATA>/venv`） |
| `hooknotice_config.py` / `config.json`（プラグインなら `<DATA>/config.json`） | 設定（通知の横幅、コマンドを改行する文字数、場面ごとのオン/オフ）の読み書きと、通知する場面の一覧（`SCENES`） | 標準ライブラリのみ |
| `messages.py` | 画面・ダイアログの文言と Claude に返す拒否の理由の辞書（`ja` / `en`）と、使う言語の決定（`tr` / `language`） | 標準ライブラリのみ |
| `settings_window.py` | 設定画面。通知の ⚙ とスラッシュコマンド `/hooknotice:settings`（プラグインの `skills/settings`）から開く | PySide6 |
| `platform_support.py` | OS ごとに違う処理（venv のパス、起動方法、ファイルロック、プロセスの生存確認、状態ファイルの場所、通知音、前面化）。上の2つから使う | 標準ライブラリのみ |

`hook_notify.py` を標準ライブラリだけで書いているのは、Claude Code がどの Python で Hook を起動しても
動くようにするためです。PySide6 が要るのはウィンドウ側だけで、venv の `bin/python3` を絶対パスで起動します
（venv が無いときや依存が更新されたときは、`uv sync --frozen` を実行してよいかを OS のダイアログで確認する。自動では実行しない。
uv が無いときは、Hook を動かしている Python の `venv` と `pip` で準備することもダイアログから選べる）。

Hook の起動に使う Python の名前は OS や入れ方で違う（macOS は `python3`、Windows の python.org 版は `python` と `py`）。
ラッパーのスクリプトは置かず、`hooks.json` のコマンドを `python3 ... || python ... || py -3 ... || true` とつないでいる。
`hook_notify.py` は常に exit 0 で終わるので、次の候補へ進むのは起動できなかったときだけで、二重に動くことはない。

プラグインの本体（`CLAUDE_PLUGIN_ROOT`、`~/.claude/plugins/cache/hooknotice/hooknotice/<版>/`）は更新のたびに別のフォルダに
入れ替わるため、書き込むもの（venv と `config.json`）は更新しても残る `CLAUDE_PLUGIN_DATA`
（`~/.claude/plugins/data/hooknotice-hooknotice/`）に置きます。この環境変数が無いとき（リポジトリから直接動かすとき）は、
従来どおり本体と同じフォルダの `.venv` と `config.json` を使います（`platform_support.plugin_data_dir` / `venv_dir`）。

## 2. 処理の流れ

```
Claude Code
  │ Hook 発火（stdin に JSON ペイロード）
  ▼
hook_notify.py --event <種別>
  ├─ ペイロードから表示内容を組み立てる（build_body / shell_command）
  ├─ 発火元アプリの bundle id を推定（__CFBundleIdentifier → TERM_PROGRAM）
  │
  ├─ 許可待ち以外、または AskUserQuestion / ExitPlanMode
  │     └─ spawn(): Popen(start_new_session=True) で切り離して起動 → すぐ exit 0
  │
  └─ 許可待ち（permission_request）
        └─ ask(): subprocess.run(... --actions --explain-input ...) で終了を待つ
              ├─ stdout "allow"   → {"hookSpecificOutput":{..."decision":{"behavior":"allow"}}}
              ├─ stdout "deny"    → {..."decision":{"behavior":"deny","message":...}}
              └─ "dismiss"・空など → 何も出力しない（Claude Code の通常ダイアログに任せる）
                 いずれも exit 0

notify_window.py（1通知 = 1プロセス）
  ├─ テーマ適用 → レイアウト構築 → 高さ決定
  ├─ stack_state.json に自分(pid, 高さ)を追加し、位置を決めて表示・通知音
  ├─ 250ms ごと: スタック位置の再計算 / 親(Hook)の生存確認
  ├─ 「解説」: QProcess で claude -p を非同期起動 → Markdown を表示 → 高さ再計算
  └─ 閉じる: 結果を stdout に1行出力（--actions 時）→ イベントループ終了 → スタックから削除
```

## 3. Claude Code の Hook との連携

### 登録内容

| Hook | マッチャー | 実行方式 | `--event` |
| --- | --- | --- | --- |
| `PermissionRequest` | `*` | **同期**（`timeout: 600`） | `permission_request` |
| `Notification` | （なし＝全12種） | async | `notification` |
| `Stop` | （なし） | async | `stop` |
| `StopFailure` | （なし） | async | `stop_failure` |
| `SubagentStop` / `TaskCompleted` / `TeammateIdle` | （なし） | async | `subagent_stop` / `task_completed` / `teammate_idle` |
| `UserPromptSubmit` | （なし） | async | `prompt_submit`（送信時刻を `prompts.json` に記録するだけ） |
| `SessionStart` | （なし） | 同期（timeout 10） | `session_start`（venv を確認し、準備が必要なら `--setup` を切り離して起動。確認ダイアログを出す） |

通知は既定で約6秒（`delay_seconds`）待ってから出す。設定で「文字数から自動」（`delay_mode: reading`）にすると、
本文の文字数と読む速さ（`reading_cpm`）から待ち時間を決める（`Config.delay_for`。`delay_seconds` は最低値、上限120秒）。許可待ちは、待つ間にターミナル側で答えられたら出さない
（Claude Code は答えられても Hook を終了させないので、会話の記録 `transcript_path` にツールの結果が書かれたかで
確かめる。表示後に答えられた場合も同じ確認で通知を閉じる）。ほかの通知は、待つ間に同じセッションで
プロンプトが送られていれば出さない。

通知するかどうかは Hook 側で `config.json` の `notify` を見て決める（オフなら何もせず終了）。
settings.json は変えずに、設定画面から場面ごとに切り替えられる。

### 許可を返す仕組み

`PermissionRequest` Hook は、stdout に次の JSON を出すと Claude Code の許可判断を代行できます
（公式ドキュメント hooks の「PermissionRequest decision control」）。

```json
{"hookSpecificOutput": {"hookEventName": "PermissionRequest",
                        "decision": {"behavior": "allow"}}}
```

- `"deny"` のときは `message` が Claude に伝わる（Claude は拒否理由を受け取って作業を続ける）。
- 何も出さずに exit 0 すると「決定なし」になり、通常の許可ダイアログで答える。
- **async の Hook の出力は無視される。** 決定を返すには同期にする必要がある（このため許可待ちだけ同期）。
- タイムアウト（既定 600 秒）すると Hook はキャンセルされ、出力は捨てられる。
- settings の deny / ask ルールは Hook の allow より優先される。

### 実機で分かった挙動（2026-09-24、VS Code 拡張）

- 同期 Hook の実行中も、VS Code 側の許可ダイアログは**同時に表示される**。どちらで答えてもよい。
- auto モードで許可確認自体が起きない操作では、`PermissionRequest` Hook は発火しない。
- `AskUserQuestion` と `ExitPlanMode` も `PermissionRequest` を通る。ここで deny を返すと質問そのものが
  拒否されるため、この2つはボタン無しの通知にしている（`NO_ACTION_TOOLS`）。

## 4. 通知ウィンドウ（`notify_window.py`）の内部

### 4.1 ウィンドウ

- `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint`、背景透過、角丸は `paintEvent` で描く。
- `Qt.Tool` は使わない。別プロセスの複数通知で最前面の重なり順が不安定になったため
  （Dock アイコンが一瞬出るのは許容）。
- フォーカスを奪わない（`activate()` を呼ばない）。
- 背景は `QLinearGradient` のハイライト帯が流れるアニメーション（40ms 間隔）。色相・角度に乱数の揺らぎを
  入れ、通知ごとに少しずつ見た目が変わる。

### 4.2 高さの決め方（`_fit_height`）

幅は設定の `width`（既定 600px。起動時に1回読む）、高さは内容で決まる。

1. コマンド欄・解説欄（`QTextEdit` / `QTextBrowser`）は、ドキュメントを複製して幅を設定し、
   折り返した全文の高さに固定する（`_fit_text_edit`）。
2. レイアウト全体の高さを求め、`HEIGHT`（110）を下限、「画面の高さ − 2×MARGIN」を上限にする。
3. 上限を超えた分は **解説欄（最小 80px）→ コマンド欄（最小 40px）** の順に縮め、その欄をスクロールさせる。

注意: 高さ計算にはフォントサイズが効くので、スタイルシート（テーマ）はレイアウト構築**前**に当てる。

### 4.3 複数通知の積み上げ（`StackSlot`）

常駐プロセスが無いので、複数の通知プロセスが1つの JSON ファイルで位置を調整する。

- ファイル: `platform_support.state_dir()` の `stack_state.json`（macOS は `~/Library/Application Support/hooknotice/`）
- 中身: 表示中の通知の到着順リスト `[{"pid": 123, "height": 146}, ...]`。`platform_support.locked_state` で排他制御
  （macOS は `fcntl.flock`）。
- 起動時に末尾へ追加（`acquire`）、終了時に削除（`release`、`aboutToQuit` に接続）。
- 最新の通知が常に右下で、古い通知ほど上に並ぶ。各通知は 250ms ごとに最新の通知から自分までの高さを
  読み直し（`heights_newest_to_self`）、位置が変われば 200ms のアニメーションで移動する。新しい通知が来れば
  上へずれ、下の通知が閉じれば下へ詰まり、下の通知が伸びれば（解説表示）上へずれる。
- 画面上端を超える分は1列左に折り返す（`_stack_position`）。
- 異常終了したプロセスの記録は `platform_support.pid_alive` の生存確認で回収する。

### 4.4 回答の返し方（`--actions`）

- ボタン行: 左端に「解説」、右寄せで「キャンセル」「OK」。
- 閉じるときに結果を stdout に1行出す: OK → `allow`、キャンセル → `deny`、✕・本体クリック・コマンド欄クリック → `dismiss`。
- 親（待っている Hook）が先に終わったら何も出さずに閉じる。判定は `os.getppid()` が起動時と変わったか、
  **または pid 1 か**（Hook が先に死んでからウィンドウが起動した場合、起動時点で既に launchd の子になっている）。
  監視する pid は Hook が `--parent-pid` で渡す（省略時は `os.getppid()`）。Windows の venv の `python.exe` はランチャーで、
  ウィンドウから見た親 pid がランチャーになり、Hook が終わっても生き続けるため、親 pid に頼れない。

### 4.5 配色（テーマ）

- `QApplication.styleHints().colorScheme()` で macOS の外観（Light / Dark）を取得。判定不能ならダーク。
- 色は `THEMES["dark" | "light"]` にまとめ、文字列の値だけを `STYLE_SHEET` テンプレートに差し込む。
  `QColor` の値（ライトの縁取り、解説中のコード背景）は描画コードで直接使う。
- `colorSchemeChanged` に `_apply_theme` を接続し、表示中の通知も追従する。
- ハイライト色は「色相」と「テーマの範囲内での彩度・明度の位置（0〜1）」を最初に乱数で決めておき、
  テーマ適用時に色を作る。これで外観が切り替わっても同じ通知の個性が保たれる。

### 4.6 解説ボタン

- `hook_notify.py` が操作内容（ツール名、作業ディレクトリ、`tool_input` の JSON。8000文字で切り詰め）を
  `--explain-input` で渡す。
- claude の実行ファイルは `CLAUDE_CODE_EXECPATH`（Hook に渡される環境変数。VS Code 拡張では同梱の
  バイナリを指す）→ PATH 上の `claude` の順に探す。無ければボタンを出さない。
- 起動コマンド（`QProcess` で非同期。UI は止まらない）:

  ```
  claude -p --model sonnet --tools "" --setting-sources "" --no-session-persistence \
         --system-prompt <EXPLAIN_PROMPT> <操作内容>
  ```

  | 指定 | 理由 |
  | --- | --- |
  | `--tools ""` | 解説のためにツールを実行させない |
  | `--setting-sources ""` | ユーザー設定（= この hooknotice の Hook）を読ませず、通知の再帰を防ぐ |
  | 環境変数 `HOOKNOTICE_DISABLED=1` | 同上の二重の安全策 |
  | 作業ディレクトリ = 一時ディレクトリ | 作業中プロジェクトの CLAUDE.md を読み込ませない |
  | `closeWriteChannel()` | stdin を閉じないと入力待ちで約3秒遅れる |
  | `--bare` は**使わない** | OAuth・キーチェーンを読まず、API キーが無いと認証できない |

- 生成には10〜15秒かかる（実測: Bash の例で 14.4 秒、Edit の例で 9.6 秒）。生成中はボタンを無効化し、
  閉じたら子プロセスを kill する。失敗したら理由を表示してもう一度押せるようにする。
- 表示は `QTextBrowser.setMarkdown()`。Qt の Markdown 表示は 340px のカードには大きく、コードも目立たない
  ため `_polish_markdown` で整える: 見出しを 12〜14px に（Qt が付ける文字サイズの段階 `FontSizeAdjustment` は 0 に
  戻す）、`code` とコードブロックを Menlo 11px にして背景を付け、
  コードブロックの折り返し禁止（`NonBreakableLines`）を解除、リストの字下げを 14px に。
- 表示後に `_fit_height` → `_init_gradient_params`（グラデーションの終点を新しい高さに合わせる）→
  `StackSlot.update_height` の順に呼ぶ。

### 4.7 コマンド欄の整形（`hook_notify.py` の `format_command` / `format_powershell_command`）

Bash と PowerShell の許可待ちでは、コマンド欄に渡す前にワンライナーを複数行に整形する。表示専用で、解説に渡す内容と
Claude Code に返す決定は元のコマンドのまま。ツール名から整形する関数を引く表が `COMMAND_FORMATTERS` で、
`shell_command` がこれを使う。まず Bash（`format_command`）。

1. `_scan_command` が1文字ずつ走査し、トップレベルの語と演算子（`;` `&&` `||` `|`）の列にする。
   - 語は**元の文字列の部分文字列**をそのまま使う（トークンを組み立て直さない）ので、引用符や中身は変わらない。
   - 引用符（`'` `"` `$'…'` `` ` ``）は閉じ引用符まで読み飛ばし、`(` `{` で深さを増やし `)` `}` で減らす。
     深さ 0 のときだけ空白と演算子を区切りとみなす。`>|` の `|`、`2>&1` や `&` は区切りにしない。
   - 解析に自信が持てない書き方（ヒアドキュメント、既に複数行、閉じていない引用符・括弧、コメント、`;;`、`|&`）は
     `_Unsupported` を投げ、元のまま表示する。
2. `;` でまとまりに、`&&` / `||` で要素に、`|` で段に分けて組み立てる。
   - `;` は行末に残し、まとまりの間に空行。`&&` / `||` は行末に残して ` \`。
   - 要素が設定の `command_line_limit`（既定は幅から自動計算。600px で 83 文字）を超えるときだけ、
     `_format_element` が代入（`NAME=値`）を1行ずつ、
     本体を2文字字下げ、パイプの2段目以降を `  | …` に分ける。
   - 語の間の複数の空白は1つにまとめる（引用符の外なので意味は同じ）。
3. 最後に `/bin/bash -n -c <整形結果>` で構文を確かめ、通らなければ元のまま返す。
   `-n` は読むだけで実行しない。コマンドを `eval` して比べる方法は、許可前のコマンドが実行される恐れがあるので使わない。

開発時の検証では、元と整形後を `f() {…}; declare -f f` として bash に**定義だけ**させ、bash が正規化した
関数定義が一致することを確認した（手元で用意した固定の文字列でのみ行う。実行時には使わない）。

PowerShell（`format_powershell_command`）は、括弧の中のパイプも開いて字下げするので、平らな列ではなく木にする。

1. `_parse_powershell` が再帰下降で木を作る。要素は `("text", 文字列)`・`("op", ; | && ||)`・
   `("group", 開き, 中身, 閉じ)`・`("dq", 部品の列)`。
   - text は**元の文字列の部分文字列**（空白も含めてそのまま）。`'…'`・`` ` ``+1文字・`${…}` は text の一部として読み飛ばす。
   - `(` `$(` `@(` `{` `@{` `[`（`_PS_CLOSERS`）で group を開いて再帰し、閉じ括弧が対応しなければ `_Unsupported`。
   - `"…"` は dq にし、中の `$(` だけをコードとして再帰する（部品は文字列か group）。
   - 解析に自信が持てない書き方（既に複数行、ヒアストリング、コメント、`--%`、閉じていない引用符・括弧）は `_Unsupported`。
2. `_ps_block` が文の並びを行にする。`;` で文に、`&&` / `||` で要素に、`|` で段に分け（`_ps_split`）、
   段ごとに1行、2段目以降は `_PS_INDENT`（4文字）深く置く。トップレベルは文の間に空行、括弧の中は改行だけ。
3. `_ps_inline` は要素を元のままつなぐ。group だけ `_ps_group` に渡し、直下に `|` があれば
   「開き・改行・`_ps_block`（1段深く）・改行・閉じ」にする。`[ ]` と `;` を含む `( )` は開かない。
   閉じ括弧の字下げは、開き括弧がある行の字下げ（引数の `indent`）。
4. 最後に、整形結果と元のコマンドから空白を除いた文字列を比べ、違えば元のまま返す。
   bash の `-n` に当たる確認だが、PowerShell は macOS に無く、起動も遅い（Hook を待たせる）ので、構文チェックには使わない。
   そのぶん、行の区切りは PowerShell が必ず次の行へ続ける位置（`|`・`&&`・`||`・開き括弧の後ろ、`;` の後ろ）だけにしている。

### 4.8 設定ファイル（`hooknotice_config.py`）

- `config.json` の各キー（`language`・`width`・`command_line_limit`・`notify`・`sound`・待ち時間の3つ）を `load_config()` で読む。無い・壊れている・範囲外の値は既定値
  （例外を出さない。Hook は何があっても Claude Code を止めてはいけないため）。
- `bool` は `int` の一種なので、`true` を 1 と解釈しないよう除外している。
- 文字数の自動計算 `auto_line_limit(width) = floor((width − 34) / 6.61) − 2`:
  6.61px は Menlo 11px の1文字幅（offscreen の `QFontMetricsF` で実測）、34px は余白 20・枠 8・スクロールバー 6。
  `hook_notify.py` は Qt を使えない（標準ライブラリのみ）ので、実測値を定数で持つ。
- 通知は1件ごとに新しいプロセスで起動し、そのたびに設定を読むので、ファイルの変更（設定画面の保存を含む）が
  次の通知から反映される。設定画面（`settings_window.py`）は 2026-09-27 に追加した。

### 4.9 質問・計画の承認待ちの本文（`--markdown`）

- `AskUserQuestion` / `ExitPlanMode` の `tool_input` には要約用のキー（`command` など）が無く、以前は JSON がそのまま
  本文になっていた。`hook_notify.py` の `tool_markdown` が Markdown に組み立てて `--markdown` で渡す。
  - 質問: `**[header]** question` + 番号付きの選択肢 `**label** — description`。`preview` は番号付きリストの項目の中に
    入れるため3文字字下げしたコードブロックにし、フェンスは preview 内の最長のバッククォート列より1つ長くする（`_code_fence`）。
  - 計画: `plan` をそのまま（もともと Markdown）。
  - 型が合わない値は飛ばし、何も組み立てられなければ従来の本文にフォールバックする。
- `notify_window.py` は解説欄と同じ `_new_markdown_view` / `_set_markdown`（= `setMarkdown` + `_polish_markdown`）で表示する。
  解説欄と違い、クリックは本体クリック扱い（`viewport().installEventFilter`）。質問にはアプリ側で答えるため。
- 高さの調整では、解説欄と同じく縮めてよい欄（最小 80px）に含める。

### 4.10 多言語対応（`messages.py`）

- **言語の決め方**: `messages.language()` がプロセスごとに1回だけ決めてキャッシュする。`config.json` の `language` が
  `ja` / `en` ならそれ、`auto`（既定）なら `platform_support.system_language()`。
  - macOS は `~/Library/Preferences/.GlobalPreferences.plist` の `AppleLanguages[0]` を `plistlib` で読む。Hook の環境では
    `LANG` が空だったり `en_US.UTF-8` だったりして OS の表示言語と一致しないため、環境変数は最後の手段にした。
    `defaults read -g AppleLanguages` でも取れるが、Hook ごとにサブプロセスを起動したくないのでファイルを直接読む。
  - Windows は `GetUserDefaultUILanguage() & 0x3FF == 0x11`（LANG_JAPANESE）。実機では未確認。
  - Qt の `QLocale.system()` は使わない。`hook_notify.py` は Qt を読み込めないので、3つのプロセスで判定がずれないよう
    同じ関数を使う。
- **依存の向き**: `messages` → `hooknotice_config` → `platform_support`。`messages` が `load_config` と
  `system_language` を使うため、下の2つは `messages` を読み込まない（循環させない）。文言が必要な
  `platform_support.ask_dialog` の Windows 用の書き添えは、引数 `button_hints` で呼び出し側が渡す。
- **キーの規約**: 用途別の接頭辞 `title.*`（通知のタイトル。`title()` が `"Claude Code: "` を付ける）/ `body.*`（本文の定型句）/
  `button.*` / `window.*` / `explain.*` / `deny.*`（Claude に返す拒否の理由）/ `setup.*`（準備のダイアログ）/
  `dialog.*` / `settings.*` / `group.<分類>` / `scene.<key>.label|desc`。差し込む値は `str.format` の名前付き
  （`{agent}` など）。英語と日本語で差し込む値の名前をそろえる。
- **定数を読み込み時に翻訳しない**: `EVENT_TITLES` などはキーの対応表にし、使う時点で `tr()` を呼ぶ。
  読み込み時に `tr()` を呼ぶと、`config.json` を読む前後関係やテストで言語を差し替えられなくなるため。
- **解説の言語**: システムプロンプト（`explain.prompt`）ごと言語別に持ち、見出し（ステップ別の詳細解説 / 注意点 / まとめ ↔
  Step-by-step details / Cautions / Summary）もその言語で指定する。「日本語で」の一語だけを差し替える方式は、
  見出しが日本語のまま残るので採らなかった。
- **翻訳しないもの**: Claude Code から届く内容（応答・コマンド・計画・質問と選択肢）、ボタンの結果値、コード中のコメント・
  docstring・内部用の例外メッセージ（`_Unsupported` の理由など、画面に出ないもの）。
- **設定画面**: 「言語」のコンボの項目名は、どの言語で表示していても読めるよう「日本語」「English」と各言語で書く。
  設定画面自体は起動時の言語のまま（開き直すと切り替わる）。表示中に全ウィジェットを作り直す手間に見合わないため。
- **新しい言語の足し方**: `MESSAGES` に言語コードの辞書を足す → `SUPPORTED_LANGUAGES` と `hooknotice_config.LANGUAGES` に
  加える → `system_language()` の判定に加える → 設定画面のコンボの項目名を足す。キーの欠け・差し込む値の違いは、
  6章の確認スクリプトで見つけられる。

## 5. 主な設計判断

- **前面アプリの判定は通知を出す直前にする**: 待ち時間のあいだに別のアプリへ移った場合は通知したいので、`main` の待ち時間のあと、
  `notify` の前で `host_app_focused()` を見る。最前面の取得は osascript ではなく `lsappinfo`（自動操作の許可が要らず速い）。
  比較するのは bundle id だけなので、同じアプリの別ウィンドウ・別タブは区別できない（割り切り）。

| 判断 | 理由 | 捨てた案 |
| --- | --- | --- |
| 常駐デーモンを持たない | デーモンが止まると通知が一切出ず、実際に長期間止まっていた | 旧デーモン + TCP IPC 方式 |
| 1通知 = 1プロセス、位置はファイル共有 | デーモン無しで積み上げと詰め直しを実現できる | — |
| 許可待ちだけ同期 Hook | 決定を返せるのは同期 Hook のみ。他は Claude を止めない async のまま | 全部同期 |
| ✕・本体クリックは「決定なし」 | ターミナル側で答える逃げ道を残す | ✕ = 拒否 |
| 解説は `claude -p` を使う | ユーザーの Claude Code のログインをそのまま使え、API キー管理が不要 | Anthropic API を直接呼ぶ |
| 解説は通知カード内に表示 | 読んでそのまま OK / キャンセルできる | 別ウィンドウ |
| コマンドの整形は空白・改行・`\` だけ | 許可の判断材料なので、表示と実行される内容をずらさない（引用符も足さない） | 読みやすさ優先で書き換える |
| `&&` / `;` は行末に残す | 条件付き実行か無条件かが読み取れる。そのままシェルとして正しい | `&&` を消す、行頭に置く |
| 設定は JSON ファイル（設定画面はその編集役） | 1通知1プロセスなので再起動なしで反映される | 常駐して設定を持つ |
| 文言は Python の辞書（`messages.py`） | `hook_notify.py` は標準ライブラリだけで動かす必要があり、gettext の .mo のビルドも要らない。2言語なら辞書で十分 | gettext / Qt Linguist |
| 言語の既定は `auto`（OS の言語） | 日本語の利用者は何もしなくても従来どおり日本語、それ以外は英語で使える | 既定 `ja` 固定 |
| 改行する文字数は幅から自動計算 | 幅を変えたら文字数も追従しないと広げた幅が活きない。指定したときだけ優先 | 幅と文字数を独立に設定 |

## 6. 動作確認の方法

実機を使わない確認は、`QT_QPA_PLATFORM=offscreen` でウィンドウを作り `grab().save()` で画像にする方法が
有効。`StackSlot` の代わりに `heights_newest_to_self` / `update_height` だけを持つ仮のクラスを渡せば、
状態ファイルに触れずに描画できる。

```python
import os, sys, random
random.seed(1)                      # グラデーションの乱数を固定すると、変更前後の画像をバイト比較できる
sys.path.insert(0, os.getcwd())     # hooknotice/ で実行すること（別の場所だと import に失敗する）
import notify_window as nw
from PySide6.QtWidgets import QApplication
nw._current_theme = lambda: "light" # テーマを強制
app = QApplication([])
class Slot:
    def heights_newest_to_self(self): return [100]
    def update_height(self, h): pass
w = nw.NotificationWindow("Claude Code: 許可待ち", "", "説明", "ls -la", "", Slot(),
                          actions=True, explain_input="dummy")
w.show(); w.grab().save("out.png")
```

言語を切り替えて描画するときは、`notify_window` を読み込む前に `import messages; messages._language = "en"` とする
（`config.json` を書き換えずに済む）。日英の文言の欠け・差し込む値の違いは次で確かめる。

```python
import string, messages as m
ja, en = m.MESSAGES["ja"], m.MESSAGES["en"]
names = lambda t: {f[1] for f in string.Formatter().parse(t) if f[1] is not None}
print(set(ja) ^ set(en), [k for k in ja if names(ja[k]) != names(en[k])])  # どちらも空なら OK
```

Hook としての確認は、ペイロードを stdin に流して `hook_notify.py` を直接起動する。

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"ls","description":"テスト"}}' \
  | python3 plugins/hooknotice/hook_notify.py --event permission_request
```

PowerShell の整形は、`plugins/hooknotice` で次のように確かめる（macOS でも動く。`tool_name` を `PowerShell` にした
ペイロードを上の方法で流せば、コマンド欄の見た目も確かめられる）。

```python
import hook_notify as h
print(h.format_powershell_command('"n=$(($top | Measure-Object).Count)"; $top | ForEach-Object { $_.Name }'))
for raw in ("Get-Content a.txt # c | x", '"unclosed | x', "a ;; b | c", "cmd --% a | b"):
    assert h.format_powershell_command(raw) == raw  # 解析できない書き方は元のまま
```

実機の外観切り替えは次で行える（テスト後は元に戻すこと）。

```bash
osascript -e 'tell application "System Events" to tell appearance preferences to set dark mode to false'
```
