# docs（hooknotice の開発者向け資料）

hooknotice の保守・改修をする人向けの技術資料です。使い方は [../README.ja.md](../README.ja.md)（英語版は [../README.md](../README.md)）、
外部から見た仕様と変更履歴の要約は [specification.md](specification.md) を参照してください。
ここには「なぜそう作ったか」「どこでつまずいたか」を残します。

| ファイル | 内容 |
| --- | --- |
| [architecture.md](architecture.md) | ツールの技術解説（構成、処理の流れ、Hook との連携、ウィンドウの内部構造、設計判断） |
| [dev-log.md](dev-log.md) | 開発記録（2026-09-24〜: 新しいものが上） |
| [failures.md](failures.md) | 失敗・つまずきの記録（症状、原因、対処、教訓） |
| [specification.md](specification.md) | 仕様書（外部から見た動作と変更履歴） |
| [TODO.md](TODO.md) | 後で検討すること |

## 書き方の約束

- 機能追加・修正をコミットするときは、内容に応じてこの表のファイルを同じ PR で必ず更新する（`CLAUDE.md` の規則）。
- 新しい機能を足したら dev-log.md に節を追加し、つまずいたことは failures.md に1件ずつ残す。
- 構成や前提が変わったら architecture.md を更新する（古い説明を残さない）。
- 家族・知人の情報や認証情報は書かない。パスはホームを `~` で書く。
