# hooknotice

[English](README.md) | **日本語**

Claude Codeが許可確認（Permission Request）や質問待ちで停止した時に、通知音を鳴らして
グラデーション背景のカード型ウィンドウを表示する Claude Code のプラグインです。実体は Hooks と
`hook_notify.py` / `notify_window.py` の2ファイルで、常駐デーモンやプロセス間通信は不要です。
詳細な仕様、開発者向けの技術解説・開発記録・失敗の記録は [docs/](docs/README.md) を参照してください。

## できること

- 許可待ち・質問待ちで停止したときと、作業が終わったときに、通知音が鳴り、アニメーションするグラデーション
  背景のカード型ウィンドウが画面右下に表示されます。
- 本文には **Claude Code が尋ねている内容**が省略されずに表示されます。
  - コマンド実行の許可待ちでは、Claude が書いたコマンドの説明が上に、コマンド全文が等幅フォントで
    下に表示されます（説明が無い場合はコマンドのみ）。
  - 長いワンライナーは、`;` や `&&` の位置で改行し、環境変数の前置きやパイプも1行ずつに分けて表示します。
    変えるのは空白と改行だけで、コマンドの意味は変わりません（解析できない書き方はそのまま表示します）。
  - それ以外の許可待ちは `Edit: <ファイルパス>` のようなツール名と対象、質問待ちは
    通知メッセージです。
  - 作業完了（「Claude Code: 作業完了」）では、Claude の最後の応答を整形して表示します
    （応答文が無いときは「作業が完了しました」）。Claude が応答を終えるたびに、すぐ表示されます。
- 表示は**日本語と英語**に対応しています。既定では OS の言語に合わせます（下の「言語」）。
- 配色は macOS の外観設定（ライト/ダーク）に合わせて変わります。表示中に切り替えた場合も追従します。
- カードの高さは内容に合わせて伸びます。画面に収まらないほど長いコマンドは、コマンド欄を
  ホイールでスクロールして読めます。
- **許可待ちの通知には「キャンセル」「OK」ボタンが付き、そのまま回答できます。**
  - **OK**: Claude Code に許可を返し、ツールが実行されます。
  - **キャンセル**: 拒否を返します。Claude には拒否された旨が伝わり、作業を続けます。
  - **✕**: 何も決めずに閉じ、通常どおりターミナル側の許可ダイアログで答えます。
  - ボタン付きの通知は、押し間違いで閉じないよう、本体（ボタン以外の部分）をクリックしても閉じません。
  - ターミナル側の許可ダイアログも同時に表示されるので、どちらで答えても構いません。
  - settings の deny ルールに当たる操作は、OK を押しても許可されません。
  - 自動許可（auto）モードなど、許可確認自体が行われない場合は通知も出ません。
  - 計画の承認（ExitPlanMode）では、OK / キャンセルの代わりに「計画を続ける」「都度確認で承認」
    「編集を自動許可で承認」「自動モードで承認」の4つのボタンが出ます。承認ボタンは、承認と同時に
    権限モードをそれぞれ default / acceptEdits / auto に切り替えます。計画の修正を文章で指示したいときは
    ✕ で閉じてターミナル側で答えてください。
  - 選択肢の質問（AskUserQuestion）では、本文に質問と選択肢（プレビュー付き）を整形して表示し、その下に
    選択肢のボタンが出ます。すべての質問で選んでから「回答する」を押すと、その回答で進みます
    （複数選択可の質問は複数オンにできます）。自由記述で答えたいときは ✕ で閉じてターミナル側で答えてください。
    選択肢の無い質問が含まれる場合はボタン無しの通知になり、クリックすると VS Code などが前面に出ます。
- **「解説」ボタン**を押すと、許可を求められている操作（コマンドや編集内容）の解説を Claude が書き、
  通知の中に表示します。10〜15秒ほどかかり、押すたびに Claude の利用枠を消費します。
  解説を読んでから、そのまま OK / キャンセルで答えられます。
- 通知は**約6秒放置されたときだけ**出ます（待ち時間は設定画面で変更、0 ですぐ表示）。
  設定画面で「文字数から自動」を選ぶと、長い計画や返答ほど長く待ちます（読む速さ＝1分あたりの文字数を指定）。
  - 許可待ち・選択肢の質問・計画の承認は、その間にターミナル（VS Code）側で答えれば通知は出ません。
    放置すると約6秒後にボタン付きで出て、そのまま答えられます。
  - 作業完了などは、その間に次のプロンプトを送れば出ません。画面を見ているだけで何も操作しない場合は出ます。
  - Claude Code 自身が待ってから出す通知（許可ダイアログの放置・応答待ちの放置・MCP の入力フォーム／URL）は、
    待ち時間を足さずにすぐ出します。
- 設定でオンにすると、**Claude Code を起動したアプリ（ターミナル・VS Code など）が最前面のときは通知を出しません**
  （既定はオフ。設定画面で変更。macOS のみ）。判定は表示する直前なので、待ち時間のあいだに別のアプリへ移っていれば出ます。
  許可待ちは、通常のダイアログで答えます。
- ウィンドウは**閉じるボタンを押すかクリックするまで自動では消えません**（許可待ちの通知は、
  ターミナル側で先に回答された・Hook がタイムアウト（600秒）した場合に自動で閉じます）。
- クリックすると少し縮むアニメーションの後に閉じます。閉じるボタン以外の部分をクリックした
  場合は、発火元（Claude Codeを実行しているターミナルやVS Code）も前面化されます。
- 複数の通知が同時に発生しても**重ならず縦にスタック表示**され、途中の通知を閉じると
  上の通知が下に詰まります（新しい通知が常に一番右下に出ます）。
- 対応OS: **macOS**。**Windows は対応コードを入れたが実機で未確認**（下の「Windows で使う場合」）。
  `hook_notify.py` は標準ライブラリのみ、`notify_window.py` は [uv](https://docs.astral.sh/uv/) で管理する
  PySide6(Qt) を使用。OS ごとの違いは `platform_support.py` にまとめています。

## セットアップ

必要なもの: macOS、`python3`（macOS 標準のもので可）、[uv](https://docs.astral.sh/uv/)（推奨。pip でも可、下記）。

Claude Code で、マーケットプレイスを追加してプラグインを導入します。

```
/plugin marketplace add Tri9ster/hooknotice
/plugin install hooknotice@hooknotice
```

（シェルからは `claude plugin marketplace add Tri9ster/hooknotice` と `claude plugin install hooknotice@hooknotice`。）
導入後、Claude Code を再起動（VS Code はウィンドウの再読み込み）します。Hooks はプラグインが登録するため、
**全プロジェクトで有効**になり、`settings.json` の編集は不要です。

**初回起動時: 準備の確認ダイアログ**。通知ウィンドウには PySide6（Qt for Python）が必要ですが、hooknotice は
自分からはダウンロードしません。導入後に初めて Claude Code を起動すると、「hooknotice の準備」ダイアログで
`uv sync --frozen` を実行してよいかを確認します（プラグインの更新で `pyproject.toml` / `uv.lock` が変わったときも同じです）。

- **実行する**: その場で `uv sync --frozen` を実行し、終わったら結果を表示します。次の通知から表示されます。
- **今はしない**: 何もしません。次に Claude Code を起動したとき、もう一度確認します。
- **今後確認しない**: 以後このダイアログを出しません（元に戻すには状態フォルダの `setup.declined` を削除します）。

環境（`venv`）は、プラグインの更新でも消えないデータフォルダ `~/.claude/plugins/data/hooknotice-hooknotice/venv`
に作られます。準備が済むまで、通知は表示されません。

uv が見つからないときは、uv の入れ方と pip で入れる手順をダイアログに表示します（「手順をコピー」でクリップボードにコピーできます）。

- **uv を入れる（推奨）**: `curl -LsSf https://astral.sh/uv/install.sh | sh`（または `brew install uv`、`pip3 install uv`）
  の後、Claude Code を起動し直して「実行する」を選びます。
- **uv を使わずに pip で入れる**:

  ```bash
  python3 -m venv ~/.claude/plugins/data/hooknotice-hooknotice/venv
  ~/.claude/plugins/data/hooknotice-hooknotice/venv/bin/pip install "PySide6-Essentials>=6.7"
  ```

  Python 3.10 以上なら最新版、macOS 標準の Python 3.9 なら 3.9 に対応する版（6.10 系）が入ります。

### 更新・アンインストール

- **更新**: 次のどちらかで最新版を GitHub から取り込み、その後 Claude Code を再起動します（VS Code はウィンドウの再読み込み）。
  - **Claude Code の中から**（ターミナル版の Claude Code。VS Code 拡張では `/plugin` が使えないので、下のターミナルの方法を使う）:
    `/plugin` を開き、「Marketplaces」タブで hooknotice を更新してから、「Installed」タブで hooknotice を更新します。
  - **ターミナルから**:

    ```bash
    claude plugin marketplace update hooknotice    # GitHub から最新のマーケットプレイスを取得
    claude plugin update hooknotice@hooknotice     # プラグインを最新版に更新
    ```

  `claude plugin list` の `Version` で、更新後の版を確かめられます。
- **アンインストール**: `/plugin uninstall hooknotice@hooknotice`（または `claude plugin uninstall hooknotice@hooknotice`）。
  データフォルダ（`venv` と `config.json`）も削除されます。状態フォルダ（`~/Library/Application Support/hooknotice/`）
  は残るので、不要なら手で削除してください。

### Windows で使う場合（未検証）

Windows の対応コードは入っていますが、実機では確認していません。

1. [uv](https://docs.astral.sh/uv/) を入れ（PowerShell で `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`）、
   準備の確認ダイアログで「実行する」を選びます（データフォルダ `%USERPROFILE%\.claude\plugins\data\hooknotice-hooknotice`
   に `venv\Scripts\python.exe` が作られます）。
   確認ダイアログは Windows の標準のメッセージボックスで出ます（ボタンは「はい / いいえ / キャンセル」に割り当て）。
2. プラグインの Hooks は `python3` で起動します。Claude Code は Windows でも Hook を Git Bash で実行しますが、
   `python3` が無い環境が多いため、通知が出ない場合は Git Bash で `python3` が動くか確認してください。
3. macOS との違い:
   - システムの通知音は `%SystemRoot%\Media`（通常 `C:\Windows\Media`）の WAV から選びます。任意の音声ファイルも WAV のみです。
   - 本体クリックでの発火元アプリ（VS Code 等）の前面化は行いません。
   - 表示中の通知一覧は `%LOCALAPPDATA%\hooknotice\stack_state.json` に置きます。
   - 長いコマンドの整形は Git Bash の `bash` で構文を確かめます。見つからなければ整形せずに表示します。
   - 等幅フォントは Consolas です。改行する文字数の自動計算は Menlo の文字幅のままなので、
     折り返し具合が合わなければ `config.json` の `command_line_limit` で調整してください。

## カスタマイズ

- **設定画面**: 通知の右上の **⚙** を押すか、Claude Code で **`/hooknotice:settings`** と入力すると開きます。
  表示の言語、通知する場面ごとのオン/オフ、通知を出すまでの待ち時間、通知音、通知の横幅、長いコマンドを改行する文字数を変えられます。
  「保存」を押すと次の通知から反映されます（Claude Code の再起動は不要）。「テスト通知」で今の幅を確かめられます。
- 通知する場面と既定値（Claude Code の Notification 12種と StopFailure を含む、すべての通知に対応しています）:

  | 分類 | 場面（`notify` のキー） | 既定 |
  | --- | --- | --- |
  | 回答が必要 | 許可待ち `permission_request`、選択肢の質問 `question`、計画の承認 `plan` | オン |
  | 回答が必要 | 許可ダイアログの放置 `permission_prompt`（許可待ちと重複） | オフ |
  | 作業の区切り | 作業完了 `stop`、エラーで停止 `stop_failure` | オン |
  | 作業の区切り | 応答待ちの放置 `idle_prompt`（作業完了と重複） | オフ |
  | MCP | 入力フォーム `elicitation_dialog`、URL を開く依頼 `elicitation_url_dialog` | オン |
  | MCP | 入力の完了 `elicitation_complete`、回答の送信 `elicitation_response` | オフ |
  | バックグラウンド | 入力待ち `agent_needs_input`、作業の完了 `agent_completed` | オン |
  | 利用上限 | 自動で再開 `quota_auto_resume_fired`、再開待ち `quota_auto_resume_stale`、待機の終了 `quota_auto_resume_disabled` | オン |
  | サブエージェント・タスク | サブエージェントの完了 `subagent_stop`、タスクの完了 `task_completed`、チームの仲間が待機 `teammate_idle` | オフ |
  | その他 | 認証完了 `auth_success` | オフ |

- 設定の実体は `~/.claude/plugins/data/hooknotice-hooknotice/config.json`（プラグインを更新しても残る）で、直接編集しても構いません。

  ```json
  {
    "width": 600,
    "command_line_limit": null,
    "notify": { "permission_prompt": false, "agent_completed": true }
  }
  ```

  | キー | 既定 | 範囲 | 意味 |
  | --- | --- | --- | --- |
  | `language` | `auto` | `auto` / `ja` / `en` | 表示の言語。`auto` は OS の言語が日本語なら日本語、それ以外は英語（下の「言語」） |
  | `width` | 600 | 280〜800（px） | 通知カードの横幅 |
  | `command_line_limit` | `null` | 20〜200（文字） | 長いコマンドを改行する文字数。`null` なら幅に合わせて自動で決まります（600px → 83文字、340px → 44文字） |
  | `notify` | 上の表 | 場面ごとの `true` / `false` | 書いていない場面は既定値になります |
  | `delay_seconds` | 6 | 0〜60（秒） | 通知を出すまでの待ち時間。この間に操作があれば出さない。0 ですぐ表示。`delay_mode` が `reading` のときは最低の待ち時間 |
  | `delay_mode` | `fixed` | `fixed` / `reading` | 待ち時間の決め方。`fixed` は `delay_seconds` のまま。`reading` は通知の本文（コマンド・計画・質問・Claude の返答など）の文字数から決める（空白・改行は数えない。上限120秒） |
  | `suppress_when_focused` | `false` | `true` / `false` | `true` のとき、Claude Code を起動したアプリが最前面なら通知を出さない（macOS のみ） |
  | `reading_cpm` | 600 | 100〜3000（文字/分） | `reading` のときの読む速さ。例: 600 なら 300字で30秒 |
  | `sound` | `{"enabled": true, "source": "system", "system": "Glass", "file": ""}` | — | 通知音。`source` は `system`（システムの音、`system` に名前）か `file`（`file` にパス） |
  | `explain` | `{"model": "sonnet", "effort": "low"}` | `effort`: `low` / `medium` / `high` / `xhigh` / `max` | 「解説」に使うモデルと effort。`model` は `claude --model` にそのまま渡します。設定画面は無く、ファイルで変えます。解説は届いた分から順に表示されます |

  ファイルが無い・JSON として読めない・範囲外の値のときは既定値を使います。
- **言語**: 通知・ボタン・設定画面・準備のダイアログ、「解説」で Claude が書く解説文、キャンセル時に Claude に返す
  拒否の理由が、選んだ言語になります。`auto`（既定）は、macOS では「システム設定 > 一般 > 言語と地域」の
  「優先する言語」の先頭、Windows では表示言語で決めます（取れない場合は環境変数 `LANG` など）。
  設定画面で変えると次の通知から反映されます（設定画面自体は開き直すと切り替わります）。
  Claude の応答・コマンド・計画など、Claude Code から届く内容はそのまま表示します（翻訳はしません）。
  英語で「文字数から自動」の待ち時間を使う場合、読む速さは 1000〜1200 文字/分程度が目安です（空白は数えません）。
- **通知音を変える**: 設定画面の「通知音」で、鳴らすかどうか、システムの音（macOS は `/System/Library/Sounds`、
  Windows は `%SystemRoot%\Media` の中から選択）か任意の音声ファイルかを選べます。「試聴」で確かめられます。
  任意のファイルが見つからなくなった場合は、選んであるシステムの音を鳴らします。
- **一時的に通知を止める**: 環境変数 `HOOKNOTICE_DISABLED=1` を設定して Claude Code を起動します。
- **その他の表示位置・サイズを変える**: `notify_window.py` の `HEIGHT`（最小の高さ）/ `MARGIN` / `GAP` を編集します
  （このリポジトリを clone して。下の「開発」）。

## 動作確認

- 設定画面（`/hooknotice:settings`）で「テスト通知」を押すと、通知音が鳴り、グラデーション背景のカードが右下に出ること。
- 許可が必要なコマンドを Claude に頼み（例:「新しいシェルで `ls` を実行して」）、約6秒答えずに待つと、
  「キャンセル」「OK」付きの許可待ちの通知が出ること。
- 同じような依頼を何度か行うと、ウィンドウが重ならず縦に並ぶこと。ウィンドウ（閉じるボタン以外の部分）を
  クリックすると、少し縮んでから閉じ、VS Code やターミナルが前面に出ること。上に並んでいた通知が下に詰まること。

## トラブルシューティング

- **ウィンドウが出ない**:
  - プラグインが有効か（`/plugin` の「Installed」タブ）、導入後に Claude Code を再起動したかを確認してください。
  - `~/.claude/plugins/data/hooknotice-hooknotice/venv` が存在するか確認してください。無ければ Claude Code を
    起動し直し、準備の確認ダイアログで「実行する」を選んでください（「セットアップ」）。
  - 確認ダイアログから実行した `uv sync` が失敗した場合は、状態フォルダの `sync.log`（最後の出力）を確認してください。
  - 確認ダイアログが出ない場合は、「今後確認しない」を選んでいないか（状態フォルダの `setup.declined`）確認してください。
  - uv を PATH 以外の場所に入れている場合は、環境変数 `HOOKNOTICE_UV` に uv のパスを設定してください。
- **OK を押しても許可されない（VS Code / ターミナル側のダイアログが残る）**:
  通知の OK はダイアログのボタンを押すのではなく、Hook から Claude Code に「許可」を返す仕組みです。
  まず、OK を押した後にツール（コマンド）が実行されたかを確認してください。
  - **実行された場合**: 許可は効いています。ダイアログの表示が残っているだけです。
  - **実行されない場合**: 次の順に確認してください。
    1. プラグインの導入・更新の後に Claude Code を再起動（VS Code はウィンドウの再読み込み）したこと。
       Hook は起動時に読み込まれます。
    2. Claude Code で `/hooks` を開き、`PermissionRequest` に hooknotice が1つだけ登録されていること
       （以前に手で導入した版を使っていた場合は、`~/.claude/settings.json` からその Hook を削除します）。
       他の `PermissionRequest` Hook や、settings の deny / ask ルールに当たる操作は、OK を押しても許可されないことがあります。
- **「解説」ボタンが出ない**: 解説には Claude Code の実行ファイルを使います。Hook に渡される
  環境変数 `CLAUDE_CODE_EXECPATH` か、PATH 上の `claude` が見つからない場合はボタンを出しません。
- **解説が「生成できませんでした」になる**: 表示された理由を確認してください。Claude Code に
  ログインしていない、利用上限に達している、などが考えられます。もう一度「解説」を押すと再試行します。
- **クリックしても前面化しない**: 発火元アプリは環境変数 `__CFBundleIdentifier`
  （無ければ `TERM_PROGRAM`）から推定しています。どちらも取れない環境では前面化されません。
  使用中のアプリを追加したい場合は `hook_notify.py` の `TERM_PROGRAM_BUNDLE_IDS` に追記してください。
- **通知が多すぎる / 足りない**: 設定画面（⚙ または `/hooknotice:settings`）で場面ごとにオン/オフできます。
  許可待ちをオフにすると、通知を出さずにターミナル側のダイアログだけで答えます。
- **スタック位置がおかしいまま残る**: `~/Library/Application Support/hooknotice/stack_state.json`
  が表示中の通知の並び順を記録しています。異常終了したプロセスの記録は次回起動時に自動で
  回収されますが、問題が続く場合はこのファイルを削除しても支障ありません。

## データの扱い

hooknotice のコード自体は通信しません。外部との通信が起きるのは、次の2つだけです。

- **確認ダイアログで「実行する」を選んだとき**: `uv sync` を実行し、uv が PyPI から PySide6-Essentials と shiboken6 を
  ダウンロードします。送るのはパッケージの取得要求だけです（自分で `uv sync` や `pip install` を実行したときも同じです）。
- **「解説」ボタンを押したとき**: 許可を求めている操作の内容（ツール名、作業ディレクトリのパス、
  コマンドなどの入力。最大8,000文字）を、利用者自身がログインしている `claude` コマンドに渡します。
  内容は `claude` を通して Anthropic に送られ、利用者の Claude の利用枠（または API の料金）を消費します。
  扱いは Anthropic の規約とプライバシーポリシーに従います。ボタンを押さなければ送られません。
- **ローカルに保存するもの**（どれも外部には送りません）:

  | ファイル | 中身 |
  | --- | --- |
  | `config.json`（データフォルダ） | 設定画面で選んだ設定 |
  | `prompts.json`（状態フォルダ） | セッション ID と、最後にプロンプトを送った時刻（1日たつと消える） |
  | `stack_state.json`（状態フォルダ） | 表示中の通知のプロセス番号と高さ（通知を並べるため） |
  | `settings.lock`（状態フォルダ） | 設定画面を2つ開かないための目印 |
  | `sync.log`（状態フォルダ） | 確認ダイアログから実行した `uv sync` の出力 |
  | `setup.lock` / `setup.declined`（状態フォルダ） | 確認ダイアログを2つ出さないための目印、「今後確認しない」の印 |

  データフォルダは `~/.claude/plugins/data/hooknotice-hooknotice/` です（`venv` も置かれ、プラグインのアンインストールで削除されます）。
  状態フォルダは、macOS が `~/Library/Application Support/hooknotice/`、Windows が `%LOCALAPPDATA%\hooknotice\` です。
  通知に表示したコマンドや Claude の返答は、ファイルに保存しません。
- **読むもの**: 許可待ちの間は、ターミナル側で先に答えたかを確かめるため、Claude Code の会話の記録
  （`transcript_path`）の末尾を読みます。読むだけで、書き換え・保存・送信はしません。
  また、`language` が `auto` のときは、macOS の言語設定（`~/Library/Preferences/.GlobalPreferences.plist`）を読みます。

## 既知の制約

hooknotice は、公式ドキュメントに記載のない次の環境変数を利用しています。将来の Claude Code や macOS で
使えなくなった場合も通知と許可ボタンは動きますが、該当する機能だけが働かなくなります。

| 環境変数 | 設定元 | 用途 | 使えない場合 |
| --- | --- | --- | --- |
| `CLAUDE_CODE_EXECPATH` | Claude Code | 「解説」で `claude` を呼び出す | PATH 上の `claude` を使う。無ければ「解説」ボタンを出さない |
| `__CFBundleIdentifier` | macOS | クリックで元のアプリを前面に出す | `TERM_PROGRAM` から推定。できなければ前面化しない |

また、許可待ちにターミナル側で先に答えたかどうかは、Claude Code の会話の記録（Hook に渡される `transcript_path`）を
読んで判断しています。記録の中身の形式は公式には文書化されていないため、形式が変わった場合は、答えた後でも
待ち時間（既定6秒）が過ぎると通知が出ることがあります（通知の ✕ で閉じれば影響はありません）。

## 開発

プラグインの本体は [plugins/hooknotice/](plugins/hooknotice/) にあります。手元の変更を試すには、直接読み込みます
（そのセッションでは導入済みの版の代わりに使われます）。

```bash
claude --plugin-dir ./plugins/hooknotice
```

Claude Code を使わずにテスト通知を出すには、`plugins/hooknotice` で一度 `uv sync` を実行して環境を作り
（そこに `.venv` ができます。`CLAUDE_PLUGIN_DATA` が無いときはこちらを使います）、次を実行します。

```bash
cd plugins/hooknotice
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | python3 hook_notify.py --event permission_request
```

コマンドはウィンドウが閉じられるまで待ち、OK で allow、キャンセルで deny の JSON を出力して終了し、
✕ では何も出力せずに終了します。このリポジトリの開発ルールは [CLAUDE.md](CLAUDE.md) にあります。

## ライセンス

[MIT License](LICENSE)（Copyright (c) 2026 Tri9ster）。無保証です。通知のボタンで許可・回答した操作の結果は、利用者の責任となります。

依存ライブラリの [PySide6-Essentials](https://pypi.org/project/PySide6-Essentials/)（Qt for Python の基本モジュール）と、
それが使う [shiboken6](https://pypi.org/project/shiboken6/)（Python と Qt をつなぐ部品）は、
どちらも LGPLv3 / GPLv2 / GPLv3（または商用ライセンス）で提供されています。
hooknotice はこれらを同梱せず、利用者が準備の確認ダイアログで「実行する」を選んだとき（または自分で `pip install` したとき）に、利用者の環境へ PyPI から入れる形で使います。

hooknotice は Claude Code 用の非公式ツールで、Anthropic とは関係ありません。
