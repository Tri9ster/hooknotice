# hooknotice の開発ルール

hooknotice は Claude Code のプラグイン（通知ウィンドウ）です。このファイルは、このリポジトリで作業する Claude
（GitHub Actions 上の Claude GitHub App を含む）向けのルールです。

## 言語

- Issue・PR・コメントへの回答、コミットメッセージ、docs は日本語で書く。
- 利用者向けの README は英語（`README.md`）と日本語（`README.ja.md`）の2本。片方を変えたら、もう片方も同じ内容にする。
- 画面の文言は `plugins/hooknotice/messages.py` の `ja` / `en` の両方に足す（キーと差し込む値をそろえる。確かめ方は
  `docs/architecture.md` 6章）。
- コミットメッセージの形式: `<gitmoji><type>(<scope>): <日本語の要約>`（scope は省略可）。

## 構成

- `.claude-plugin/marketplace.json`: マーケットプレイス。`plugins/hooknotice/` がプラグイン本体。
- `plugins/hooknotice/.claude-plugin/plugin.json`: `version` を上げたときだけ利用者に更新が届く。利用者に届けたい変更では上げる。
- `plugins/hooknotice/hook_notify.py` と `platform_support.py`・`hooknotice_config.py`・`messages.py` は
  **標準ライブラリだけ**で書く（Hook はシステムの `python3` で動く）。PySide6 を使うのは `notify_window.py` と `settings_window.py` だけ。
- 書き込むもの（venv・`config.json`）は `CLAUDE_PLUGIN_DATA` に置く。プラグインの本体（`CLAUDE_PLUGIN_ROOT`）には書き込まない。
- 何が起きても Claude Code の動作を妨げない（Hook は常に exit 0、例外で止めない）。
- 依存を変えたら `plugins/hooknotice` で `uv lock` を実行し、`uv.lock` も一緒にコミットする。
- 仕様の変更は `docs/specification.md`（変更履歴を含む）に、作業の記録は `docs/dev-log.md` に、つまずきは
  `docs/failures.md` に残す（`docs/README.md` の約束）。

## 確認方法（重要）

GitHub Actions のマシンは Linux で画面が無いため、**通知ウィンドウの見た目・音・macOS の動作は確認できない**。
Actions 上でできる確認は次まで。確認できなかったことは、PR の説明に「手元の macOS で確認が必要」と書く。

- 構文チェック: `python3 -m py_compile plugins/hooknotice/*.py`
- マニフェストの検証: `claude plugin validate .`（使えれば）
- 画面なしの描画: `QT_QPA_PLATFORM=offscreen` で PySide6 のウィジェットを作って大きさなどを確かめる
  （`docs/architecture.md` 6章）。
- 文言の日英のそろい: `docs/architecture.md` 6章のスクリプト。

利用者（リポジトリの持ち主）は、PR のブランチを取り込み（`gh pr checkout <番号>`）、
`claude --plugin-dir ./plugins/hooknotice` で読み込んで macOS の実機で確かめる。

## 書かないもの

- 個人情報（名前・メールアドレス・住所など）、認証情報（トークン・API キー）、利用者固有の絶対パス。パスはホームを `~` で書く。
