# 「解説」のモデル比較: 24回ぶんの解説文

[20261011_explain_model_comparison.md](20261011_explain_model_comparison.md) の付録。モデルが返した解説文を、手を加えずにそのまま載せる。
解説文の中に見出しやコードブロックがあるため、1件ずつコードブロックで囲んである。

## bash 小

### bash 小 / sonnet / 1回目

最初の文字まで 2.1秒、完了まで 9.5秒、1300字。

`````markdown
この操作は、カレントディレクトリ（`~/work/sample`）以下を再帰的に探し、最終更新から7日より古い `.log` ファイルをすべて削除します。`|` によって、`find` が見つけたファイルの一覧を `xargs` に渡し、`xargs` がそれらを `rm` で削除する流れです。

---

### ステップ別の詳細解説

#### 1. 対象ファイルの検索

```bash
find . -name '*.log' -mtime +7 -print0
```

- `find .`: カレントディレクトリ以下をサブディレクトリも含めて再帰的に探索します。
- `-name '*.log'`: ファイル名が `.log` で終わるものに絞ります。シェルによる展開を避けるため、引用符で囲んでいます。
- `-mtime +7`: 最終更新から7日より古いものに絞ります。`find` は経過日数を切り捨てて数えるので、実質的には8日以上前に更新されたファイルが対象です。
- `-print0`: 見つけたパスを、改行ではなくヌル文字（`\0`）で区切って出力します。スペースや改行を含むファイル名でも安全に扱えます。

#### 2. パイプによる受け渡し

```bash
|
```

- `find` の出力（ヌル区切りのパス一覧）を、次の `xargs` の標準入力に渡します。

#### 3. 一括削除

```bash
xargs -0 rm -f
```

- `xargs`: 標準入力から受け取ったパスを、引数として `rm` に渡します。
- `-0`: 入力をヌル区切りとして解釈します。`find` の `-print0` と対で使います。
- `rm -f`: ファイルを削除します。`-f` は、存在しないファイルがあってもエラーにせず、確認も求めません。

### 注意点

- 削除は**ゴミ箱を経由せず、元に戻せません**。`-f` により確認もありません。
- 対象は `~/work/sample` 以下のサブディレクトリ内も含めた**すべての `.log` ファイル**です。`node_modules` や `vendor` など、依存パッケージ内のログも対象になる場合があります（推測：ディレクトリの中身は入力から読み取れません）。
- `-type f` を指定していないため、名前が `.log` で終わるファイル以外のものも一致する可能性があります。ただしディレクトリは `rm`（`-r` なし）では削除されません。
- 事前に `-print0 | xargs -0 rm -f` の部分を外して `find . -name '*.log' -mtime +7` だけを実行すれば、削除対象を確認できます。

---

### まとめ

**`~/work/sample` 以下にある、7日より古い `.log` ファイルを再帰的に検索し、確認なしで一括削除する操作**です。実行前に対象一覧を確認しておくと安全です。
`````

### bash 小 / sonnet / 2回目

最初の文字まで 2.0秒、完了まで 10.0秒、1347字。

`````markdown
この操作は、カレントディレクトリ（`~/work/sample`）以下にある、最終更新から7日より古い `.log` ファイルを検索し、すべて強制削除します。`|` で `find` の結果を `xargs` に渡し、`rm` の引数として一括で処理する構成です。

---

### ステップ別の詳細解説

#### 1. 古いログファイルの検索

```bash
find . -name '*.log' -mtime +7 -print0
```

- `find .`: カレントディレクトリ以下を再帰的に検索します。
- `-name '*.log'`: ファイル名が `.log` で終わるものに限定します。シングルクォートで囲んでいるため、シェルによる展開は行われず `find` 自身がパターンを解釈します。
- `-mtime +7`: 最終更新から7日（24時間×7）を超えて経過したものに限定します。端数は切り捨てて判定されるため、実質的には「8日以上前」のものが対象です。
- `-print0`: 結果をヌル文字（`\0`）区切りで出力します。空白や改行を含むファイル名でも安全に扱えます。

#### 2. パイプによる受け渡し

```bash
|
```

- `find` の出力を `xargs` の標準入力に渡します。

#### 3. 一括削除

```bash
xargs -0 rm -f
```

- `xargs`: 標準入力から受け取ったファイル名を、コマンドの引数にまとめて渡します。
- `-0`: 入力をヌル文字区切りとして解釈します。`-print0` と対で使います。
- `rm -f`: ファイルを削除します。`-f` により、確認プロンプトを出さず、存在しないファイルがあってもエラーにしません。

### 注意点

- **削除は取り消せません。** `rm` はゴミ箱を経由せず、ファイルを直接削除します。
- `-f` を付けているため、書き込み保護されたファイルも確認なしで削除されます（権限があれば）。
- `find` は **サブディレクトリも再帰的に検索**します。`node_modules` や `.git` などの内部にある `.log` ファイルも対象になります。
- 作業ディレクトリが `~/work/sample` であることを前提にしています。別の場所で実行すると、意図しない範囲が対象になります。
- 事前に `xargs -0 rm -f` の部分を外して `find` のみで実行すれば、削除対象を確認できます（ドライラン）。
- 一致するファイルが0件の場合、GNU 版の `xargs` では `rm -f` が引数なしで実行されますが、`-f` により無害です。macOS の `xargs` は空入力ではコマンドを実行しません。

---

### まとめ

**`~/work/sample` 以下にある、7日より古い `.log` ファイルを再帰的に探し、確認なしで完全に削除する**操作です。対象範囲に重要なログが含まれていないかを確認したうえで、許可するか判断してください。
`````

### bash 小 / haiku / 1回目

最初の文字まで 4.3秒、完了まで 10.9秒、1048字。

`````markdown
このコマンドは、作業ディレクトリ `~/work/sample` 以下にある `.log` ファイルのうち、**7日以上前に最後に更新されたものを検索して削除します**。パイプで接続された `find` と `xargs` を組み合わせることで、ファイル名にスペースや特殊文字が含まれていても安全に処理できます。

---

### ステップ別の詳細解説

#### 1. ファイル検索と出力

```bash
find . -name '*.log' -mtime +7 -print0
```

- **`find .`** — カレントディレクトリ（`~/work/sample`）以下をすべて検索
- **`-name '*.log'`** — ファイル名が `.log` で終わるものに限定
- **`-mtime +7`** — **最後の更新時刻が7日より古い**（現在から7日以上前）ファイルのみマッチ
- **`-print0`** — マッチしたファイルパスをヌル文字（`\0`）で区切って出力

#### 2. パイプで受け渡し

```bash
|
```

- 前のコマンドの標準出力を、次のコマンドの標準入力に接続

#### 3. ファイル削除

```bash
xargs -0 rm -f
```

- **`xargs -0`** — ヌル文字で区切られた入力を読み込み、複数のファイルパスを `rm` コマンドの引数として組み立てる
- **`rm -f`** — ファイルを強制削除（存在しないファイルでもエラーを出さない）

---

### 注意点

- **削除は取り消せません** — このコマンドはファイルをゴミ箱に移さず完全削除します
- **更新時刻判定** — ファイルの「最後に更新された日時」をもとに判定するため、アクセスだけしたファイルは対象外です
- **大量削除の場合** — マッチするファイル数が多いと、意図しないファイルも削除される可能性があります。実行前に `find . -name '*.log' -mtime +7` で対象を確認することを推奨します
- **権限確認** — 削除対象のファイルが存在して削除権限がなければ、その部分は失敗します

---

### まとめ

**7日以上前のログファイルを自動削除する日常的なメンテナンス操作**です。ただし削除は完全であり、実行前に対象ファイルの確認が重要です。
`````

### bash 小 / haiku / 2回目

最初の文字まで 9.8秒、完了まで 14.9秒、1088字。

`````markdown
このコマンドは、`~/work/sample` ディレクトリ配下で7日より前に修正された `.log` ファイルをすべて検索し、削除します。`find` で対象ファイルを探し出し、`|（パイプ）` で `xargs` に渡して一括削除する流れです。

---

### ステップ別の詳細解説

#### 1. find コマンドで古いログファイルを検索
```bash
find . -name '*.log' -mtime +7 -print0
```
- `find .`：カレントディレクトリ（`~/work/sample`）及びその全サブディレクトリから検索開始
- `-name '*.log'`：ファイル名が `.log` で終わるファイルを対象にする
- `-mtime +7`：ファイルの修正時刻が7日より前（修正されてから7日以上経過）であることを条件にする
- `-print0`：マッチしたファイルパスをヌル文字（`\0`）で区切って出力（ファイル名に空白や特殊文字がある場合の安全性確保）

#### 2. パイプ経由で xargs に渡して削除
```bash
| xargs -0 rm -f
```
- `|`：前のコマンドの標準出力を次のコマンドの標準入力へ繋ぐ
- `xargs -0`：ヌル文字区切りの入力をコマンドライン引数に変換（複数のファイルパスを `rm` コマンドに渡す）
- `rm -f`：ファイルを強制削除（削除確認なし）

---

### 注意点

- **削除は取り消せない**：`rm -f` は即座にファイルを削除し、ゴミ箱に移動しません。削除されたファイルは復元困難です。
- **広範囲の削除対象**：`~/work/sample` 以下の全サブディレクトリが対象になります。意図しないログファイルも削除される可能性があります。
- **修正時刻が基準**：最後に修正されてから7日以上経過したファイルが削除対象です。ファイルの作成日時やアクセス時刻ではなく修正時刻（`mtime`）が判定基準です。
- **事前確認推奨**：実行前に `find . -name '*.log' -mtime +7` だけで実行し、対象ファイルを確認することを強く推奨します。

---

### まとめ

**このコマンドは `~/work/sample` 配下の7日以上前に修正された全ての `.log` ファイルを永続的に削除します。** 削除は取り消せない操作であるため、実行前に対象ファイルを必ず確認してください。
`````

## bash 中

### bash 中 / sonnet / 1回目

最初の文字まで 2.0秒、完了まで 16.4秒、2848字。

`````markdown
この操作は、`~/Documents/projects` を外付けなどのバックアップ先 `/Volumes/Backup/projects` へ、日時付きの世代フォルダとして rsync で増分バックアップします。そのあと `latest` リンクを更新し、30日より古い世代を削除します。コマンドは改行で区切られたシェルスクリプトで、`&&` は使わず、`|` で rsync の出力を `tee` に渡してログにも保存します。

---

### ステップ別の詳細解説

#### 1. 安全設定と変数の定義
```bash
set -euo pipefail
SRC="$HOME/Documents/projects"
DEST="/Volumes/Backup/projects"
STAMP=$(date +%Y%m%d_%H%M%S)
LOG="$DEST/backup_$STAMP.log"
```
- `set -euo pipefail`: エラーが出たら即停止（`-e`）、未定義変数の使用をエラーにし（`-u`）、パイプの途中の失敗も検出します（`pipefail`）。
- `SRC`: バックアップ元。
- `DEST`: バックアップ先。
- `STAMP`: `20261011_153000` のような現在日時。世代フォルダ名になります。
- `LOG`: ログファイルのパス（バックアップ先の中）。

#### 2. バックアップ先の存在確認
```bash
if [ ! -d "$DEST" ]; then
  echo "バックアップ先が見つかりません: $DEST" >&2
  exit 1
fi
```
- `$DEST` ディレクトリが無ければ（ドライブ未接続など）、エラーメッセージを標準エラーに出して終了します。
- 未マウント時に誤ってローカルディスクへ書き込むのを防ぐ役割です。

#### 3. 世代フォルダの作成と rsync
```bash
mkdir -p "$DEST/$STAMP"
rsync -a --delete --exclude 'node_modules' --exclude '.venv' \
  --link-dest="$DEST/latest" "$SRC/" "$DEST/$STAMP/" | tee "$LOG"
```
- `mkdir -p`: 今回の世代フォルダを作ります。
- `-a`: アーカイブモード（権限・日時・シンボリックリンクなどを保持して再帰コピー）。
- `--delete`: コピー先にあって元に無いファイルを削除します。ただし新規の空フォルダが対象なので、実質的に影響は小さいです。
- `--exclude 'node_modules'` / `'.venv'`: 依存パッケージ・仮想環境を除外します。
- `--link-dest="$DEST/latest"`: 前回の世代と同一のファイルは、コピーせずハードリンクにします。容量を節約でき、世代ごとに完全なスナップショットに見えます。
- `| tee "$LOG"`: rsync の出力を画面に表示しつつ、ログファイルへ保存します。

#### 4. `latest` リンクの更新
```bash
ln -sfn "$DEST/$STAMP" "$DEST/latest"
```
- `-s`: シンボリックリンクを作成します。
- `-f`: 既存のリンクを置き換えます。
- `-n`: 既存の `latest` がディレクトリへのリンクでも、その中にリンクを作らず `latest` 自体を置き換えます。
- 次回の `--link-dest` の基準が、今回の世代になります。

#### 5. 古い世代の削除
```bash
find "$DEST" -maxdepth 1 -type d -name '20*' -mtime +30 -exec rm -rf {} +
```
- `-maxdepth 1 -type d`: `$DEST` 直下のディレクトリのみが対象です。
- `-name '20*'`: 名前が `20` で始まる世代フォルダに限定します。
- `-mtime +30`: 更新から30日を超えたものが対象です。
- `-exec rm -rf {} +`: 該当ディレクトリを確認なしで再帰的に強制削除します。

#### 6. 世代数の集計と完了表示
```bash
COUNT=$(find "$DEST" -maxdepth 1 -type d -name '20*' | wc -l | tr -d ' ')
echo "完了: $STAMP (保持している世代: $COUNT)"
```
- 残っている世代フォルダの数を数えます。`tr -d ' '` は、macOS の `wc` が付ける余分な空白を除去します。
- 完了メッセージと世代数を表示します。

### 注意点
- **削除を伴います**: `rm -rf` で30日より古い世代を復元不能な形で削除します。ごみ箱は経由しません。
- **初回実行時の警告**: `latest` がまだ無いため、`--link-dest` が警告を出す場合があります（通常は続行します）。
- **`mtime` の注意**: 世代フォルダの更新時刻で判定します。`-mtime +30` が対象にするのは、現在の `latest` が指す世代を含む古いフォルダです。長期間バックアップを実行しないと、直近の世代しか無くなった状態でも、30日を超えれば最新の世代まで消える可能性があります（実行を再開しても、その時点で基準が無くなります）。
- **`set -e` との関係**: rsync が失敗するとスクリプトが止まるため、`latest` の更新や削除は実行されません。ただし作成済みの空または不完全な世代フォルダは残る可能性があります。
- **除外の影響**: `node_modules` と `.venv` はバックアップされないため、復元時に再構築が必要です。
- **ログの位置**: ログは `$DEST` 直下に `backup_*.log` として残り、自動では削除されません（`20*` に一致しないため）。

---

### まとめ
**`~/Documents/projects` を日時付きの世代スナップショットとして `/Volumes/Backup/projects` へ増分バックアップし、30日より古い世代を自動削除する**操作です。削除処理（`rm -rf`）を含むため、バックアップ先のパスと保持期間が意図通りか確認してから許可してください。
`````

### bash 中 / sonnet / 2回目

最初の文字まで 2.0秒、完了まで 14.7秒、2637字。

`````markdown
このコマンドは、`~/Documents/projects` を外付けディスク `/Volumes/Backup/projects` に日時付きの世代フォルダとしてバックアップし、30日より古い世代を削除するものです。全体は `set -euo pipefail` によりエラー時に即停止する1つのスクリプトで、途中の `|` は rsync の出力をログに保存しつつ画面にも表示するため、`&&` や `;` に当たる連結は改行で順次実行されます。

---

### ステップ別の詳細解説

#### 1. 安全設定と変数の定義
```bash
set -euo pipefail
SRC="$HOME/Documents/projects"
DEST="/Volumes/Backup/projects"
STAMP=$(date +%Y%m%d_%H%M%S)
LOG="$DEST/backup_$STAMP.log"
```
- `set -e`: コマンドが失敗したらスクリプトを即終了します。
- `set -u`: 未定義変数の使用をエラーにします。
- `set -o pipefail`: パイプの途中で失敗した場合もエラーとして扱います。
- `SRC`: バックアップ元（ホーム下のプロジェクトフォルダ）です。
- `DEST`: バックアップ先（外付けボリューム）です。
- `STAMP`: 現在日時（例: `20261011_153000`）で、世代フォルダ名になります。
- `LOG`: バックアップ先に置くログファイルのパスです。

#### 2. バックアップ先の存在確認
```bash
if [ ! -d "$DEST" ]; then
  echo "バックアップ先が見つかりません: $DEST" >&2
  exit 1
fi
```
- `-d` で `DEST` がディレクトリとして存在するか確認します。
- 無ければエラーメッセージを標準エラーに出し、終了コード1で止まります。外付けディスクが未接続の場合の安全装置です。

#### 3. 世代フォルダの作成と rsync によるコピー
```bash
mkdir -p "$DEST/$STAMP"
rsync -a --delete --exclude 'node_modules' --exclude '.venv' \
  --link-dest="$DEST/latest" "$SRC/" "$DEST/$STAMP/" | tee "$LOG"
```
- `mkdir -p`: 今回の世代用フォルダを作成します。
- `-a`: アーカイブモード（権限・日時・シンボリックリンクなどを保持して再帰コピー）です。
- `--delete`: コピー先に存在し元に無いファイルを削除します。ここでは新規の空フォルダが対象なので実質的な影響は小さいです。
- `--exclude`: `node_modules` と `.venv` を除外します。
- `--link-dest="$DEST/latest"`: 前回の世代と変更のないファイルはコピーせずハードリンクにし、容量を節約します。
- `tee "$LOG"`: rsync の出力を画面に表示しつつログへ保存します。

#### 4. 最新世代へのシンボリックリンク更新
```bash
ln -sfn "$DEST/$STAMP" "$DEST/latest"
```
- `-s`: シンボリックリンクを作ります。
- `-f`: 既存の `latest` を置き換えます。
- `-n`: `latest` が既存のリンクの場合、その先のディレクトリの中ではなくリンク自体を置き換えます。

#### 5. 30日より古い世代の削除
```bash
find "$DEST" -maxdepth 1 -type d -name '20*' -mtime +30 -exec rm -rf {} +
```
- `-maxdepth 1`: `DEST` 直下のみを対象にします。
- `-type d -name '20*'`: `20` で始まるディレクトリ（世代フォルダ）に限定します。
- `-mtime +30`: 最終更新が30日より前のものです。
- `-exec rm -rf {} +`: 該当ディレクトリを確認なしで再帰的に削除します。

#### 6. 保持世代数の表示
```bash
COUNT=$(find "$DEST" -maxdepth 1 -type d -name '20*' | wc -l | tr -d ' ')
echo "完了: $STAMP (保持している世代: $COUNT)"
```
- 残っている世代フォルダ数を数え、空白を除去して完了メッセージに表示します。

### 注意点
- ステップ5の `rm -rf` は、バックアップ先の古い世代を確認なしで完全に削除します。取り消せません。
- 世代フォルダの `mtime` は作成時刻とは限らないため、期待どおりの世代が消えない、または想定外に消える可能性があります（推測）。
- 世代が1つだけの状態で30日以上バックアップが失敗し続けると、最新の有効なバックアップも消える恐れがあります。ただし今回の実行で新しい世代が作られた後に消すので、直近の世代は残ります。
- 外付けディスクが未接続でも `/Volumes/Backup/projects` という通常のフォルダが存在すると、内蔵ディスクに書き込まれてしまう可能性があります。
- `node_modules` と `.venv` はバックアップされません。
- 初回は `latest` が存在しないため、`--link-dest` の警告が出ることがありますが、通常は処理が続行されます。

---

### まとめ
**`~/Documents/projects` を外付けディスクへハードリンク方式で世代バックアップし、30日より古い世代を自動削除する**処理です。書き込み先は `/Volumes/Backup/projects` に限られますが、古い世代の削除は取り消せない点に注意してください。
`````

### bash 中 / haiku / 1回目

最初の文字まで 5.5秒、完了まで 16.9秒、2432字。

`````markdown
このスクリプトは、`$HOME/Documents/projects` を外部ストレージ（`/Volumes/Backup/projects`）に世代管理しながらバックアップし、古い世代を自動削除するツールです。複数のコマンドが組み合わされて、ソース確認→バックアップ実行→世代管理という一連の処理を行います。

---

### ステップ別の詳細解説

#### 1. 変数とエラーハンドリング設定
```bash
set -euo pipefail
SRC="$HOME/Documents/projects"
DEST="/Volumes/Backup/projects"
STAMP=$(date +%Y%m%d_%H%M%S)
LOG="$DEST/backup_$STAMP.log"
```
- `set -euo pipefail`: エラー時に停止、未定義変数でエラー、パイプラインエラーを検出
- `SRC`: バックアップ対象ディレクトリ（ホームの Documents/projects）
- `DEST`: バックアップ先ディレクトリ（外部ストレージ）
- `STAMP`: 現在時刻を `年月日_時分秒` 形式で記録（世代識別用）
- `LOG`: バックアップログをバックアップ先に保存

#### 2. バックアップ先の確認
```bash
if [ ! -d "$DEST" ]; then
  echo "バックアップ先が見つかりません: $DEST" >&2
  exit 1
fi
```
- `/Volumes/Backup/projects` ディレクトリが存在するか確認
- 存在しなければエラーメッセージを標準エラーに出力して終了

#### 3. タイムスタンプ付きバックアップディレクトリ作成
```bash
mkdir -p "$DEST/$STAMP"
```
- バックアップ先に `年月日_時分秒` 形式の新しいディレクトリを作成

#### 4. rsync でファイル同期
```bash
rsync -a --delete --exclude 'node_modules' --exclude '.venv' \
  --link-dest="$DEST/latest" "$SRC/" "$DEST/$STAMP/" | tee "$LOG"
```
- `-a`: アーカイブモード（権限・タイムスタンプなど保持）
- `--delete`: ソースに存在しないファイルをバックアップ先から削除
- `--exclude`: `node_modules` と `.venv` を除外（容量節約）
- `--link-dest="$DEST/latest"`: 前回バックアップ（latest）との差分のみコピー、変わらないファイルはハードリンク（容量・速度最適化）
- `| tee "$LOG"`: 出力をログファイルとコンソール両方に表示

#### 5. 最新バージョンのシンボリックリンク更新
```bash
ln -sfn "$DEST/$STAMP" "$DEST/latest"
```
- `-s`: シンボリックリンク作成
- `-f`: 既存リンクを上書き
- `-n`: リンク先がディレクトリでも追従しない
- `latest` を新しいバックアップディレクトリ（$STAMP）に指す

#### 6. 30日以上前のバックアップを削除
```bash
find "$DEST" -maxdepth 1 -type d -name '20*' -mtime +30 -exec rm -rf {} +
```
- `-maxdepth 1`: 直下のディレクトリのみ対象
- `-type d -name '20*'`: 「20」で始まるディレクトリ（タイムスタンプ形式）を検索
- `-mtime +30`: 30日以上前に変更されたもの
- `-exec rm -rf {} +`: マッチしたディレクトリとその内容を削除

#### 7. 保持世代数をカウント・表示
```bash
COUNT=$(find "$DEST" -maxdepth 1 -type d -name '20*' | wc -l | tr -d ' ')
echo "完了: $STAMP (保持している世代: $COUNT)"
```
- 現在保持している世代数をカウント
- 完了メッセージを出力

---

### 注意点

- **外部ストレージへのアクセス**: `/Volumes/Backup` がマウントされていることが必須です。未マウント時はエラーで終了します
- **ファイル削除**: `--delete` オプションにより、ソースに存在しないファイルはバックアップ先から削除されます。誤った設定では重要なファイルが失われる可能性があります
- **古い世代の削除**: 30日以上前のディレクトリは `rm -rf` で完全削除され、取り消せません
- **権限要件**: `$HOME/Documents/projects` の読み取り、`/Volumes/Backup/projects` への書き込み権限が必要です
- **ハードリンク活用**: ディスク容量は節約されますが、複数世代で同じデータを参照するため、バックアップ先のディスク容量は確認が必要です

---

### まとめ

**このスクリプトは、プロジェクトディレクトリを外部ストレージに差分バックアップし、ハードリンクで容量を最適化しつつ、30日以上前の古い世代を自動削除します。** 定期実行により、限定された容量の中で履歴を保持できるバックアップシステムを構築するのが目的と考えられます。
`````

### bash 中 / haiku / 2回目

最初の文字まで 7.2秒、完了まで 18.9秒、2469字。

`````markdown
**ホームディレクトリの `Documents/projects` フォルダを、外部ドライブ `/Volumes/Backup/projects` に世代管理してバックアップし、古い世代を自動削除するスクリプト。** タイムスタンプ付きディレクトリで世代を保管し、ハードリンク機能で容量を効率化します。

---

### ステップ別の詳細解説

#### 1. 初期設定とエラーハンドリング
```bash
set -euo pipefail
```
- **`set -e`**: コマンド実行に失敗した時点でスクリプト中断
- **`set -u`**: 未定義変数の参照でエラー
- **`set -o pipefail`**: パイプライン内のコマンド失敗を検知

#### 2. バックアップパスの定義
```bash
SRC="$HOME/Documents/projects"
DEST="/Volumes/Backup/projects"
STAMP=$(date +%Y%m%d_%H%M%S)
LOG="$DEST/backup_$STAMP.log"
```
- **`SRC`**: バックアップ元（`~/Documents/projects`）
- **`DEST`**: バックアップ先（外部ドライブ）
- **`STAMP`**: タイムスタンプ（例: `20261011_143022`）を生成
- **`LOG`**: ログファイルをバックアップ先に保存

#### 3. バックアップ先の存在確認
```bash
if [ ! -d "$DEST" ]; then
  echo "バックアップ先が見つかりません: $DEST" >&2
  exit 1
fi
```
- バックアップ先ディレクトリが存在しない場合、エラーメッセージを出力して終了
- 外部ドライブがマウントされていない場合に処理を防止

#### 4. バックアップ用ディレクトリの作成
```bash
mkdir -p "$DEST/$STAMP"
```
- 必要に応じて親ディレクトリを含めて作成（`-p` オプション）
- 例: `/Volumes/Backup/projects/20261011_143022`

#### 5. rsync によるバックアップ実行
```bash
rsync -a --delete --exclude 'node_modules' --exclude '.venv' \
  --link-dest="$DEST/latest" "$SRC/" "$DEST/$STAMP/" | tee "$LOG"
```
- **`-a`**: アーカイブモード（パーミッション・タイムスタンプ保持）
- **`--delete`**: 元フォルダで削除されたファイルもバックアップから削除
- **`--exclude`**: `node_modules` と `.venv` は除外
- **`--link-dest="$DEST/latest"`**: 前回バックアップ（latest）との差分をハードリンクで再利用→容量節約
- **`| tee "$LOG"`**: 実行内容をログファイルに記録しながら標準出力にも表示

#### 6. 最新バージョンへのシンボリックリンク作成
```bash
ln -sfn "$DEST/$STAMP" "$DEST/latest"
```
- **`-s`**: シンボリックリンク作成
- **`-f`**: 既存のリンクがあれば上書き
- **`-n`**: リンク先がディレクトリの場合の動作を制御
- `latest` → 最新バックアップへのショートカット

#### 7. 30日以上前のバックアップを削除
```bash
find "$DEST" -maxdepth 1 -type d -name '20*' -mtime +30 -exec rm -rf {} +
```
- **`-maxdepth 1`**: 1階層下まで（サブフォルダの中は検索しない）
- **`-type d`**: ディレクトリのみ対象
- **`-name '20*'`**: タイムスタンプ形式（`20xxxxxx`）のディレクトリ
- **`-mtime +30`**: 修正日時が30日より古い
- **`-exec rm -rf {} +`**: 該当ディレクトリを削除

#### 8. 保持している世代数を表示
```bash
COUNT=$(find "$DEST" -maxdepth 1 -type d -name '20*' | wc -l | tr -d ' ')
echo "完了: $STAMP (保持している世代: $COUNT)"
```
- タイムスタンプ形式のディレクトリを数えて表示

---

### 注意点

- **ディレクトリ削除**: `rm -rf` により30日以上前のバックアップが**完全に削除**される（復旧不可）
- **外部ドライブ依存**: `/Volumes/Backup` がマウントされていない場合、バックアップは失敗
- **権限**: バックアップ先への読み書き権限が必要
- **ハードリンク機能**: ファイルシステムがハードリンク対応である必要がある（NTFS は非対応）
- **実行中の上書き**: `--delete` により、バックアップ元で削除されたファイルは世代内からも削除される

---

### まとめ

**このスクリプトは、毎回最新のバックアップとの差分のみを保存することで容量を節約しながら、複数世代のプロジェクトフォルダを外部ドライブに自動保管し、30日より古い古い世代を自動削除します。** 定期実行（cron など）に向いています。
`````

## bash 大

### bash 大 / sonnet / 1回目

最初の文字まで 1.3秒、完了まで 19.9秒、4280字。

`````markdown
このスクリプトは、GitHub から `webapp` の指定ブランチ（既定は `main`）を新しいリリースディレクトリへ取得し、依存インストール・DBバックアップ・マイグレーションを行ったうえで、`current` シンボリックリンクを切り替えてサービスを再起動する本番デプロイ処理です。ヘルスチェックに失敗すれば直前のリリースへロールバックし、成功すれば古いリリースとバックアップを削除します。`set -euo pipefail` により、コマンド失敗・未定義変数・パイプ途中の失敗で即座に中断します。

---

### ステップ別の詳細解説

#### 1. 変数定義と補助関数
```bash
set -euo pipefail
APP_NAME="webapp"
DEPLOY_ROOT="/srv/$APP_NAME"
RELEASES="$DEPLOY_ROOT/releases"
SHARED="$DEPLOY_ROOT/shared"
CURRENT="$DEPLOY_ROOT/current"
KEEP=5
REPO="git@github.com:example/$APP_NAME.git"
BRANCH="${1:-main}"
STAMP=$(date +%Y%m%d%H%M%S)
NEW="$RELEASES/$STAMP"
HEALTH_URL="http://127.0.0.1:8080/healthz"
log() { ... }
die() { ... }
```
- `set -euo pipefail`：エラー・未定義変数・パイプ内エラーで停止します。
- `/srv/webapp` 配下に `releases/`（世代別）、`shared/`（共有物）、`current`（現行リリースへのリンク）を使う構成です。
- `BRANCH`：第1引数、なければ `main`。
- `STAMP`：タイムスタンプ。新リリースのディレクトリ名になります。
- `log` は時刻付きメッセージ出力、`die` はエラー表示して終了する関数です。

#### 2. ロールバック関数
```bash
rollback() {
  local prev
  prev=$(ls -1 "$RELEASES" | sort | tail -n 2 | head -n 1)
  [ -n "$prev" ] || die "戻せるリリースがありません"
  ln -sfn "$RELEASES/$prev" "$CURRENT"
  sudo systemctl restart "$APP_NAME"
}
```
- リリースを昇順に並べ、後ろから2番目（＝新リリースの1つ前）を選びます。
- `ln -sfn`：`current` のリンク先を前のリリースに張り替えます。
- `sudo systemctl restart`：サービスを再起動します（管理者権限を使用）。

#### 3. 事前チェック
```bash
command -v git >/dev/null || die "git がありません"
command -v uv >/dev/null || die "uv がありません"
[ -d "$SHARED" ] || die "$SHARED がありません"
FREE_KB=$(df -k "$DEPLOY_ROOT" | awk 'NR==2 {print $4}')
```
- `git`・`uv` の存在と共有ディレクトリの有無を確認します。
- `df` で空き容量を調べ、1GB（1048576KB）未満なら中止します。

#### 4. ソース取得
```bash
git clone --depth 1 --branch "$BRANCH" "$REPO" "$NEW"
REV=$(git -C "$NEW" rev-parse --short HEAD)
```
- SSH 経由で GitHub から最新コミットのみ（shallow）をクローンします。
- 短縮コミットハッシュを `REV` に保存します。

#### 5. 共有ファイルのリンク
```bash
ln -s "$SHARED/.env" "$NEW/.env"
ln -s "$SHARED/uploads" "$NEW/uploads"
ln -s "$SHARED/log" "$NEW/log"
```
- 設定（`.env`）・アップロード・ログを世代間で共有するためのシンボリックリンクです。

#### 6. 依存インストールと静的ファイル生成
```bash
(cd "$NEW" && uv sync --frozen --no-dev)
(cd "$NEW" && uv run python manage.py collectstatic --noinput >/dev/null)
```
- `uv sync --frozen --no-dev`：ロックファイル通りに本番用依存のみをインストールします（ネットワークアクセスあり）。
- `collectstatic`：Django の静的ファイルを集約します。出力は破棄されます。

#### 7. DBバックアップ
```bash
pg_dump "$APP_NAME" | gzip > "$SHARED/backup/pre_$STAMP.sql.gz"
```
- PostgreSQL の `webapp` データベースをダンプして圧縮保存します。

#### 8. マイグレーション
```bash
if ! (cd "$NEW" && uv run python manage.py migrate --noinput); then
  rm -rf "$NEW"
  die "マイグレーションに失敗しました"
fi
```
- DB スキーマを更新します。失敗時は新リリースのディレクトリを削除して中止します。

#### 9. 切り替えと再起動
```bash
ln -sfn "$NEW" "$CURRENT"
sudo systemctl restart "$APP_NAME"
```
- `current` を新リリースへ向け、サービスを再起動します。ここから本番に反映されます。

#### 10. ヘルスチェックとロールバック
```bash
for i in $(seq 1 10); do
  if curl -fsS --max-time 3 "$HEALTH_URL" >/dev/null; then ok=1; break; fi
  sleep 2
done
if [ "$ok" -ne 1 ]; then rollback; exit 1; fi
```
- 最大10回（2秒間隔）`/healthz` を確認します。全部失敗なら `rollback` を実行して異常終了します。

#### 11. 後片付けと記録
```bash
ls -1 "$RELEASES" | sort | head -n -"$KEEP" | while read -r old; do
  rm -rf "${RELEASES:?}/$old"
done
find "$SHARED/backup" -name 'pre_*.sql.gz' -mtime +14 -delete
echo "$STAMP $REV $BRANCH $(whoami)" >> "$SHARED/log/deploy.log"
```
- 新しい5世代を残して古いリリースを `rm -rf` で削除します。
- 14日より古い `pre_*.sql.gz` バックアップを削除します。
- デプロイ履歴（日時・リビジョン・ブランチ・実行ユーザー）を `deploy.log` に追記します。

---

### 注意点
- **本番環境への影響**：`current` の切り替えとサービス再起動で、稼働中アプリが即座に新バージョンに置き換わり、短時間の断が起こりえます。
- **`sudo` の使用**：`systemctl restart` に管理者権限を使います。パスワード入力が必要な環境では途中で止まる可能性があります。
- **DBマイグレーションは元に戻らない**：ロールバックはコードのみで、DBスキーマは戻りません。新スキーマと旧コードが非互換だと、ロールバック後も不具合が残る恐れがあります。バックアップからの復元は手動です。
- **`rm -rf` による削除**：古いリリース（5世代超）とマイグレーション失敗時の新リリースを削除します。`${RELEASES:?}` で変数が空の場合の事故は防いでいます。
- **バックアップ削除**：14日超の DB バックアップを自動削除します。
- **ロールバック判定の注意（推測を含む）**：`ls | sort | tail -n 2 | head -n 1` は「直前のリリース」を選ぶ前提です。リリースが1つしかない場合、新リリース自身を選んでしまい意味のないロールバックになる可能性があります。
- **`pg_dump` の認証**：接続先・認証は環境依存で、入力からは判別できません（`PG*` 環境変数や peer 認証を想定していると推測されます）。
- **外部通信**：GitHub への SSH 接続（`git clone`）と、`uv sync` による依存パッケージの取得が発生します。
- **実行環境の差**：パスが `/srv/webapp` であり、作業ディレクトリ（`~/work/sample`）とは無関係にサーバー側ディレクトリを操作します。実行先マシンが意図した本番／ステージングかを確認してください。

---

### まとめ
**`webapp` の最新コードを新リリースとして取得・構築し、DBバックアップとマイグレーションを経て本番へ切り替える自動デプロイ**です。ヘルスチェック失敗時は**前リリースへ戻し**、成功時は古いリリースとバックアップを整理します。
`````

### bash 大 / sonnet / 2回目

最初の文字まで 1.3秒、完了まで 18.6秒、4355字。

`````markdown
このスクリプトは、`webapp` アプリを `/srv/webapp` 配下に新リリースとしてデプロイします。Git から取得、依存インストール、DBバックアップ、マイグレーション、シンボリックリンク切り替え、サービス再起動、ヘルスチェックを行い、失敗時はロールバックします。成功時は古いリリースとバックアップも削除します。`set -euo pipefail` により、エラー・未定義変数・パイプの失敗で即座に停止します。

---

### ステップ別の詳細解説

#### 1. 初期設定と変数定義
```bash
set -euo pipefail
APP_NAME="webapp"
DEPLOY_ROOT="/srv/$APP_NAME"
RELEASES="$DEPLOY_ROOT/releases"
SHARED="$DEPLOY_ROOT/shared"
CURRENT="$DEPLOY_ROOT/current"
KEEP=5
REPO="git@github.com:example/$APP_NAME.git"
BRANCH="${1:-main}"
STAMP=$(date +%Y%m%d%H%M%S)
NEW="$RELEASES/$STAMP"
HEALTH_URL="http://127.0.0.1:8080/healthz"
```
- `set -euo pipefail`：コマンド失敗、未定義変数の参照、パイプ途中の失敗でスクリプトを中断します。
- `RELEASES` / `SHARED` / `CURRENT`：リリース置き場、共有ファイル置き場、現行版を指すリンクのパスです。
- `KEEP=5`：残すリリース数です。
- `BRANCH="${1:-main}"`：第1引数のブランチ名を使い、なければ `main` になります。
- `STAMP`：現在時刻のタイムスタンプで、新リリースのディレクトリ名になります。

#### 2. ヘルパー関数
```bash
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }
rollback() {
  local prev
  prev=$(ls -1 "$RELEASES" | sort | tail -n 2 | head -n 1)
  [ -n "$prev" ] || die "戻せるリリースがありません"
  log "ロールバック: $prev"
  ln -sfn "$RELEASES/$prev" "$CURRENT"
  sudo systemctl restart "$APP_NAME"
}
```
- `log`：時刻付きでメッセージを表示します。
- `die`：エラーを表示して終了します。
- `rollback`：リリース一覧を昇順に並べ、後ろから2番目（直前のリリース）に `current` を張り替え、`sudo` でサービスを再起動します。

#### 3. 事前チェック
```bash
command -v git >/dev/null || die "git がありません"
command -v uv >/dev/null || die "uv がありません"
[ -d "$SHARED" ] || die "$SHARED がありません"

FREE_KB=$(df -k "$DEPLOY_ROOT" | awk 'NR==2 {print $4}')
if [ "$FREE_KB" -lt 1048576 ]; then
  die "空き容量が 1GB 未満です"
fi
```
- `git` と `uv` の存在、共有ディレクトリの存在を確認します。
- `df -k` で空き容量を取得し、1GB（1048576KB）未満なら中止します。

#### 4. ソースの取得
```bash
git clone --depth 1 --branch "$BRANCH" "$REPO" "$NEW"
REV=$(git -C "$NEW" rev-parse --short HEAD)
```
- `--depth 1`：最新コミットだけを取得する浅いクローンです。
- SSH 経由で GitHub に接続し、`$NEW` に展開します。
- `REV`：短縮コミットハッシュです。

#### 5. 共有ファイルのリンク
```bash
ln -s "$SHARED/.env" "$NEW/.env"
ln -s "$SHARED/uploads" "$NEW/uploads"
ln -s "$SHARED/log" "$NEW/log"
```
- 設定 `.env`、アップロード、ログを全リリースで共有するためのシンボリックリンクです。

#### 6. 依存インストールと静的ファイル生成
```bash
(cd "$NEW" && uv sync --frozen --no-dev)
(cd "$NEW" && uv run python manage.py collectstatic --noinput >/dev/null)
```
- `uv sync --frozen --no-dev`：ロックファイル通りに、開発用を除く依存をインストールします。
- `collectstatic --noinput`：Django の静的ファイルを対話なしで集めます（標準出力は破棄）。

#### 7. DBバックアップ
```bash
pg_dump "$APP_NAME" | gzip > "$SHARED/backup/pre_$STAMP.sql.gz"
```
- PostgreSQL の `webapp` データベースをダンプし、gzip 圧縮して保存します。

#### 8. マイグレーション
```bash
if ! (cd "$NEW" && uv run python manage.py migrate --noinput); then
  rm -rf "$NEW"
  die "マイグレーションに失敗しました"
fi
```
- DB スキーマを更新します。失敗時は新リリースを削除して中止します。

#### 9. 切り替えと再起動
```bash
ln -sfn "$NEW" "$CURRENT"
sudo systemctl restart "$APP_NAME"
```
- `current` を新リリースに張り替え、`sudo` でサービスを再起動します。

#### 10. ヘルスチェックとロールバック
```bash
for i in $(seq 1 10); do
  if curl -fsS --max-time 3 "$HEALTH_URL" >/dev/null; then ok=1; break; fi
  sleep 2
done
if [ "$ok" -ne 1 ]; then
  log "ヘルスチェックに失敗しました"
  rollback
  exit 1
fi
```
- 最大10回（2秒間隔）`/healthz` を確認します。成功しなければ `rollback` を呼んで終了します。

#### 11. 後片付けと記録
```bash
ls -1 "$RELEASES" | sort | head -n -"$KEEP" | while read -r old; do
  rm -rf "${RELEASES:?}/$old"
done
find "$SHARED/backup" -name 'pre_*.sql.gz' -mtime +14 -delete
echo "$STAMP $REV $BRANCH $(whoami)" >> "$SHARED/log/deploy.log"
```
- 新しい5件を除く古いリリースを `rm -rf` で削除します。
- 14日より古い `pre_*.sql.gz` バックアップを削除します。
- デプロイ履歴を `deploy.log` に追記します。

### 注意点
- **本番環境への変更**：`/srv/webapp` 配下の作成、`current` の切り替え、`sudo systemctl restart` によるサービス再起動が行われ、一時的に影響が出る可能性があります。
- **DBマイグレーションは巻き戻されません**：ヘルスチェック失敗時のロールバックはコードとリンクのみで、DBスキーマは元に戻りません。バックアップからの復元は手動です。
- **`rm -rf` による削除**：古いリリース（5件超）と、マイグレーション失敗時の新リリースが削除されます。古いバックアップ（14日超）も `-delete` で消えます。
- **ロールバックの前提**：直前のリリースが存在することが前提です。初回デプロイでは `tail -n 2 | head -n 1` が自分自身を指す可能性があります（推測）。
- **`pipefail` の影響**：`pg_dump` が失敗するとスクリプトは中断しますが、不完全なバックアップファイルが残る場合があります。
- **外部通信**：GitHub への SSH 接続、`uv sync` によるパッケージ取得（外部ネットワーク）が発生します。
- **想定外の実行環境**：作業ディレクトリは `~/work/sample` ですが、スクリプトは `/srv/webapp` を操作します。ローカル開発機では、必要なディレクトリ・DB・サービスがなく失敗する可能性が高いです（推測）。
- **`backup` ディレクトリ**：`$SHARED/backup` の存在は事前チェックされておらず、無ければ `pg_dump` の出力先で失敗します。

---

### まとめ
**Git から取得した最新コードを新リリースとして `/srv/webapp` に配置し、DBバックアップとマイグレーションの後にサービスを切り替える本番デプロイ**です。ヘルスチェック失敗時は前のリリースに戻し、成功時は古いリリースとバックアップを整理します。
`````

### bash 大 / haiku / 1回目

最初の文字まで 6.0秒、完了まで 24.9秒、4230字。

`````markdown
このスクリプトは、**Webアプリケーション（Python/Django想定）をGitから取得し、依存関係をインストール・マイグレーション実行後に切り替えるデプロイスクリプト**です。失敗時は自動的に前のリリースへロールバックします。

---

### ステップ別の詳細解説

#### 1. 環境変数の設定と関数定義

```bash
APP_NAME="webapp"
DEPLOY_ROOT="/srv/$APP_NAME"
RELEASES="$DEPLOY_ROOT/releases"
SHARED="$DEPLOY_ROOT/shared"
CURRENT="$DEPLOY_ROOT/current"
KEEP=5
REPO="git@github.com:example/$APP_NAME.git"
BRANCH="${1:-main}"
STAMP=$(date +%Y%m%d%H%M%S)
NEW="$RELEASES/$STAMP"
```

- `APP_NAME`：デプロイするアプリ名（`webapp`）
- `DEPLOY_ROOT`：デプロイ基盤パス（`/srv/webapp`）
- `RELEASES`：各リリースの保存場所
- `SHARED`：環境ファイル・ログなど複数リリース間で共有するファイルの格納場所
- `CURRENT`：現在使用中のリリースへのシンボリックリンク
- `KEEP`：保持する古いリリースの数（5個）
- `REPO`・`BRANCH`：GitリポジトリとブランチURL（デフォルト`main`）
- `STAMP`：タイムスタンプ（リリースID）

#### 2. 前提条件の確認

```bash
command -v git >/dev/null || die "git がありません"
command -v uv >/dev/null || die "uv がありません"
[ -d "$SHARED" ] || die "$SHARED がありません"

FREE_KB=$(df -k "$DEPLOY_ROOT" | awk 'NR==2 {print $4}')
if [ "$FREE_KB" -lt 1048576 ]; then
  die "空き容量が 1GB 未満です"
fi
```

- 必要なコマンド（`git`・`uv`）が存在するか確認
- 共有ディレクトリが存在するか確認
- デプロイパスがあるファイルシステムの空き容量が1GB以上あるか確認（不足なら中止）

#### 3. ソースコードの取得

```bash
log "取得: $REPO ($BRANCH)"
git clone --depth 1 --branch "$BRANCH" "$REPO" "$NEW"
REV=$(git -C "$NEW" rev-parse --short HEAD)
```

- リモートリポジトリから指定ブランチの最新1世代のみを新規ディレクトリ（`$NEW`）に取得
- コミットハッシュの短縮形を取得して記録

#### 4. 共有ファイルのシンボリックリンク

```bash
ln -s "$SHARED/.env" "$NEW/.env"
ln -s "$SHARED/uploads" "$NEW/uploads"
ln -s "$SHARED/log" "$NEW/log"
```

- 環境ファイル、アップロードディレクトリ、ログディレクトリを共有ディレクトリにシンボリックリンク
- リリースごとに異なるディレクトリではなく、永続的な共有リソースを使用

#### 5. 依存関係のインストール

```bash
(cd "$NEW" && uv sync --frozen --no-dev)
```

- 新規リリースディレクトリへ移動し、Pythonパッケージ管理ツール`uv`で依存関係をインストール
- `--frozen`：ロックファイルを信頼して厳密に再現性を確保
- `--no-dev`：開発依存を除外

#### 6. 静的ファイルの生成

```bash
(cd "$NEW" && uv run python manage.py collectstatic --noinput >/dev/null)
```

- Django管理コマンドで静的ファイル（CSS・JS等）を収集・生成
- `--noinput`：対話的確認をスキップ

#### 7. データベースのバックアップ

```bash
pg_dump "$APP_NAME" | gzip > "$SHARED/backup/pre_$STAMP.sql.gz"
```

- デプロイ前にPostgreSQLデータベース全体をダンプ
- gzip圧縮して`$SHARED/backup/`に保存（タイムスタンプ付き）

#### 8. マイグレーションの実行

```bash
if ! (cd "$NEW" && uv run python manage.py migrate --noinput); then
  rm -rf "$NEW"
  die "マイグレーションに失敗しました"
fi
```

- Django マイグレーションコマンド実行
- **失敗時は新規ディレクトリを削除し、スクリプト終了**

#### 9. シンボリックリンク切り替えとサービス再起動

```bash
ln -sfn "$NEW" "$CURRENT"
sudo systemctl restart "$APP_NAME"
```

- `CURRENT`シンボリックリンクを新しいリリースに切り替え（`-f`で上書き、`-n`でディレクトリを参照）
- `sudo`で`systemctl`を実行してアプリケーションサービスを再起動

#### 10. ヘルスチェック

```bash
ok=0
for i in $(seq 1 10); do
  if curl -fsS --max-time 3 "$HEALTH_URL" >/dev/null; then
    ok=1
    break
  fi
  sleep 2
done

if [ "$ok" -ne 1 ]; then
  log "ヘルスチェックに失敗しました"
  rollback
  exit 1
fi
```

- HTTPエンドポイント（`http://127.0.0.1:8080/healthz`）に最大10回、2秒間隔でリクエスト
- タイムアウトは3秒
- **成功すればデプロイ確定、失敗すれば`rollback`関数で前のリリースに戻す**

#### 11. `rollback`関数（自動ロールバック）

```bash
rollback() {
  local prev
  prev=$(ls -1 "$RELEASES" | sort | tail -n 2 | head -n 1)
  [ -n "$prev" ] || die "戻せるリリースがありません"
  log "ロールバック: $prev"
  ln -sfn "$RELEASES/$prev" "$CURRENT"
  sudo systemctl restart "$APP_NAME"
}
```

- 直前のリリース（2番目に新しい）を特定
- `CURRENT`シンボリックリンクをそれに切り替え
- サービスを再起動

#### 12. 古いリリースとバックアップの削除

```bash
ls -1 "$RELEASES" | sort | head -n -"$KEEP" | while read -r old; do
  rm -rf "${RELEASES:?}/$old"
done

find "$SHARED/backup" -name 'pre_*.sql.gz' -mtime +14 -delete
```

- `$RELEASES`内で古い順に、保持数（5個）を超える分をディレクトリごと削除
- `$SHARED/backup`内で14日以上前のバックアップファイル（`pre_*.sql.gz`）を削除

#### 13. デプロイログへの記録

```bash
echo "$STAMP $REV $BRANCH $(whoami)" >> "$SHARED/log/deploy.log"
```

- 成功時にタイムスタンプ、コミットハッシュ、ブランチ、実行ユーザーをログファイルに追記

---

### 注意点

- **`sudo systemctl restart` 実行**：このスクリプト実行ユーザーが`sudo`でシステムコマンドを実行する権限が必要
- **絶対パス `/srv/webapp` の操作**：このパスのディレクトリ・ファイルが存在し、スクリプト実行ユーザーが読み書き権限を持つ必要があります
- **PostgreSQL へのアクセス**：`pg_dump`を実行できる権限が必要（通常、dbユーザーなど）
- **Git SSH 認証**：リポジトリが`git@github.com:...`形式なため、SSH秘密鍵の設定が必須です
- **古いリリース削除は取り消せない**：`rm -rf`で削除されるため、復旧不可
- **マイグレーション失敗時は新規ディレクトリ削除**：失敗時は新規リリースディレクトリごと削除されます
- **ヘルスチェック失敗で自動ロールバック**：前のリリースが存在しない場合は`die`で終了

---

### まとめ

**このスクリプトは、GitリポジトリからWebアプリケーションを取得し、依存関係のインストール・データベースマイグレーション・サービス再起動を実行してから、ヘルスチェックで正常動作を確認するデプロイパイプラインです。失敗時の自動ロールバック機能と、古いリリース・古いバックアップの自動削除機能を備えています。**
`````

### bash 大 / haiku / 2回目

最初の文字まで 9.6秒、完了まで 28.9秒、4536字。

`````markdown
# Bash スクリプト実行確認：アプリデプロイ

このスクリプトは、**Git リポジトリから最新コードを取得し、依存関係をインストール・マイグレーションを実行してから、サービスを切り替え・再起動する自動デプロイメント処理**です。ヘルスチェックに失敗した場合は自動的に前バージョンへロールバックします。

---

### ステップ別の詳細解説

#### 1. 初期化と環境変数設定

```bash
APP_NAME="webapp"
DEPLOY_ROOT="/srv/$APP_NAME"
RELEASES="$DEPLOY_ROOT/releases"
SHARED="$DEPLOY_ROOT/shared"
CURRENT="$DEPLOY_ROOT/current"
KEEP=5
REPO="git@github.com:example/$APP_NAME.git"
BRANCH="${1:-main}"
STAMP=$(date +%Y%m%d%H%M%S)
```

- **APP_NAME**: デプロイ対象アプリの名前（`webapp`）
- **DEPLOY_ROOT**: アプリケーション全体の配置先（`/srv/webapp`）
- **RELEASES**: 各リリースバージョンを保存するディレクトリ
- **SHARED**: 環境設定や永続化ファイル（.env, uploads, log）の共有ディレクトリ
- **CURRENT**: 現在実行中のバージョンを示すシンボリックリンク
- **KEEP**: 保持するリリース数（古い順に削除される）
- **REPO**: Git リポジトリURL
- **BRANCH**: デプロイするブランチ（第1引数で指定、デフォルトは `main`）
- **STAMP**: 今回のデプロイタイムスタンプ（リリースディレクトリ名として使用）

#### 2. ヘルパー関数の定義

```bash
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }
rollback() { ... }
```

- **log**: 時刻付きログを標準出力に出力
- **die**: エラーメッセージを出力して終了
- **rollback**: 1つ前のリリースに切り替えてサービスを再起動

#### 3. 前提条件チェック

```bash
command -v git >/dev/null || die "git がありません"
command -v uv >/dev/null || die "uv がありません"
[ -d "$SHARED" ] || die "$SHARED がありません"

FREE_KB=$(df -k "$DEPLOY_ROOT" | awk 'NR==2 {print $4}')
if [ "$FREE_KB" -lt 1048576 ]; then
  die "空き容量が 1GB 未満です"
fi
```

- **コマンド確認**: git と uv (Python 管理ツール) の存在確認
- **ディレクトリ確認**: 共有ディレクトリが存在するか確認
- **ディスク容量確認**: デプロイ先に1GB 以上の空き容量があるか確認（不足時は中止）

#### 4. リポジトリをクローン

```bash
log "取得: $REPO ($BRANCH)"
git clone --depth 1 --branch "$BRANCH" "$REPO" "$NEW"
REV=$(git -C "$NEW" rev-parse --short HEAD)
log "リビジョン: $REV"
```

- **git clone**: 指定ブランチのみを浅くクローン（`--depth 1` で高速化）
- **NEW**: 今回のデプロイ先ディレクトリパス
- **REV**: クローンしたコミットの短縮SHA（ログ記録用）

#### 5. 共有ファイルをシンボリックリンク

```bash
ln -s "$SHARED/.env" "$NEW/.env"
ln -s "$SHARED/uploads" "$NEW/uploads"
ln -s "$SHARED/log" "$NEW/log"
```

- **.env**: 環境変数ファイル（機密情報など）
- **uploads**: ユーザーアップロードファイル（永続化が必要）
- **log**: ログファイル（複数リリース間で共有）

すべてのリリースバージョン間で共通の設定・データを指します。

#### 6. 依存関係をインストール

```bash
(cd "$NEW" && uv sync --frozen --no-dev)
```

- **uv sync**: Python 依存パッケージをロックファイルから確定的にインストール
- **--frozen**: ロックファイルを変更しない
- **--no-dev**: 開発用パッケージを除外

#### 7. 静的ファイルを生成

```bash
(cd "$NEW" && uv run python manage.py collectstatic --noinput >/dev/null)
```

- **collectstatic**: Django の静的ファイル（CSS, JS, 画像）を収集・最適化
- **--noinput**: ユーザー入力を待たない（非対話実行）

#### 8. データベースをバックアップ

```bash
pg_dump "$APP_NAME" | gzip > "$SHARED/backup/pre_$STAMP.sql.gz"
```

- PostgreSQL データベースを SQL ダンプしてgzip 圧縮
- ファイル名に `pre_` とタイムスタンプを付与（デプロイ前のバージョン特定用）

#### 9. マイグレーション実行

```bash
if ! (cd "$NEW" && uv run python manage.py migrate --noinput); then
  rm -rf "$NEW"
  die "マイグレーションに失敗しました"
fi
```

- **migrate**: Django データベーススキーマ変更を実行
- 失敗時は新リリースディレクトリを削除してスクリプト終了

#### 10. サービス切り替えと再起動

```bash
ln -sfn "$NEW" "$CURRENT"
sudo systemctl restart "$APP_NAME"
```

- **ln -sfn**: `current` シンボリックリンクを新バージョンに切り替え（`-f` で上書き）
- **systemctl restart**: アプリケーションサービスを再起動（`sudo` で昇格実行）

#### 11. ヘルスチェック（最大20秒間）

```bash
ok=0
for i in $(seq 1 10); do
  if curl -fsS --max-time 3 "$HEALTH_URL" >/dev/null; then
    ok=1
    break
  fi
  sleep 2
done

if [ "$ok" -ne 1 ]; then
  log "ヘルスチェックに失敗しました"
  rollback
  exit 1
fi
```

- **curl**: 健全性確認API（`http://127.0.0.1:8080/healthz`）を呼び出し
- 最大10回、2秒間隔でリトライ（合計最大20秒）
- **失敗時**: `rollback()` で1つ前バージョンに自動切り替え、スクリプト中止

#### 12. 古いリリースを削除

```bash
ls -1 "$RELEASES" | sort | head -n -"$KEEP" | while read -r old; do
  rm -rf "${RELEASES:?}/$old"
done
```

- 最新から数えて `$KEEP` 個（デフォルト5個）を残す
- それより古いリリースディレクトリを完全削除

#### 13. 古いバックアップを削除

```bash
find "$SHARED/backup" -name 'pre_*.sql.gz' -mtime +14 -delete
```

- 14日以上前のバックアップを自動削除（ストレージ節約）

#### 14. デプロイログ記録

```bash
echo "$STAMP $REV $BRANCH $(whoami)" >> "$SHARED/log/deploy.log"
log "完了: $STAMP ($REV)"
```

- デプロイ時刻、コミットSHA、ブランチ、実行ユーザーをログファイルに追記

---

### 注意点

- **リリース削除**: 古いリリースが`$KEEP`個を超えると自動削除されるため、必要な過去バージョンは保持できません
- **sudo 権限必須**: `systemctl restart` 実行時にrootやsudo権限が必要です
- **PostgreSQL 依存**: データベースバックアップに `pg_dump` を使用するため、PostgreSQL がインストール・実行中である必要があります
- **デプロイ先ディレクトリ**: `/srv/webapp` とその配下（`releases`, `shared`）の存在と書き込み権限が必須です
- **ロールバック自動実行**: ヘルスチェック失敗時に自動的に前バージョンに切り替わるため、手動介入の時間がありません
- **マイグレーション失敗時の動作**: マイグレーション失敗時は新リリースが削除されますが、DB は既に変更されている可能性があります
- **Git SSH鍵**: リポジトリ取得時に `git@github.com` を使用するため、SSH鍵認証が設定されている必要があります

---

### まとめ

**このスクリプトは、Web アプリケーションの自動デプロイパイプラインを実装しており、最新コードの取得から DB マイグレーション、サービス切り替え、ヘルスチェック、そして失敗時の自動ロールバックまでを一連で処理します。古いバージョンも履歴として保持する仕組みになっています。**
`````

## python 小

### python 小 / sonnet / 1回目

最初の文字まで 1.3秒、完了まで 7.2秒、1166字。

`````markdown
カレントディレクトリ（`~/work/sample`）にある `package.json` を Python で読み込み、プロジェクトの名前とバージョンを標準出力に表示するだけの読み取り専用コマンドです。連結演算子（`&&`・`;`・`|`）は使われておらず、単一のコマンドです。

---

### ステップ別の詳細解説

#### 1. Python のワンライナー実行

```
python3 -c "import json,sys; d=json.load(open('package.json')); print(d['name'], d['version'])"
```

- `python3 -c "..."`: 引数の文字列を Python のコードとして直接実行します。スクリプトファイルは作成されません。
- `import json,sys`: JSON を扱う標準ライブラリ `json` と `sys` を読み込みます。`sys` はこのコード内では使われていません（無害です）。
- `json.load(open('package.json'))`: カレントディレクトリの `package.json` を読み取り用で開き、JSON を辞書として `d` に格納します。ファイルを書き換える操作はありません。
- `print(d['name'], d['version'])`: `name` と `version` の値をスペース区切りで出力します（例: `my-app 1.0.0`）。
- 補足: `open()` で開いたファイルは明示的に閉じられていませんが、プログラムはすぐ終了するため実害はありません。

### 注意点

- 読み取りのみで、ファイルの削除・上書き・ネットワーク通信は行いません。
- `package.json` が存在しない場合は `FileNotFoundError`、`name` や `version` キーが無い場合は `KeyError` でエラー終了します（その場合も何も変更されません）。
- 相対パスで指定しているため、作業ディレクトリ内の `package.json` が対象になります。なお、Python は `-c` 実行時にカレントディレクトリからモジュールを読み込むため、同ディレクトリに `json.py` などの紛らわしいファイルがあるとそちらが読み込まれる可能性があります（信頼できないリポジトリでなければ通常は問題ありません）。

---

### まとめ

**`package.json` からプロジェクト名とバージョンを読み取って表示する**だけの安全な読み取り専用コマンドで、システムやファイルへの変更はありません。
`````

### python 小 / sonnet / 2回目

最初の文字まで 2.0秒、完了まで 7.4秒、1064字。

`````markdown
このコマンドは、作業ディレクトリ(`~/work/sample`)にある `package.json` を Python で読み込み、プロジェクト名とバージョンを1行で表示します。ファイルの読み取りと標準出力への表示だけで、何も変更しません。

---

### ステップ別の詳細解説

#### 1. Python のワンライナー実行

```bash
python3 -c "import json,sys; d=json.load(open('package.json')); print(d['name'], d['version'])"
```

- `python3 -c "..."`: 引数の文字列を Python のコードとして実行します。スクリプトファイルは作りません。
- `import json,sys`: JSON を扱う `json` モジュールと `sys` モジュールを読み込みます。`sys` はこのコード内で使われておらず、無害ですが不要です。
- `json.load(open('package.json'))`: カレントディレクトリの `package.json` を読み取り用で開き、JSON を辞書として解析して `d` に代入します。ファイルを閉じる処理は明示されていません(短命のプロセスなので実害はありません)。
- `print(d['name'], d['version'])`: `name` と `version` の値をスペース区切りで標準出力に表示します。例: `my-app 1.0.0`

### 注意点

- 読み取り専用の操作です。ファイルの書き換え、削除、ネットワーク通信は行いません。
- `package.json` が存在しない場合は `FileNotFoundError`、`name` や `version` キーが無い場合は `KeyError` で失敗します。失敗しても副作用はありません。
- カレントディレクトリの `json.py` などがあると、標準モジュールの代わりに読み込まれる可能性があります。ただし、ここでは `~/work/sample` が作業ディレクトリです。信頼できないリポジトリの場合は、`-I` オプションを付けると安全です(推測を含みます)。

---

### まとめ

**`package.json` からプロジェクト名とバージョンを読み取って表示する**だけの、副作用のない安全な確認コマンドです。
`````

### python 小 / haiku / 1回目

最初の文字まで 6.4秒、完了まで 11.7秒、1183字。

`````markdown
このコマンドは、**作業ディレクトリ `~/work/sample` にある `package.json` ファイルから `name` と `version` フィールドを抽出して標準出力に表示**するものです。

---

### ステップ別の詳細解説

#### 1. Python インタプリタの起動とコード実行

```
python3 -c "import json,sys; d=json.load(open('package.json')); print(d['name'], d['version'])"
```

- **`python3`** — Python 3 インタプリタを起動
- **`-c`** — 続く文字列をPython コードとして実行するオプション
- **`import json,sys`** — JSON 処理用の `json` モジュール（および `sys` モジュール）をインポート

#### 2. ファイルの読み込みと JSON パース

- **`open('package.json')`** — 現在のディレクトリ（~/work/sample）から `package.json` ファイルを開く
- **`json.load(...)`** — ファイルの内容を JSON として解析し、Python の辞書オブジェクト `d` に格納

#### 3. データの抽出と表示

- **`d['name']`** — JSON オブジェクトから `name` キーの値を取得
- **`d['version']`** — JSON オブジェクトから `version` キーの値を取得
- **`print(...)`** — 取得した2つの値をスペース区切りで標準出力に表示

### 注意点

- **ファイル存在の前提** — `package.json` がディレクトリ `~/work/sample` に存在する必要があります。なければエラーが発生します
- **JSON 形式の妥当性** — ファイルが正しい JSON 形式である必要があります。形式が不正だとパースエラーになります
- **必須フィールド** — `name` および `version` キーが JSON 内に存在しないとエラーになります
- **ファイル読み取り権限** — ファイルが読み取り可能である必要があります

---

### まとめ

**このコマンドは、カレントディレクトリの `package.json` から `name` と `version` の値を読み込み、それらをコンソールに出力します。**Node.js プロジェクトやその他のパッケージの メタデータを素早く確認する際に使われる操作です。
`````

### python 小 / haiku / 2回目

最初の文字まで 10.6秒、完了まで 14.2秒、1134字。

`````markdown
~/work/sample ディレクトリ内の `package.json` ファイルを開き、その中から `name` と `version` フィールドの値を抽出して表示します。

---

### ステップ別の詳細解説

#### 1. Python3 の起動とモジュールインポート

```bash
python3 -c "import json,sys; d=json.load(open('package.json')); print(d['name'], d['version'])"
```

- `python3` : Python 3 インタプリタを起動
- `-c` : 後に続く文字列を Python コードとして実行
- `import json,sys` : JSON 処理モジュールとシステムモジュールをインポート

#### 2. package.json の読み込みと解析

- `open('package.json')` : 作業ディレクトリの `package.json` ファイルをテキストモードで開く
- `json.load()` : ファイルの内容を JSON 形式として解析し、Python 辞書に変換
- `d=` : 解析結果を変数 `d` に代入

#### 3. name と version の抽出と表示

- `d['name']` : JSON オブジェクトの `name` フィールドにアクセス
- `d['version']` : JSON オブジェクトの `version` フィールドにアクセス
- `print()` : 2つの値をスペース区切りで標準出力に表示

---

### 注意点

- **ファイルが存在しない場合** : `package.json` が ~/work/sample に存在しないと、ファイルオープンエラーで実行が失敗します
- **JSON 形式のエラー** : ファイルの内容が正しい JSON 形式でないと、解析エラーで失敗します
- **フィールド欠落** : `name` または `version` フィールドが JSON に存在しないと、キーエラーで失敗します
- **リソースリーク** : `open()` で開いたファイルハンドルが明示的に閉じられていません（ただしスクリプト終了時には自動的にクローズされます）

---

### まとめ

**作業ディレクトリ内の `package.json` から `name` と `version` フィールドを読み取り、コンソールに表示する操作です。**ファイルは読み込まれるだけで変更は加わりません。
`````

## python 中

### python 中 / sonnet / 1回目

最初の文字まで 1.3秒、完了まで 11.4秒、2647字。

`````markdown
この操作は、`data/` フォルダ内の `sales_*.csv` をすべて読み込み、カテゴリ別に件数・合計・平均を集計して、作業ディレクトリ直下の `summary.csv` に書き出します。Python スクリプトをヒアドキュメント（`<<'EOF'`）で標準入力から渡して実行する形で、コマンドの連結（`&&`・`;`・`|`）はありません。

---

### ステップ別の詳細解説

#### 1. Python をヒアドキュメントで起動する

```bash
python3 - <<'EOF'
...
EOF
```

- `python3 -` : 標準入力からスクリプトを読み込んで実行します。
- `<<'EOF'` : 終端の `EOF` までをスクリプト本文として渡します。`'EOF'` と引用符が付いているため、シェルによる変数展開は行われず、本文はそのまま Python に渡されます。

#### 2. 集計用の準備

```python
import csv
from collections import defaultdict
from pathlib import Path

totals = defaultdict(float)
counts = defaultdict(int)
```

- `csv`, `defaultdict`, `Path` : CSV の読み書き、初期値付き辞書、パス操作に使う標準ライブラリです。
- `totals` : カテゴリごとの金額合計（初期値 0.0）。
- `counts` : カテゴリごとの件数（初期値 0）。

#### 3. 売上 CSV の読み込みと集計

```python
for path in sorted(Path("data").glob("sales_*.csv")):
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not row["amount"]:
                continue
            totals[row["category"]] += float(row["amount"])
            counts[row["category"]] += 1
```

- `Path("data").glob("sales_*.csv")` : `data/` 内の `sales_` で始まる CSV を列挙します。`sorted` でファイル名順に処理します。
- `path.open(encoding="utf-8", newline="")` : 読み取り専用で開きます（UTF-8 指定）。
- `csv.DictReader(f)` : 1行目をヘッダーとして、各行を辞書として読みます。
- `if not row["amount"]: continue` : `amount` が空欄の行を飛ばします。
- `float(row["amount"])` : 金額を数値化してカテゴリ別に加算し、件数も1増やします。
- 推測：`amount` や `category` 列が存在しないファイルがあると `KeyError` で停止します。また、数値でない値があると `ValueError` になります。

#### 4. summary.csv への書き出し

```python
with open("summary.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "count", "total", "average"])
    for category in sorted(totals, key=totals.get, reverse=True):
        total = totals[category]
        n = counts[category]
        writer.writerow([category, n, round(total), round(total / n, 1)])
```

- `open("summary.csv", "w", ...)` : 作業ディレクトリ直下の `summary.csv` を書き込みモードで開きます。**同名ファイルが既にあれば内容は上書きされます。**
- ヘッダー行 `category, count, total, average` を出力します。
- `sorted(totals, key=totals.get, reverse=True)` : 合計金額の大きい順にカテゴリを並べます。
- `round(total)` で合計を整数に、`round(total / n, 1)` で平均を小数第1位に丸めて出力します。

#### 5. 結果の表示

```python
print(f"{len(totals)} カテゴリを summary.csv に書き出しました")
```

- 集計したカテゴリ数を標準出力に表示します。

---

### 注意点

- `summary.csv` が既に存在する場合、確認なしに上書きされます。必要なら事前にバックアップしてください。
- `data/` 内の CSV は読み取りのみで、変更・削除はされません。
- ネットワーク通信や権限の変更はありません。
- `data/` に該当ファイルがない場合でも、ヘッダーだけの `summary.csv` が作られ、「0 カテゴリ」と表示されます（推測：エラーにはなりません）。

---

### まとめ

**`data/sales_*.csv` をカテゴリ別に集計し、合計金額の多い順に件数・合計・平均を `summary.csv` へ書き出す**操作です。影響は作業ディレクトリ内の **`summary.csv` の作成（既存なら上書き）** に限られます。
`````

### python 中 / sonnet / 2回目

最初の文字まで 2.0秒、完了まで 12.3秒、2510字。

`````markdown
この操作は、作業ディレクトリ内の `data/` にある `sales_*.csv` をすべて読み込み、カテゴリ別に件数・合計・平均を集計して `summary.csv` に書き出す Python スクリプトを実行します。スクリプトは `python3 - <<'EOF' ... EOF` のヒアドキュメントで標準入力から渡されるため、ファイルとして保存されません。

---

### ステップ別の詳細解説

#### 1. Python をヒアドキュメントで起動

```bash
python3 - <<'EOF'
...
EOF
```

- `python3 -` は標準入力からスクリプトを読み込んで実行します。
- `<<'EOF'` はヒアドキュメントです。`EOF` をシングルクォートで囲んでいるので、シェルによる変数展開やコマンド置換は行われず、本文がそのまま Python に渡されます。
- `&&` や `;`、パイプによる連結はなく、単一のコマンドです。

#### 2. 集計用の準備

```python
import csv
from collections import defaultdict
from pathlib import Path

totals = defaultdict(float)
counts = defaultdict(int)
```

- 標準ライブラリだけを使うので、追加のインストールは不要です。
- `totals` はカテゴリごとの金額合計、`counts` はカテゴリごとの件数を保持します。キーが無ければ 0 から始まります。

#### 3. CSV の読み込みと集計

```python
for path in sorted(Path("data").glob("sales_*.csv")):
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not row["amount"]:
                continue
            totals[row["category"]] += float(row["amount"])
            counts[row["category"]] += 1
```

- `Path("data").glob("sales_*.csv")` は、`data/` 直下にある `sales_` で始まる CSV を列挙します。`sorted` でファイル名順に処理します。
- 各ファイルを UTF-8 で読み取り専用に開きます。
- `csv.DictReader` は1行目をヘッダーとして、各行を辞書にします。`category` 列と `amount` 列が必要です。
- `amount` が空の行はスキップします。
- それ以外の行は `amount` を `float` に変換して合計に加え、件数を1増やします。

#### 4. summary.csv への書き出し

```python
with open("summary.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "count", "total", "average"])
    for category in sorted(totals, key=totals.get, reverse=True):
        total = totals[category]
        n = counts[category]
        writer.writerow([category, n, round(total), round(total / n, 1)])
```

- `"w"` モードで、作業ディレクトリ直下の `summary.csv` を開きます。
- ヘッダー行は `category,count,total,average` です。
- カテゴリは合計額の大きい順に並べます。
- `total` は整数に丸め、`average`（合計÷件数）は小数第1位に丸めて出力します。

#### 5. 完了メッセージの表示

```python
print(f"{len(totals)} カテゴリを summary.csv に書き出しました")
```

- 集計したカテゴリ数を標準出力に表示します。

### 注意点

- **既存の `summary.csv` は警告なしに上書きされます。** すでに同名のファイルがあれば、元の内容は失われます。
- `data/` 内の CSV は読み取りのみで、変更も削除もしません。
- 次のような場合は途中でエラーになり、`summary.csv` は生成されないか中途半端な状態になる可能性があります（推測を含みます）。
  - `category` や `amount` の列が無い。
  - `amount` に数値以外の文字列、たとえば `1,000` のようなカンマ付きの値がある。
- `data/` に該当ファイルが無い場合は、ヘッダーだけの `summary.csv` が作られ、「0 カテゴリ」と表示されます。
- ネットワーク通信や権限の変更はありません。

---

### まとめ

**`data/sales_*.csv` の売上をカテゴリ別に集計し、件数・合計・平均を合計額の降順で `summary.csv` に書き出す**操作です。影響を受けるのは作業ディレクトリ直下の `summary.csv` の作成（または上書き）だけです。
`````

### python 中 / haiku / 1回目

最初の文字まで 5.8秒、完了まで 14.8秒、2379字。

`````markdown
このコマンドは、`data` ディレクトリ内の複数の売上 CSV ファイル（`sales_*.csv`）をカテゴリ別に集計し、合計額・件数・平均額をまとめた `summary.csv` を作成するものです。

---

### ステップ別の詳細解説

#### 1. Python インタプリタの起動と初期化

```bash
python3 - <<'EOF'
```

- `python3` インタプリタを起動
- `-` により、標準入力（ヒアドキュメント）からコードを読み込み
- `<<'EOF'...EOF` は、ここまでの行を標準入力として py​thon3 に渡す

#### 2. ライブラリのインポートと集計用変数の初期化

```python
import csv
from collections import defaultdict
from pathlib import Path

totals = defaultdict(float)
counts = defaultdict(int)
```

- `csv`：CSV ファイルを読み書きするためのモジュール
- `defaultdict`：キーが存在しなくても初期値を自動生成する辞書
- `Path`：ファイルパスを扱うモジュール
- `totals`：カテゴリごとの合計額を格納（初期値 0.0）
- `counts`：カテゴリごとの件数を格納（初期値 0）

#### 3. CSV ファイルの読み込みと集計

```python
for path in sorted(Path("data").glob("sales_*.csv")):
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not row["amount"]:
                continue
            totals[row["category"]] += float(row["amount"])
            counts[row["category"]] += 1
```

- `Path("data").glob("sales_*.csv")`：`data` ディレクトリ内で `sales_` で始まり `.csv` で終わるファイルを全て取得
- `sorted()`：ファイルを名前順にソート
- `path.open(encoding="utf-8", newline="")`：UTF-8 エンコーディングで各ファイルを開く
- `csv.DictReader(f)`：CSV をヘッダ付きの辞書形式で読み込み（1 行ずつ処理）
- `if not row["amount"]: continue`：`amount` 列が空の行はスキップ
- 各行の `category` と `amount` を集計：`totals` に合計額を加算、`counts` に 1 を加算

#### 4. 集計結果の書き出し

```python
with open("summary.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "count", "total", "average"])
    for category in sorted(totals, key=totals.get, reverse=True):
        total = totals[category]
        n = counts[category]
        writer.writerow([category, n, round(total), round(total / n, 1)])
```

- `open("summary.csv", "w", ...)`：ファイルを**上書きモード**で新規作成
- ヘッダ行 `["category", "count", "total", "average"]` を最初に書き込み
- `sorted(totals, key=totals.get, reverse=True)`：カテゴリを合計額の大きい順にソート
- 各カテゴリについて、件数・合計額・平均額（1 小数点位）をまとめて行として書き込み

#### 5. 完了メッセージの出力

```python
print(f"{len(totals)} カテゴリを summary.csv に書き出しました")
```

- 標準出力に集計したカテゴリ数を表示

---

### 注意点

- **ファイルの上書き**：既存の `summary.csv` があれば**上書きされます**
- **入力ファイルの存在**：`data` ディレクトリと `sales_*.csv` ファイルが存在しないと、結果は空の summary.csv になります
- **エラー処理がない**：CSV の形式が不正（カラム欠落など）の場合、スクリプトが失敗する可能性があります

---

### まとめ

**このコマンドは、作業ディレクトリ内の `data` フォルダから複数の売上 CSV ファイルを読み込み、カテゴリごとに合計額・件数・平均額を計算して、新たに `summary.csv` として出力します。**
`````

### python 中 / haiku / 2回目

最初の文字まで 5.0秒、完了まで 12.1秒、1841字。

`````markdown
このスクリプトは、`data` ディレクトリ内のすべての売上 CSV ファイル（`sales_*.csv`）をカテゴリ別に集計し、合計金額・件数・平均値を計算して `summary.csv` に書き出します。

---

### ステップ別の詳細解説

#### 1. データの読み込みと集計

```python
for path in sorted(Path("data").glob("sales_*.csv")):
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not row["amount"]:
                continue
            totals[row["category"]] += float(row["amount"])
            counts[row["category"]] += 1
```

- `Path("data").glob("sales_*.csv")` により、`data` ディレクトリ内で `sales_` で始まる CSV ファイルをアルファベット順にすべて走査
- 各ファイルを UTF-8 エンコーディングで開く
- `csv.DictReader` により、ヘッダー行を列名として各行を辞書として読み込む
- `amount` フィールドが空の行はスキップ
- `category` をキーとして、`totals` に金額を加算、`counts` に件数を加算

#### 2. 結果の書き出し

```python
with open("summary.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "count", "total", "average"])
    for category in sorted(totals, key=totals.get, reverse=True):
        total = totals[category]
        n = counts[category]
        writer.writerow([category, n, round(total), round(total / n, 1)])
```

- `summary.csv` を新規作成モード（`w`）で開く
- ヘッダー行 `["category", "count", "total", "average"]` を書き出す
- `totals` 辞書を合計金額で降順にソートし、各カテゴリについて以下を書き出す：
  - カテゴリ名
  - 件数（`counts[category]`）
  - 合計金額（四捨五入して整数化）
  - 平均値（小数第1位で四捨五入）

#### 3. 完了メッセージ

```python
print(f"{len(totals)} カテゴリを summary.csv に書き出しました")
```

- 処理されたカテゴリ数を画面に出力

### 注意点

- **上書き注意**：`summary.csv` が既に存在する場合は上書きされます
- **前提条件**：`data` ディレクトリと `sales_*.csv` ファイルが存在していることが前提です。ファイルが1つも見つからない場合は、空のヘッダーのみの CSV が生成されます
- **エンコーディング**：入力・出力ファイルは UTF-8 エンコーディングを使用しており、異なるエンコーディングのファイルがあるとエラーが発生します
- **データ形式**：入力 CSV には `category` 列と `amount` 列が必須です

---

### まとめ

**このスクリプトは、`data` ディレクトリ内の複数の売上 CSV ファイルを読み込み、カテゴリごとに合計金額・件数・平均値を計算して `summary.csv` に書き出します。** 結果は合計金額が大きいカテゴリから順に並びます。
`````

## python 大

### python 大 / sonnet / 1回目

最初の文字まで 2.1秒、完了まで 15.4秒、2633字。

`````markdown
この操作は、Python スクリプトを標準入力から実行し、`~/Pictures/inbox` 内の写真・動画をハッシュで重複判定したうえで、撮影日時ベースの名前で `~/Pictures/library` に整理します。引数に `--apply` がないと確認のみ（ドライラン）で動きます。ただし、この呼び出しは `python3 -` の形式で引数が渡されていないため、`sys.argv` に `--apply` は含まれず、**ドライランとして動作する**と読み取れます。

---

### ステップ別の詳細解説

#### 1. ヒアドキュメントで Python を実行
```bash
python3 - <<'EOF'
...
EOF
```
- `python3 -` は標準入力からスクリプトを読み込んで実行します。
- `<<'EOF'`（クォート付き）により、シェルによる変数展開などは行われず、中身がそのまま Python に渡されます。
- 引数は無いので `DRY_RUN = "--apply" not in sys.argv` は `True` になります。

#### 2. 設定と補助関数
```python
ROOT = ~/Pictures/inbox
LIBRARY = ~/Pictures/library
TRASH = ~/Pictures/.duplicates
EXTS = {".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4"}
```
- 整理元（inbox）、整理先（library）、重複の退避先（.duplicates）、対象拡張子を定義します。
- `sha256()` はファイルを 1MB ずつ読んで SHA-256 ハッシュを計算します。
- `taken_at()` はファイルの作成日時（macOS の `st_birthtime`、なければ更新日時）を「撮影日時」として使います。EXIF は読まないため、実際の撮影日時とは異なる場合があります（コードからの判断）。
- `unique_name()` は同名ファイルがあれば `_1`, `_2`… を付けて衝突を避けます。

#### 3. 初期化（ドライランでも実行される）
```python
LIBRARY.mkdir(parents=True, exist_ok=True)
TRASH.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(DB)
con.execute("CREATE TABLE IF NOT EXISTS files (...)")
```
- library と .duplicates フォルダを作成します。
- `library/index.sqlite3` を開き（無ければ新規作成）、ハッシュ・パス・サイズ・日時を記録する `files` テーブルを作ります。
- これらはドライランでも実行されるため、**ディスク上に空のフォルダと DB ファイルが作られます**。

#### 4. inbox の走査と振り分け
```python
for path in sorted(ROOT.rglob("*")):
```
- inbox 配下を再帰的に走査し、隠しファイルと対象外拡張子（`skipped` に計上）は除外します。
- 各ファイルのハッシュを DB と照合します。
  - **既存と同一（かつ登録先ファイルが存在）**: 重複として `.duplicates` へ移動する予定を記録します。
  - **新規**: `library/年/年-月/YYYYMMDD_HHMMSS.拡張子` へ移動する予定を記録します。
- ドライランでは、実際の移動・DB 登録は行いません。

#### 5. 後処理（`--apply` のときのみ）
```python
con.commit()
for old in TRASH.iterdir(): ... old.unlink()
for folder in sorted(ROOT.rglob("*"), reverse=True): ... folder.rmdir()
```
- DB をコミットします。
- `.duplicates` 内の **30 日より古いファイルを完全削除**します。
- inbox 内の空フォルダを削除します。
- 今回は実行されない見込みです。

#### 6. レポートと出力
- `--apply` 時のみ、`library/report_日時.json` に操作内容を保存します。
- 最後に「移動 N 件 / 重複 N 件 (MB) / 対象外 N 件」を表示し、ドライランなら `--apply` を付けるよう案内します。

### 注意点
- 今回の呼び出しでは `--apply` が付かないため、**ファイルの移動・削除は行われません**。ただし `~/Pictures/library`、`~/Pictures/.duplicates`、`index.sqlite3` は作成されます。
- `--apply` を付けて実行する場合は、`.duplicates` 内の 30 日超のファイルが**復元不能に削除**されます。また、inbox の空ディレクトリも削除されます。
- 重複判定は DB のハッシュに基づきます。DB に未登録の既存ファイルは重複と見なされません。
- `INSERT OR REPLACE` は同じハッシュの既存レコードを上書きします。
- 日時は EXIF ではなくファイルの作成日時で決まるため、コピーなどで変わっている場合は誤った年月に振り分けられる可能性があります。
- 秒単位まで同じファイル名は `_1` のような連番になります。
- ネットワーク通信はなく、操作はローカルのみです。

---

### まとめ
**inbox の写真・動画を重複検出し、日付別フォルダに整理するスクリプトを「確認のみ（ドライラン）」で実行する操作**です。ファイルの移動や削除は行われず、件数の集計と保存先フォルダ・DB の準備だけが行われます。
`````

### python 大 / sonnet / 2回目

最初の文字まで 1.9秒、完了まで 16.3秒、2860字。

`````markdown
この操作は、`~/Pictures/inbox` 内の写真・動画をハッシュ値で重複判定し、`~/Pictures/library` へ日付別に整理して移動するPythonスクリプトを実行するものです。ヒアドキュメント（`python3 - <<'EOF'`）で標準入力からスクリプトを渡しています。コマンドラインに `--apply` が付いていないため、**確認のみ（ドライラン）モード**で動きます。

---

### ステップ別の詳細解説

#### 1. スクリプトの渡し方と設定

```python
python3 - <<'EOF'
ROOT = Path.home() / "Pictures" / "inbox"
LIBRARY = Path.home() / "Pictures" / "library"
TRASH = Path.home() / "Pictures" / ".duplicates"
DRY_RUN = "--apply" not in sys.argv
```

- `python3 -` は標準入力からスクリプトを読み込みます。`<<'EOF'` は、変数展開をしないヒアドキュメントです。
- `ROOT` は整理元、`LIBRARY` は整理先（索引DBもここ）、`TRASH` は重複ファイルの退避先です。
- 対象拡張子は jpg / jpeg / png / heic / mov / mp4 です。
- `sys.argv` に `--apply` が含まれないため、`DRY_RUN` は `True` になります。この実行では実際の移動や削除は行われません。

#### 2. 準備処理（この段階は確認モードでも実行される）

```python
LIBRARY.mkdir(parents=True, exist_ok=True)
TRASH.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(DB)
con.execute("CREATE TABLE IF NOT EXISTS files (...)")
```

- `library` と `.duplicates` フォルダを、なければ作成します。
- `library/index.sqlite3` に接続します。ファイルがなければ新規作成されます。
- `files` テーブル（ハッシュ・パス・サイズ・撮影日時・追加日時）がなければ作ります。

#### 3. ファイルの走査と重複判定

```python
for path in sorted(ROOT.rglob("*")):
    digest = sha256(path)
    row = con.execute("SELECT path FROM files WHERE hash = ?", (digest,)).fetchone()
```

- `inbox` 以下を再帰的に調べます。ドットで始まるファイルと対象外の拡張子はスキップします。
- 各ファイルの SHA-256 を計算し、索引DBの既存ハッシュと照合します。
- 一致し、かつ登録先のファイルが実在すれば「重複」とします。重複は `.duplicates` への退避を計画します。
- 重複でなければ、作成日時（`st_birthtime`、なければ更新日時）から `library/年/年-月/YYYYMMDD_HHMMSS.拡張子` という移動先を決めます。同名があれば `_1`, `_2` … を付けます。

#### 4. 実行モードでの処理（`--apply` 付きの場合のみ）

```python
shutil.move(str(path), target)
con.execute("INSERT OR REPLACE INTO files VALUES (...)")
...
for old in TRASH.iterdir():
    if ... < limit:
        old.unlink()
for folder in sorted(ROOT.rglob("*"), reverse=True):
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
```

- ファイルを実際に移動し、索引DBへ登録してコミットします。
- `.duplicates` 内の、更新日時が30日より古いファイルを**完全削除**します。
- `inbox` 内の空フォルダを削除します。
- 今回の実行（`--apply` なし）では、このブロックは動きません。

#### 5. レポート出力

```python
print(f"[{mode}] 移動 {moved} 件 / 重複 {duplicates} 件 ...")
```

- 移動件数、重複件数と容量（MB）、対象外件数を表示します。
- ドライランでは JSON レポートは書き出さず、`--apply` を付けるよう案内します。

### 注意点

- 今回はドライランですが、`library` と `.duplicates` の作成、および SQLite DB の作成・接続は行われます。写真自体は変更されません。
- **スクリプト内に `--apply` を渡す仕組みの不備があります。** `python3 -` にはコマンドライン引数がないため、`sys.argv` に `--apply` が入ることはありません。この形では常にドライランになります（動作を確認する用途には安全です）。
- 実行モードに切り替えた場合は、次の点に注意してください。
  - `.duplicates` 内の30日超のファイルが完全に削除され、元に戻せません。この削除は、今回の実行分だけでなく以前から溜まっていたファイルにも及びます。
  - 重複判定は索引DBに登録済みのものだけが対象です。DBが空だと、`inbox` 内の重複同士も最初の1件は通常の移動扱いになります。ただし2件目以降は、DB登録後なので重複と判定されます。ドライランではDBに登録しないため、その件数は実際より少なく表示される可能性があります（推測を含みます）。
  - 撮影日時にはEXIFではなくファイルの作成日時を使うため、実際の撮影日とずれることがあります。

---

### まとめ

**写真・動画の整理と重複検出を、変更を加えない確認モードで試す操作**です。`inbox` の内容を日付別に `library` へ移す計画と、重複件数・容量を表示するだけで、ファイルの移動や削除は行いません。
`````

### python 大 / haiku / 1回目

最初の文字まで 34.3秒、完了まで 57.5秒、5864字。

`````markdown
このスクリプトは、`~/Pictures/inbox` 内の写真・動画を、撮影日時に基づいて `~/Pictures/library` に体系的に整理し、SHA256 ハッシュで重複を検出して `~/.duplicates` に移動します。`--apply` フラグなしで実行した場合は、実際の移動を行わず、どのような操作が行われるかを確認できるドライラン (DRY_RUN) モードで動作します。

---

### ステップ別の詳細解説

#### 1. モジュールのインポートと定数の定義

```python
import hashlib, json, sqlite3, sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path.home() / "Pictures" / "inbox"
LIBRARY = Path.home() / "Pictures" / "library"
TRASH = Path.home() / "Pictures" / ".duplicates"
DB = LIBRARY / "index.sqlite3"
EXTS = {".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4"}
DRY_RUN = "--apply" not in sys.argv
```

- `hashlib`: ファイルの SHA256 ハッシュ値を計算（重複検出に使用）
- `sqlite3`: SQLite データベース操作用
- `shutil`: ファイル移動用
- `ROOT`: スキャン対象のディレクトリ（`~/Pictures/inbox`）
- `LIBRARY`: 整理後のライブラリ先（`~/Pictures/library`）
- `TRASH`: 重複ファイルの移動先（`~/.duplicates`）
- `DB`: ファイル追跡用 SQLite データベースの場所
- `EXTS`: 処理対象の拡張子（画像・動画のみ）
- `DRY_RUN`: `--apply` フラグがなければ `True`（確認のみ），あれば `False`（実行）

#### 2. SHA256 ハッシュ計算関数

```python
def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()
```

- ファイルを 1MB ずつ（`1 << 20` = 1048576 バイト）読み込んでハッシュを計算
- 16 進数文字列で SHA256 ハッシュ値を返す
- 大きなファイルでもメモリ効率よく処理可能

#### 3. 撮影日時の取得関数

```python
def taken_at(path: Path) -> datetime:
    stat = path.stat()
    return datetime.fromtimestamp(getattr(stat, "st_birthtime", stat.st_mtime))
```

- ファイルの作成時刻（`st_birthtime`、macOS・APFS対応）を取得
- 作成時刻がない場合は更新時刻（`st_mtime`）にフォールバック
- `datetime` 形式で返す

#### 4. 一意なファイル名を生成する関数

```python
def unique_name(dest: Path) -> Path:
    if not dest.exists():
        return dest
    for i in range(1, 1000):
        candidate = dest.with_name(f"{dest.stem}_{i}{dest.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"名前を決められません: {dest}")
```

- 移動先のパスが既に存在する場合、`_1`, `_2`, ... を追加して名前を変更
- 1000 個までの名前競合に対応
- すべて埋まっていたら例外を発生

#### 5. データベースと作業ディレクトリの初期化

```python
LIBRARY.mkdir(parents=True, exist_ok=True)
TRASH.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(DB)
con.execute(
    "CREATE TABLE IF NOT EXISTS files ("
    "hash TEXT PRIMARY KEY, path TEXT NOT NULL, size INTEGER, taken TEXT, added TEXT)"
)
```

- `LIBRARY` と `TRASH` ディレクトリを作成（既に存在していても OK）
- SQLite データベースを開く（なければ作成）
- `files` テーブルを作成（存在しなければ）
  - `hash`: ファイルの SHA256（主キー）
  - `path`: ライブラリ内の最終パス
  - `size`: ファイルサイズ（バイト）
  - `taken`: 撮影日時（ISO形式）
  - `added`: DB に追加された日時（ISO形式）

#### 6. スキャン・重複判定・整理のメインループ

```python
for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path.name.startswith("."):
        continue
    if path.suffix.lower() not in EXTS:
        skipped += 1
        continue
    digest = sha256(path)
    row = con.execute("SELECT path FROM files WHERE hash = ?", (digest,)).fetchone()
    
    # 重複判定
    if row and Path(row[0]).exists():
        duplicates += 1
        freed += size
        target = unique_name(TRASH / path.name)
        actions.append({"action": "duplicate", "from": str(path), "to": str(target), "same_as": row[0]})
        if not DRY_RUN:
            shutil.move(str(path), target)
        continue
    
    # 新規ファイルの整理
    when = taken_at(path)
    folder = LIBRARY / f"{when:%Y}" / f"{when:%Y-%m}"
    target = unique_name(folder / f"{when:%Y%m%d_%H%M%S}{path.suffix.lower()}")
    actions.append({"action": "move", "from": str(path), "to": str(target)})
    moved += 1
    if DRY_RUN:
        continue
    folder.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), target)
    con.execute(
        "INSERT OR REPLACE INTO files VALUES (?, ?, ?, ?, ?)",
        (digest, str(target), size, when.isoformat(), datetime.now().isoformat()),
    )
```

**ファイルスキャン:**
- `ROOT.rglob("*")` でサブディレクトリ含むすべてのファイルを再帰的に列挙
- ファイルでない、または `.` で始まるファイル（隠しファイル）なら スキップ
- 拡張子が対象外なら カウントしてスキップ

**重複判定:**
- ファイルの SHA256 を計算し DB 検索
- 同じハッシュを持つファイルが存在し、その場所にファイルが現存する場合は重複
  - `TRASH` に一意な名前で移動（ドライラン中は実行なし）
  - アクション記録に追加（元ファイル、移動先、重複元）
  - 解放容量をカウント

**新規ファイルの整理:**
- 撮影日時を取得
- `LIBRARY/YYYY/YYYY-MM` フォルダ構造を決定
- ファイル名を `YYYYMMDD_HHMMSS.拡張子` に変更
- アクション記録に追加
- （ドライラン中でなければ）ディレクトリを作成し、ファイルを移動・DB に記録

#### 7. ドライラン終了後の処理と DB のコミット

```python
if not DRY_RUN:
    con.commit()
    limit = datetime.now() - timedelta(days=30)
    for old in TRASH.iterdir():
        if datetime.fromtimestamp(old.stat().st_mtime) < limit:
            old.unlink()
    for folder in sorted(ROOT.rglob("*"), reverse=True):
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
con.close()
```

- DB の変更をコミット（実行時のみ）
- `TRASH` 内で 30 日以上前のファイルを削除
- `ROOT` 内の空のディレクトリを削除（ボトムアップで奥から手前へ）
- DB のコネクションを閉じる

#### 8. レポート生成と統計表示

```python
report = LIBRARY / f"report_{datetime.now():%Y%m%d_%H%M%S}.json"
if not DRY_RUN:
    report.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8")

mode = "確認のみ" if DRY_RUN else "実行"
print(f"[{mode}] 移動 {moved} 件 / 重複 {duplicates} 件 ({freed / 1e6:.1f} MB) / 対象外 {skipped} 件")
if DRY_RUN:
    print("実際に動かすには --apply を付けて実行してください")
```

- 実行時のみ、すべてのアクション（移動・重複検出）を JSON で `LIBRARY` に保存
- 処理結果の統計を表示
  - 移動件数・重複件数・解放容量（MB）・対象外件数
- ドライラン時は実行手順を表示

---

### 注意点

- **取り消し不可能な操作**: `--apply` 実行時、ファイルは実際に移動されます。必ず事前に `--apply` なしでドライラン実行し、アクション内容を確認してください。
- **30 日後の自動削除**: `--apply` 実行時、`~/.duplicates` 内の 30 日以上前のファイルは自動削除されます。重要なファイルが混入しないよう注意してください。
- **DB の永続化**: `LIBRARY/index.sqlite3` は初回実行時に作成され、以降のスクリプト実行で追記されます。
- **macOS 特有の処理**: `st_birthtime` は macOS・APFS での作成時刻ですが、他の OS では サポートされない可能性があります。
- **ハッシュ衝突**: SHA256 は数学的には安全ですが、極めてまれなハッシュ衝突が発生した場合、異なるファイルが誤って重複と判定される可能性があります。

---

### まとめ

**このスクリプトは、`~/Pictures/inbox` から写真・動画を `~/Pictures/library` に撮影日時ベースで自動整理し、SHA256 ハッシュを使用して重複を検出・隔離するとともに、SQLite で追跡情報を保存する写真ライブラリ管理ツールです。** `--apply` フラグなしなら確認のみ、`--apply` 付きで実際に移動を実行します。
`````

### python 大 / haiku / 2回目

最初の文字まで 10.8秒、完了まで 26.7秒、4201字。

`````markdown
このスクリプトは、ホームディレクトリの `~/Pictures/inbox` フォルダから画像・動画ファイルを自動検出し、撮影日時で整理して `~/Pictures/library` に移動する一方、SHA256 ハッシュで重複を検出して `~/Pictures/.duplicates` に隔離します。`--apply` フラグがなければドライランとなり、実際には何も変更されません。

---

### ステップ別の詳細解説

#### 1. 環境設定とデータベース初期化

```python
ROOT = Path.home() / "Pictures" / "inbox"
LIBRARY = Path.home() / "Pictures" / "library"
TRASH = Path.home() / "Pictures" / ".duplicates"
DB = LIBRARY / "index.sqlite3"
EXTS = {".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4"}
DRY_RUN = "--apply" not in sys.argv
```

- **ROOT**: 処理対象の入力フォルダ
- **LIBRARY**: 整理後のファイル置き場（`YYYY/YYYY-MM` 形式で日時別フォルダを作成）
- **TRASH**: 重複ファイルの隔離先フォルダ
- **DB**: ファイル管理用のSQLiteデータベース（ハッシュ値、パス、サイズ、撮影日時などを記録）
- **EXTS**: 処理対象とする拡張子（これ以外のファイルはスキップ）
- **DRY_RUN**: コマンドラインに `--apply` がなければ確認のみモード

#### 2. ハッシュ値計算と重複検出

```python
def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()
```

- ファイルを1MB単位で読み込み、SHA256ハッシュを計算
- 同じハッシュ値を持つファイルを重複と判定
- メモリ効率のため、全ファイルをメモリに展開しない

#### 3. 撮影日時取得と名前衝突対策

```python
def taken_at(path: Path) -> datetime:
    stat = path.stat()
    return datetime.fromtimestamp(getattr(stat, "st_birthtime", stat.st_mtime))

def unique_name(dest: Path) -> Path:
    if not dest.exists():
        return dest
    for i in range(1, 1000):
        candidate = dest.with_name(f"{dest.stem}_{i}{dest.suffix}")
        if not candidate.exists():
            return candidate
```

- `taken_at()`: ファイルの作成日時（macOSの`st_birthtime`）または更新日時を取得
- `unique_name()`: 同じ日時・名前のファイルが既に存在する場合、`_1`、`_2` などを追加

#### 4. メインの処理ループ

```python
for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path.name.startswith("."):
        continue
    if path.suffix.lower() not in EXTS:
        skipped += 1
        continue
    digest = sha256(path)
    row = con.execute("SELECT path FROM files WHERE hash = ?", (digest,)).fetchone()
    # 重複チェック
    if row and Path(row[0]).exists():
        duplicates += 1
        # ... TRASH へ移動
    # 新規ファイルは日時別フォルダへ移動
    when = taken_at(path)
    folder = LIBRARY / f"{when:%Y}" / f"{when:%Y-%m}"
    target = unique_name(folder / f"{when:%Y%m%d_%H%M%S}{path.suffix.lower()}")
```

- `ROOT` フォルダ内のすべてのファイルをソート順で処理
- 隠しファイル（`.` で始まるもの）と対象拡張子以外をスキップ
- **重複ファイルの場合**: DB に同じハッシュが存在し、かつ対象ファイルが存在 → `TRASH` フォルダに移動
- **新規ファイルの場合**: 撮影日時で `LIBRARY/年/年-月` フォルダを生成し、`YYYYMMDD_HHMMSS.拡張子` 形式にリネームして移動

#### 5. データベース更新

```python
if not DRY_RUN:
    con.execute(
        "INSERT OR REPLACE INTO files VALUES (?, ?, ?, ?, ?)",
        (digest, str(target), size, when.isoformat(), datetime.now().isoformat()),
    )
    con.commit()
```

- 移動したファイルのメタデータ（ハッシュ、新しいパス、サイズ、撮影日時、追加日時）をDBに記録
- `--apply` 実行時のみコミット

#### 6. クリーンアップ（`--apply` 実行時のみ）

```python
limit = datetime.now() - timedelta(days=30)
for old in TRASH.iterdir():
    if datetime.fromtimestamp(old.stat().st_mtime) < limit:
        old.unlink()
for folder in sorted(ROOT.rglob("*"), reverse=True):
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
```

- **古いファイル削除**: `TRASH` フォルダ内で30日以上前に移動されたファイルを削除
- **空フォルダ削除**: `ROOT` フォルダ内の空になったフォルダを再帰的に削除

#### 7. レポート生成と結果表示

```python
report = LIBRARY / f"report_{datetime.now():%Y%m%d_%H%M%S}.json"
if not DRY_RUN:
    report.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"[{mode}] 移動 {moved} 件 / 重複 {duplicates} 件 ({freed / 1e6:.1f} MB) / 対象外 {skipped} 件")
```

- 実行時のすべてのアクション（移動・重複検出）をJSON形式で `report_YYYYMMDD_HHMMSS.json` に保存
- 処理結果を表示（ドライランの場合は "実際に動かすには --apply を付けて実行してください" と表示）

---

### 注意点

- **ファイル移動は取り消せない操作**: `--apply` を指定すると `shutil.move()` でファイルが実際に移動され、元のフォルダ構成は失われます
- **データベースの記録変更**: 一度 `--apply` で実行するとDBに記録されるため、以後の実行で重複判定の基準が変わります
- **30日以降の削除**: `--apply` 実行時、TRASH フォルダ内で30日以上経過したファイルは自動的に削除されます
- **名前衝突の自動リネーム**: 同じ日時のファイルが複数あると `_1`, `_2` などが自動付加され、元のファイル名が変更されます
- **最初は必ずドライランで確認推奨**: `--apply` なしで動作確認し、出力されるアクション内容を確認してから本実行してください

---

### まとめ

**このスクリプトは、`Pictures/inbox` フォルダの画像・動画を撮影日時で整理して `library` に体系的に格納しつつ、ハッシュ値により重複ファイルを自動検出して隔離し、SQLiteデータベースで一元管理するファイル整理ツールです。** `--apply` なしではドライランで実行内容を確認でき、確認後に `--apply` フラグを付けて実際に適用できます。
`````
