# 開発記録

新しいものを上に書く。失敗・つまずきの詳細は [failures.md](failures.md) の番号（F-xx）で参照する。

---

## 2026-09-30: `@claude` の実行者の制限と、Actions の依存を uv とキャッシュで入れる

### 目的
- `.github/workflows/claude.yml` を、リポジトリの持ち主以外のコメントや Issue では起動しないようにする。
- Actions は毎回まっさらな VM で動くため、`@claude` のたびに apt・PySide6・claude CLI を入れ直している。
  これは Actions では普通のやり方だが、`pip install PySide6` は本番（`PySide6-Essentials`＋`uv.lock`）とずれていて、キャッシュも無かった。

### 決めたこと
- `if:` を `github.actor == 'Tri9ster' && ( …従来の4条件… )` にした。
- PySide6 は `astral-sh/setup-uv@v6`（`enable-cache`、キーは `plugins/hooknotice/uv.lock`）＋ `uv sync --frozen` で入れ、
  `plugins/hooknotice/.venv/bin` を `GITHUB_PATH` に足して、Claude が使う `python3` を venv にした。allowedTools に `Bash(uv:*)` を追加。
- apt（Qt の offscreen に要る共有ライブラリ）と `npm install -g @anthropic-ai/claude-code`（`claude plugin validate` 用）は、
  数十秒で済むのでキャッシュせずそのまま。

### 分かったこと
- 手元では YAML の構文だけ確認した。キャッシュの効き方と、持ち主以外のコメントで skip されることは、push 後に Actions で確かめる。

---

## 2026-09-29: 解説のモデル・effort の設定化と、docs 更新ルールの追加（Issue #3）

### 目的
- 解説を作る `claude -p` のモデルと effort を、設定画面は作らず `config.json` で切り替えられるようにする。
  既定は `sonnet` / `low`。あわせて `--output-format stream-json` を使い、届いた分から解説欄に出す。
- 機能追加・修正のたびに docs を更新する運用を、`CLAUDE.md` で必須にする。

### 決めたこと
- 設定は `config.json` の `explain`（`model` 既定 `sonnet`、`effort` 既定 `low`）。`effort` は `low` / `medium` / `high` /
  `xhigh` / `max`、不正な値は既定値に戻す。`model` は `claude --model` にそのまま渡す。
- 表示は `--output-format stream-json --verbose --include-partial-messages` の `text_delta` を届いた順に出し、終了時は
  `result` の本文で置き換える（`is_error` なら失敗表示）。利用者に届けるため `plugin.json` の version を 0.1.1 に上げる。
- `CLAUDE.md` に「docs の更新（コミット前に必須）」の節を足し、`docs/README.md` の約束にも同じことを書いた。
- `docs/specification.md`（設定表・解説の起動コマンド・変更履歴）と README の英日にも反映した。

### 分かったこと
- 利用者が macOS の実機で、`claude/issue-3-20260929-1334` の実装に問題ないことを確認済み。
  Actions 上の環境では `git merge` / `git checkout <branch> -- <files>` が承認待ちになるため、
  1334 と 1409 のブランチの差分を読み、手作業で本ブランチに取り込んだ（内容は同じ。この環境では py_compile と `load_config` の確認のみ）。

---

## 2026-09-28（2回目）: Claude Code プラグイン化

### 目的
zip の手渡しと Hook の手動マージによる共有をやめ、公開リポジトリ `Tri9ster/hooknotice` をプラグイン兼マーケットプレイスにして、
`/plugin marketplace add Tri9ster/hooknotice` → `/plugin install hooknotice@hooknotice` で導入・更新できるようにする。

### 決めたこと
- 構成: リポジトリ直下に `.claude-plugin/marketplace.json`、プラグインは `plugins/hooknotice/`。マーケットプレイス名・
  プラグイン名とも `hooknotice`（インストール先が `cache/hooknotice/hooknotice/` になり名前が一貫する）。
- 本体（`CLAUDE_PLUGIN_ROOT`）は更新のたびに入れ替わるので、venv と `config.json` は `CLAUDE_PLUGIN_DATA` に置く。
  環境変数が無いとき（リポジトリから直接動かす開発時）は従来の場所を使い、コードを分けない。
- 準備は従来の確認ダイアログ（SessionStart → 了承後に `uv sync --frozen`）をそのまま使い、`UV_PROJECT_ENVIRONMENT`
  で venv を DATA に作る。`uv sync` の自動実行はしない方針を変えない。
- 設定のスキルは `skills/settings` にし、`/hooknotice:settings` で呼ぶ（プラグインのスキルは名前の前に
  プラグイン名が付くため、`hooknotice-settings` だと `/hooknotice:hooknotice-settings` と重複する）。
- `plugin.json` に `version` を書く（書いた版に固定され、上げたときだけ利用者に更新が届く）。

### 分かったこと
- Hook のプロセスには `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA` が環境変数で渡るが、Claude が Bash ツールで実行する
  コマンドには渡らない。スキル本文の `${CLAUDE_PLUGIN_DATA}` は読み込み時に置換されるので、設定画面のスキルでは
  それを `CLAUDE_PLUGIN_DATA=...` として付けて起動する。
- プラグインのファイルはコピーで配置されるため、更新日時での「依存が更新されたか」の判定は、更新のたびに誤って
  反応するおそれがある。印ファイルに `pyproject.toml` / `uv.lock` の中身のハッシュを書いて比べるようにした。

### 確認したこと
- `claude plugin validate` がマーケットプレイス・プラグインとも通る。
- `CLAUDE_PLUGIN_DATA` を仮のフォルダにして、`needs_sync` → `run_sync`（実際の `uv sync --frozen`）→ 印ファイルの
  ハッシュ → `needs_sync` が偽、`save_config` / `load_config` が DATA の `config.json` を使うこと、本体のフォルダに
  何も書かれないことを確認した。依存ファイルの更新日時だけを変えても `needs_sync` は偽のまま。
- 実際に導入しての確認（全種類の通知、ボタンの回答、設定画面のスキル）は、公開後に行う。

## 2026-09-28: 英語・日本語の多言語対応

### 目的
公開・プラグイン化（Git 管理外の TEMP/plugin-plan.md）に向けて、日本語以外の利用者にも使えるようにする。まず英語と日本語。

### 決めたこと（ユーザーと合意）
- 言語は `config.json` の `language`（`auto` / `ja` / `en`）。既定は `auto`（OS の言語が日本語なら日本語、それ以外は英語）。
- README は英語（`README.md`）と日本語（`README.ja.md`）の2本。仕様書と DevDocs は日本語のまま、この対応を追記する。

### 実装
- 文言を新モジュール `messages.py` の辞書に集め、`tr()` で引く（162キー、日英同数）。設計は architecture.md 4.10。
- `platform_support.system_language()` を追加（macOS は言語設定の plist を直接読む）。`ask_dialog` の Windows 用の書き添えは引数で受け取る。
- `hooknotice_config.Scene` から表示名・説明を外し、分類をキーにした（文言は `scene.*` / `group.*`）。
- 置き換えたもの: 通知のタイトル、本文の定型句、ボタン、「解説」の案内とシステムプロンプト（英語版を新規に書いた）、
  Claude に返す拒否の理由、準備（uv sync）のダイアログ、設定画面の全文言。設定画面に「言語」のコンボを追加。

### 検証
- 日英のキー集合が一致し、差し込む値の名前も全キーで一致すること、コードから引くキーがすべて辞書にあることをスクリプトで確認。
- `system_language()` がこの Mac で `ja` を返すこと。
- 言語を差し替えて `permission_decision`（拒否の理由）、`stop_failure_markdown`、`agent_markdown`、`question_markdown`、
  `explain_input`、準備ダイアログの文言、uv の入れ方の手順を日英で出力して確認。
- offscreen で許可待ち・計画の承認・選択肢の質問の通知と設定画面を日英で描画し、画像で確認。
  最初は設定画面の「言語」のヒントをコンボの右に置いたが、英語で5行に折り返して行が高くなったため、コンボの下の行に移した。
- 未確認: 実際の「解説」の英語出力（押すと利用枠を消費するため）、Windows の `GetUserDefaultUILanguage` の判定。

: 待ち時間を本文の文字数から決められるようにする

- 長い計画や返答を読んでいる途中で通知が出るため、待ち時間を「固定」と「文字数から自動」から選べるようにした。
  自動は `max(最低秒数, ceil(文字数 × 60 ÷ 1分あたりの文字数))`、上限120秒。対象は許可待ち・計画・質問・作業完了など、待つ通知すべて。
- 数える本文（`reading_text`）は VS Code 側で読む内容に合わせた（Edit は差分の old/new、Write は中身）。空白・改行は数えない。
- 検証:
  - `delay_for`: 固定は常に6秒。自動（600文字/分）は 30字→6秒、300字→30秒、5000字→120秒。最低0なら0。
  - `reading_text`: Bash・Edit・MultiEdit・Write・計画・質問・Stop・通知の各 payload で期待どおりの本文になった。
  - Hook（3000文字/分・最低6秒）: Stop 500字は10秒で表示、30字は6秒で表示、4秒後にプロンプト送信なら表示しない。
  - 設定画面（offscreen）: 切り替えで読む速さの欄が有効・無効になり、保存値に `delay_mode` / `reading_cpm` が入る。
    ラベルと補足が右端で切れたので、短くして折り返すようにした。保存 → 読み込みで値が保たれ、不正な値は既定値に戻る。
  - 実機（VS Code）で確認済み: 600文字/分・最低6秒で、675字の返答の後、約68秒で作業完了の通知が出た。

---

## 2026-09-27（4回目）: 許可待ちに6秒以内に答えたら通知を出さない

- 許可待ちにすぐ答えても通知が出ていた。一時ログで、答えても Claude Code は Hook を終了させないことを確かめた（F-21）。
- 待つ間と表示中に、会話の記録（`transcript_path`）でツールの結果が書かれたかを 0.5 秒ごとに確かめる `AnswerWatcher` を追加した。
  回答済みなら通知を出さず、表示中なら Hook を終了してウィンドウを閉じる。記録に該当が無ければ従来どおり通知する。
- 検証: 偽の記録で「呼び出しの書き込みが遅れて回答」「過去に同じコマンドがあり今回は未回答 → 表示後に回答で閉じる」
  「未回答なら通知する」を確認。約8MBの記録でも初回の読み込みは 0.02 秒。
  実機（VS Code）で確認済み: 6秒以内に許可すると通知は出ない／10秒待つと通知が出て、VS Code 側で許可すると自動で閉じる。

---

## 2026-09-27（3回目）: 準備（uv sync）が必要なときに確認ダイアログを出す

- README を読まない人向けに、`.venv` が無い・依存が更新されたことを SessionStart Hook で検出するようにした。
- 最初は裏で `uv sync` を自動実行する形で実装したが、ユーザーの判断で**自動実行はやめ、OS のダイアログで了承を得る**形にした。
  ダイアログは `hook_notify.py --setup` として切り離して出す（SessionStart は 0.1 秒で終わる）。
- uv が無いときは、uv の入れ方と pip で入れる手順をダイアログに出す（「手順をコピー」でクリップボードへ）。
  pip の手順は macOS 標準の Python 3.9 でも通ることを確認した（PySide6-Essentials 6.10.3 が入る）。
- 「今後確認しない」は `setup.declined` に記録する。確認ダイアログの二重表示は `setup.lock` の待たない排他ロックで防ぐ。
- Hook の PATH に uv が無いことがあるため、よくある置き場所も探す（`find_uv`。`HOOKNOTICE_UV` で指定も可）。
- 検証: ダイアログの返り値を差し替えて「今はしない / 実行する / 今後確認しない / 手順をコピー」の各分岐、
  `uv.lock` 更新の検出、pip で作った venv は確認しないこと、実物のダイアログ表示（5秒で自動的に閉じる設定）。

---

## 2026-09-27（2回目）: 名称を hooknotice に変更

- 配布前の法的チェックで、「Claude」を含む名前は Anthropic の規約（名称・ロゴの使用）に抵触するおそれがあると分かった。
- 候補を PyPI・npm・GitHub・.com で調べ、どこでも未使用の `hooknotice` にした（hookpop は同名の AI サービス、
  hookchime は同じ目的のツールが既にあったため見送り）。
- 旧名称の参照をすべて置き換えた（フォルダ・モジュール・スキル・環境変数・状態フォルダ・settings.json の Hook）。
  フォルダを移したため `.venv` は作り直した（中のスクリプトが旧パスを指すため）。以下の過去の記録は当時の名前のまま。
- ライセンスを MIT に決めた（配布しやすさ優先。PySide6 の LGPLv3 とも両立）。`LICENSE`・README・pyproject の `license` を追加した。
- 依存を `PySide6` から `PySide6-Essentials` に変えた。使うのは QtCore・QtGui・QtWidgets だけで、すべて Essentials に入っている。
  使わない PySide6-Addons（GPL だけのモジュールを含む）が入らなくなり、ライセンスの説明が単純になった。

## 2026-09-27: StopFailure と Notification 全12種への対応、設定画面の追加

### 決めたこと（ユーザーと合意）

| 項目 | 決定 |
| --- | --- |
| 対応するイベント | StopFailure と Notification の公式12種すべて |
| 出す・出さないの判断 | Hook は全部登録し、`config.json` の `notify` を見て notifier 側で決める（settings.json は触らない） |
| 既定値 | 重複するもの（permission_prompt・idle_prompt）と報告だけのもの（auth_success・elicitation_complete・elicitation_response）はオフ |
| 設定画面の起動元 | 通知の ⚙ ボタンと、スラッシュコマンド `/notifier-settings`（メニューバー常駐は、常駐しない設計に反するため見送り） |
| 通知音 | 設定画面で、鳴らすか・OS ごとのシステムの音か任意の音声ファイルかを選ぶ |
| サブエージェント・タスク系 | SubagentStop / TaskCompleted / TeammateIdle を追加（既定オフ）。SubagentStart / TaskCreated は雑音のため見送り |
| 通知のタイミング | すべての通知を約6秒放置されたときだけ出す（設定で変更、0 ですぐ）。「長くかかった作業だけ通知」案は取り下げ。`permission_prompt` への切り替えはボタンを付けられないため採らず、許可待ちの Hook 側で待つ方式にした |

### 検証

| 確認 | 方法 | 結果 |
| --- | --- | --- |
| 設定の読み書き | ファイル無し・壊れている・一部だけ・未知キーあり | 既定値で補い、保存は指定キーだけを上書きして未知キーを残した |
| Notification 12種・StopFailure | テスト入力を1種ずつ流し、ウィンドウのプロセスが増えたかを見る | 既定オンの8種と StopFailure だけ表示された |
| 設定の即時反映 | `save_config` でオン/オフを変えて同じ入力を流す | 次の通知から効いた。許可待ちオフでは出力なしで即終了 |
| 設定画面 | offscreen 描画、`--detach` で2回起動 | 表示に問題なし。2回目は開かず1つだけ |
| サブエージェント・タスク系 | テスト入力を既定とオンで流す | 既定では出ず、オンで3種とも表示。出力は無し |
| 放置の判定 | テスト入力で5パターン | 放置で約6.2秒後に表示／待つ間にプロンプト送信で出ない／待たない種類は0.1秒で表示／許可待ちは待つ間に Hook 終了で出ない・放置で6.2秒後にボタン付き |

---

## 2026-09-26: 計画承認の通知で承認ボタンが効かない不具合の修正

### 目的

実際の計画承認で、通知の承認ボタンを押しても Claude Code が先に進まなかった（F-20）。

### 実装

- `hook_notify.py` の `permission_decision`: 計画承認の allow に `updatedInput`（元の `tool_input`）を付けた。
- 調査用に一時ログ `platform_support.debug_log`（`debug.log` への追記）を入れ、確認後に削除した。

### 検証

| 確認 | 方法 | 結果 |
| --- | --- | --- |
| クリックと決定の流れ | 実際の計画承認で各ボタンを押し、debug.log を読む | クリック・結果・allow の出力はすべて正常。Claude Code だけが採用していなかった |
| 修正後の承認 | 実際の計画承認で「自動モードで承認」を押す | 計画モードを抜け、先に進んだ |
| ほかの承認ボタン | 「編集を自動許可で承認」「都度確認で承認」を実機で押す | どちらも承認され、次の Hook の `permission_mode` がそれぞれ `acceptEdits` / `default` になった |
| 選択肢の質問 | 実際の AskUserQuestion（単一選択と複数選択の2問）に通知から回答 | 回答がそのまま Claude に届いた |

---

## 2026-09-25（4回目）: 質問・計画の承認待ちの通知を Markdown で表示

### 目的

AskUserQuestion / ExitPlanMode の通知本文が `tool_input` の JSON そのままで、何を聞かれているのか読みにくかった。

### 決めたこと（ユーザーと合意）

| 項目 | 決定 |
| --- | --- |
| 表示方法 | Markdown で整形（解説欄と同じ仕組み） |
| 選択肢の preview | 表示する（コードブロック） |
| 通知から回答すること | 今回は対象外（`updatedInput` で回答を返せる可能性はあるが別機能として検討） |

### 実装

- `hook_notify.py`: `question_markdown` / `tool_markdown` / `_code_fence`、ツール別タイトル `TOOL_TITLES`、`--markdown` の受け渡し。
- `notify_window.py`: `--markdown` の本文欄。解説欄と作成・整形の処理を共通化（`_new_markdown_view`、`_set_markdown`、
  `_polish_markdown(view)`）。外観の切り替え時も当て直す。
- Markdown 整形の修正: 見出しが大きすぎた（F-18）、コードの文字が本文より大きかった（F-19）。

### 検証

| 確認 | 方法 | 結果 |
| --- | --- | --- |
| Markdown の組み立て | 質問1件 / 複数件・複数選択・``` 入り preview・不正な選択肢 / questions 無し・型違い / 計画 / Bash | 期待どおり。不正な入力は従来の本文にフォールバック |
| 見た目 | offscreen 描画（質問: ダーク/ライト、計画: ダーク） | 読みやすく表示。長い計画は画面の高さで止まりスクロール |

---

## 2026-09-25（3回目）: 通知の横幅と改行する文字数を設定ファイルで変えられるようにする

### 目的

横幅（`WIDTH = 340`）と長いコマンドを改行する文字数（`FORMAT_LINE_LIMIT = 44`）がコードに直書きで、
変えるにはコードの編集が必要だった。

### 決めたこと（ユーザーと合意）

| 項目 | 決定 | 理由 |
| --- | --- | --- |
| 設定方法 | `notifier/config.json`（設定画面は作らない） | 項目が少なく、1通知1プロセスなので次の通知から反映される |
| 文字数 | 幅から自動計算、指定したときだけ優先 | 幅を変えたら文字数も追従させたい |

### 実装

- 新規 `notifier_config.py`: `load_config()`（検証して不正な値は既定値）と `auto_line_limit()`。
- `hook_notify.py`: `FORMAT_LINE_LIMIT` をやめ、`format_command(command, line_limit=None)` が設定値を使う。
- `notify_window.py`: `WIDTH = load_config().width`。幅を使う箇所はすべて `WIDTH` 参照なので他は変更なし。
- 既定値の `config.json` を置き、Git 管理する。共有用 zip には含めない（SHARING.md に `notifier_config.py` を追加）。

### 検証

| 確認 | 方法 | 結果 |
| --- | --- | --- |
| 設定の読み込み | ファイル無し / 正常 / 文字数指定 / JSON 不正 / 範囲外 / 型違い / 配列 | すべて期待どおり（不正は既定値） |
| 自動計算 | `auto_line_limit` | 280→35、340→44（従来と同じ）、420→56、500→68、800→113 |
| 整形の回帰 | 前回の15ケース | すべて意味が一致 |
| 幅 420px の見た目 | offscreen 描画 | カードが広がり、`grep` の行も折り返さずに収まった |
| 実機: 340px → 420px | `config.json` を書き換えて通知を出し、ユーザーが目視 | 次の通知から幅が広がった |

### その後の決定

実機で試した結果、ユーザーの判断で既定の幅を 420px（文字数は自動で 56）に変更した。

---

## 2026-09-25（2回目）: コマンド欄のワンライナーを整形して表示

### 目的

`;`・`&&`・パイプ・環境変数の前置きがつながった長いワンライナーが1行で表示され、読みにくかった。

### 決めたこと（ユーザーと合意）

| 項目 | 決定 | 経緯 |
| --- | --- | --- |
| `&&` / `||` | 行末に残して ` \` | 行頭案も検討したが、ユーザーの希望で行末に。消す案は意味が読めなくなるので不採用 |
| `;` | 行末に残し、まとまりの間に空行 | ユーザーの例では `&&` になっていたが、意味が変わるため `;` のまま表示 |
| 長い要素 | 代入を1行ずつ、本体は2文字字下げ、パイプは `  | …` | ユーザーの例のとおり |
| 引用符 | 足さない | ユーザーの例では `"$S/live.py"` となっていたが、元のコマンドに無いものは表示しない |

### 実装

- `hook_notify.py` に `_scan_command`（トップレベルの語と演算子への分解）、`_format_element`、`format_command` を追加。
- `bash_command()` が返すコマンドにだけ適用。解説に渡す内容と決定には影響しない。
- 実行時の安全策は `bash -n`（構文チェックのみ）。`eval` による比較は許可前のコマンドを実行しうるため採用しない。

### 検証

| 確認 | 方法 | 結果 |
| --- | --- | --- |
| 15ケースの整形と意味の同一性 | 元と整形後を `declare -f` で正規化して比較 | すべて一致。ヒアドキュメント・複数行・閉じていない引用符・コメント付きは無変換 |
| 見た目 | offscreen 描画（ダーク） | 1行ずつ読める。カード幅（約42文字）を超える行は行頭から折り返される |

### 未確認・今後

- カード幅を超えて折り返された行は字下げされない（折り返し部分が行頭から始まる）。
- 実機の通知での表示は、ユーザーの確認待ち。

---

## 2026-09-25: 許可待ちの通知に「解説」ボタンを追加

### 目的

長いワンライナーなど、何をする操作なのか読み解くのに時間がかかり、許可の判断がしにくかった。
通知の中で Claude に解説させ、読んでからそのまま OK / キャンセルできるようにする。

### 決めたこと（ユーザーと合意）

| 項目 | 決定 | 理由 |
| --- | --- | --- |
| モデル | Sonnet | 質と速度のバランス。試行では Haiku と所要時間はほぼ同じ（約10秒） |
| 対象 | すべての許可待ち | Edit / Write / WebFetch などでも、何が起きるかを知りたい |
| 表示場所 | 通知カードを下に伸ばす | 読んでそのまま回答できる |

### 調査

- `claude` は PATH に無かった（VS Code 拡張のみの環境）。Hook の環境変数 `CLAUDE_CODE_EXECPATH` が
  拡張同梱のバイナリを指していたので、これを使う（F-12）。
- `--bare` は Hook を読まず軽いが、OAuth を読まないため使えない（F-13）。代わりに
  `--setting-sources ""` + `--tools ""` + `CLAUDE_NOTIFIER_DISABLED=1` で再帰と副作用を防ぐ。
- stdin を閉じないと「no stdin data received in 3s」の警告が出て3秒遅れる（F-14）。

### 実装

- `hook_notify.py`: `explain_input()` で操作内容を組み立て、`--explain-input` で渡す。
- `notify_window.py`:
  - ボタン行の左端に「解説」（claude が見つかる場合のみ）。
  - `QProcess` で非同期に `claude -p` を起動。生成中は「生成中…」で無効化、閉じたら kill。
  - 結果を `QTextBrowser.setMarkdown()` で表示し、`_polish_markdown` で狭いカード向けに整形（F-16, F-17）。
  - `_fit_height` を一般化し、縮める対象を「解説欄 → コマンド欄」の順にした。
  - `StackSlot.update_height` で高さを記録し、下の通知が追従する。
  - 外観の切り替え時は、保持している Markdown を再設定して整形し直す（コード背景の色をテーマに合わせる）。

### 検証

| 確認 | 方法 | 結果 |
| --- | --- | --- |
| ボタン行・解説欄の見た目（ダーク/ライト） | offscreen 描画 | OK（途中で F-15〜F-17 を修正） |
| 実際の生成（Bash） | offscreen で `_start_explain` | 14.4 秒で完了、画面高さを超えた分はスクロール |
| 実際の生成（Edit） | 同上 | 9.6 秒で完了、推測部分に「推測」と明記された |
| 生成中に閉じる | offscreen、2秒後に close | 子の claude は残らない |
| 実機: 2件重ねて解説 → OK / キャンセル | 実画面でユーザー操作 | 解説でカードが伸び、下の通知が下へずれた。allow / deny の JSON を確認 |

### 未確認

- 生成失敗時の表示（未ログイン・利用上限など）は実際に起こしていない。
- 解説表示中の外観切り替え（コード背景の追従）は実機で試していない。

---

## 2026-09-24（2回目）: 配色を macOS の外観設定に従わせる

### 目的

ダーク配色で固定されており、ライトモードでは周囲から浮いて見えた。

### 実装

- 散らばっていた色を `THEMES["dark" | "light"]` と `STYLE_SHEET` テンプレートにまとめた。
  ダーク側は変更前の値をそのまま移した。
- `styleHints().colorScheme()` でテーマを決め、`colorSchemeChanged` で表示中も追従。
- ライトでは白いウィンドウの上で輪郭が溶けるので、1px の縁取り（0.5px 内側に描画）を追加。
- ハイライト色は乱数の「位置」だけを先に決め、テーマ適用時に色を作る形に分けた。

### 検証

| 確認 | 方法 | 結果 |
| --- | --- | --- |
| ダークが変更前と同じ | 乱数を固定して offscreen 描画し、変更前の画像とバイト比較 | 同一（途中で F-09, F-10） |
| ライトの見た目 | offscreen 描画 | OK |
| 実機のダーク/ライト、表示中の追従 | osascript で外観を切り替え、ユーザーが目視 | 新しい通知はライト、表示中のダーク通知もライトに追従 |

---

## 2026-09-24: 許可待ちの通知から OK / キャンセルで回答する

### 目的

通知に気づいてもターミナル（VS Code）に戻らないと許可できず、手間だった。

### 調査

- 公式ドキュメント（hooks）で `PermissionRequest` の決定の返し方を確認:
  `hookSpecificOutput.decision.behavior` に `allow` / `deny`。
- async の Hook の出力は無視される → 許可待ちの Hook だけ同期に変更（`async` を外し `timeout: 600`）。
- 最初に調べさせたエージェントの回答は JSON の形が誤っていたので、ドキュメント本文を直接読んで確認した（F-01）。

### 決めたこと（ユーザーと合意）

- OK → allow、キャンセル → deny、✕・本体クリック → 決定なし（ターミナルに任せる）。
- 許可待ち以外は従来どおり async の通知のみ。

### 実装

- `notify_window.py`: `--actions` でボタン行を出し、結果を stdout に出力。親の終了を検知して閉じる。
- `hook_notify.py`: 許可待ちは `subprocess.run` で終了を待ち、結果を決定 JSON に変換（`permission_decision`）。
- `AskUserQuestion` / `ExitPlanMode` はボタン無しの通知にした（F-03）。

### 検証

| 確認 | 方法 | 結果 |
| --- | --- | --- |
| ボタンの見た目、OK → `allow` 出力 | offscreen 描画、ボタンを `click()` | OK |
| Hook を kill したらウィンドウも閉じる | Hook を kill してプロセスを確認 | 1回目は閉じず（F-02）、修正後は閉じる |
| 許可待ち以外は待たない | `--event idle` の所要時間 | 0.04 秒で終了 |
| 実機（manual モード）: OK / キャンセル / ✕ / 本体クリック / コマンド欄クリック | 許可が必要なコマンドを実行し、ユーザーが操作 | すべて想定どおり（途中で F-04, F-05） |

### その後の報告

配布先から「OK を押しても VS Code の OK が押されない」との報告があった。原因は未確認（F-06）。
README のトラブルシューティングに確認手順を追記して配布し直した。
