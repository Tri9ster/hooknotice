# TODO（後で検討）

2026-09-22 のダイアログ方式への移行、および同日中の PySide6製カード型ウィンドウ復元で
気になった点のメモ。

- [x] **Python環境の方針を決める**
  → `uv` を導入し、`pyproject.toml` / `uv.lock` でPySide6を管理する方式に決定。
  `hook_notify.py` は引き続き `/usr/bin/python3` で動く（標準ライブラリのみ）。
- [x] **Notification系Hookが実際に発火するか確認する**
  旧 `hook_invocations.log`（8/11〜8/31、47件）には `permission_request` しか記録されておらず、
  `Notification`（`elicitation_dialog` / `agent_needs_input` / `idle_prompt`）は一度も記録されていなかった。
  → 2026-09-26、ユーザーが実際の利用中に Notification 系の Hook が発火して通知が出ることを確認した。
- [x] **スタック段の「詰め直し」をどこまで再現するか**
  → 2026-09-23 に対応。`stack_state.json` を到着順リストにし、各通知が250msごとに自分の
  順位を読み直して上へ詰める方式にした（常駐デーモンは不要のまま）。
- [ ] **プラグインとして導入した状態での確認**
  2026-09-28 にプラグインの構成へ移した。マーケットプレイスから導入し、初回の準備ダイアログで `<DATA>/venv` が
  作られること、全種類の通知とボタンの回答、`/hooknotice:settings`、`<DATA>/config.json` の設定が効くことを確かめる。
- [ ] **Windows対応**
  2026-09-26 に OS ごとの処理を `platform_support.py` に切り出し、Windows の分岐を実装した（未検証）。残り:
  - Windows 実機で6種類の通知・積み順・ボタンの回答・Hook 終了時の自動クローズを確認する
    （Hook の起動コマンド `python` / `py -3`、子プロセスが Hook 終了後も残るか、UTF-8 の受け渡しを含む）
  - プラグインの `hooks/hooks.json` は `python3` 固定。Windows で `python3` が無い場合の起動方法を決める
  - Consolas 11px の1文字幅を実測し、`COMMAND_CHAR_WIDTH_PX` を OS 別にする
  - 通知表示でフォーカスを奪わないか、タスクバーにボタンが出ないか（`Qt.Tool` / `WA_ShowWithoutActivating` の検討）
  - 本体クリックでの発火元アプリの前面化（Windows は前面化の制限が強い）
  - 「解説」ボタン: `claude.cmd` などを `QProcess` で起動できるか
- [x] **`uv sync` を忘れた場合の気づきやすさ**
  → 2026-09-27 に、SessionStart で準備が必要なら `uv sync --frozen` を実行してよいかを確認するダイアログを出すようにした。
