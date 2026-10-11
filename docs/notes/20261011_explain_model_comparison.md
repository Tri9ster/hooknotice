# 「解説」のモデル比較(sonnet と haiku)の検証記録

- 実施日: 2026-10-11
- 目的: 通知ウィンドウの「解説」に使うモデル(`config.json` の `explain.model`)を、sonnet と haiku のどちらにするか決める。
- 実施者: Claude Code(Claude Opus 5.5)が計測・集計・解説文の読み比べを行い、持ち主が結果を確認した。
- 関連ファイル: 24回ぶんの解説文の全文は [20261011_explain_model_comparison_answers.md](20261011_explain_model_comparison_answers.md) にある。

## 1. 最終的な考察

**解説用モデルは既定値の sonnet(effort `low`)のままがよい。** 今回の条件では、速度・内容・費用のどれを見ても haiku に替える利点が見つからなかった。

- **速度**: 6種類のサンプルすべてで、平均は sonnet のほうが速かった。個別の比較でも、完了までの時間は12組のうち11組で sonnet が速かった。
- **差の正体**: 差の大半は「最初の文字が出るまで」にある。haiku は本文の前に思考ブロックを出しており、その間は解説欄に何も表示されない。書き始めてからの速さは両者で同程度だった。
- **内容**: sonnet は「この実行で実際に何が起きるか」まで踏み込み、推測には「推測」と明記した。haiku はコードを細かくなぞる書き方で、細かい誤りが混じった。許可の判断材料としては sonnet のほうが役に立つ。
- **費用**: 確認した1回では、1回あたりの費用はどちらも約0.013ドルだった。haiku は入力が約32,000トークンと大きく、思考のトークンも加わるため、安くならなかった。

長い目で見たときの注意点は次のとおり。

- この結果は「Haiku 4.5 と Sonnet 5.5」「Claude Code 2.1.292」「effort `low`」という組み合わせのものである。モデルや CLI が新しくなれば、思考の扱いや入力の大きさが変わり、結論も変わりうる。別名(`haiku`・`sonnet`)の指す先が変わったら測り直す価値がある。
- haiku が遅い主な原因は思考なので、思考を切れれば速くなる見込みはある。ただし hooknotice の設定にあるのはモデルと effort だけで、思考を切る項目は無い。試すにはプラグイン側の変更が必要になる。今回は試していない。
- 各2回の計測で、ばらつきは大きい。「sonnet のほうが速い」という向きははっきりしているが、何秒速いかという数字は目安である。

## 2. 結果

### 2.1 速度の一覧(2回の平均)

時間の単位は秒。「最初の文字まで」は、プロセスを起動してから本文の最初の文字(`text_delta`)が届くまでの時間。

| サンプル | 行数 | コードの字数 | 最初の文字まで: sonnet | 最初の文字まで: haiku | 完了まで: sonnet | 完了まで: haiku | 出力の字数: sonnet | 出力の字数: haiku |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bash 小 | 1 | 55 | 2.1 | 7.0 | 9.7 | 12.9 | 1324 | 1068 |
| bash 中 | 23 | 610 | 2.0 | 6.4 | 15.6 | 17.9 | 2742 | 2450 |
| bash 大 | 90 | 2096 | 1.3 | 7.8 | 19.2 | 26.9 | 4318 | 4383 |
| python 小 | 1 | 95 | 1.7 | 8.5 | 7.3 | 12.9 | 1115 | 1158 |
| python 中 | 26 | 867 | 1.6 | 5.4 | 11.9 | 13.4 | 2578 | 2110 |
| python 大 | 104 | 3278 | 2.0 | 22.6 | 15.8 | 42.1 | 2746 | 5032 |

### 2.2 全24回の結果

「API 時間」は結果の JSON にある `duration_api_ms`。「書き始めてからの速さ」は、出力の字数を(完了まで − 最初の文字まで)で割った値。

| 実行順 | サンプル | モデル | 回 | 最初の文字まで(秒) | 完了まで(秒) | API 時間(秒) | 出力の字数 | 書き始めてからの速さ(字/秒) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | bash 小 | sonnet | 1 | 2.1 | 9.5 | 8.4 | 1300 | 176 |
| 2 | bash 小 | haiku | 1 | 4.3 | 10.9 | 10.5 | 1048 | 158 |
| 3 | bash 小 | haiku | 2 | 9.8 | 14.9 | 15.2 | 1088 | 212 |
| 4 | bash 小 | sonnet | 2 | 2.0 | 10.0 | 8.9 | 1347 | 169 |
| 5 | bash 中 | sonnet | 1 | 2.0 | 16.4 | 16.0 | 2848 | 197 |
| 6 | bash 中 | haiku | 1 | 5.5 | 16.9 | 17.1 | 2432 | 213 |
| 7 | bash 中 | haiku | 2 | 7.2 | 18.9 | 21.4 | 2469 | 211 |
| 8 | bash 中 | sonnet | 2 | 2.0 | 14.7 | 13.8 | 2637 | 208 |
| 9 | bash 大 | sonnet | 1 | 1.3 | 19.9 | 19.8 | 4280 | 230 |
| 10 | bash 大 | haiku | 1 | 6.0 | 24.9 | 25.0 | 4230 | 224 |
| 11 | bash 大 | haiku | 2 | 9.6 | 28.9 | 28.8 | 4536 | 234 |
| 12 | bash 大 | sonnet | 2 | 1.3 | 18.6 | 18.6 | 4355 | 251 |
| 13 | python 小 | sonnet | 1 | 1.3 | 7.2 | 7.2 | 1166 | 200 |
| 14 | python 小 | haiku | 1 | 6.4 | 11.7 | 10.8 | 1183 | 223 |
| 15 | python 小 | haiku | 2 | 10.6 | 14.2 | 14.0 | 1134 | 322 |
| 16 | python 小 | sonnet | 2 | 2.0 | 7.4 | 6.5 | 1064 | 197 |
| 17 | python 中 | sonnet | 1 | 1.3 | 11.4 | 11.3 | 2647 | 261 |
| 18 | python 中 | haiku | 1 | 5.8 | 14.8 | 14.4 | 2379 | 262 |
| 19 | python 中 | haiku | 2 | 5.0 | 12.1 | 11.8 | 1841 | 260 |
| 20 | python 中 | sonnet | 2 | 2.0 | 12.3 | 11.4 | 2510 | 243 |
| 21 | python 大 | sonnet | 1 | 2.1 | 15.4 | 14.5 | 2633 | 198 |
| 22 | python 大 | haiku | 1 | 34.3 | 57.5 | 57.5 | 5864 | 252 |
| 23 | python 大 | haiku | 2 | 10.8 | 26.7 | 26.8 | 4201 | 265 |
| 24 | python 大 | sonnet | 2 | 1.9 | 16.3 | 15.3 | 2860 | 199 |

読み取れること:

- 最初の文字までの時間は、24回すべてで sonnet のほうが短かった(sonnet 1.3〜2.1秒、haiku 4.3〜34.3秒)。
- 書き始めてからの速さは、sonnet が毎秒169〜261字、haiku が毎秒158〜322字で、同程度だった。
- コードが長いほど解説が長くなり、完了までの時間も伸びる。sonnet は python 大でも解説を短くまとめ、haiku は長くなった。
- haiku の python 大の1回目(最初の文字まで34.3秒、完了まで57.5秒)は外れ値で、原因は分かっていない。

### 2.3 解説文の構成の集計

正規表現で数えた値。ステップ数は `#### ` の見出しの数、「推測」は本文中にその語が出た回数。

| サンプル | モデル | 回 | 字数 | ステップ数 | 箇条書き | 太字 | 注意点の項目 | 「推測」の回数 | 「です。/ます。」の回数 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bash 小 | sonnet | 1 | 1300 | 3 | 12 | 3 | 4 | 1 | 19 |
| bash 小 | haiku | 1 | 1048 | 3 | 11 | 12 | 4 | 0 | 4 |
| bash 小 | haiku | 2 | 1088 | 2 | 11 | 5 | 4 | 0 | 9 |
| bash 小 | sonnet | 2 | 1347 | 3 | 14 | 3 | 6 | 0 | 21 |
| bash 中 | sonnet | 1 | 2848 | 6 | 29 | 7 | 6 | 0 | 30 |
| bash 中 | haiku | 1 | 2432 | 7 | 28 | 6 | 5 | 0 | 6 |
| bash 中 | haiku | 2 | 2469 | 8 | 31 | 27 | 5 | 0 | 3 |
| bash 中 | sonnet | 2 | 2637 | 6 | 29 | 1 | 6 | 1 | 33 |
| bash 大 | sonnet | 1 | 4280 | 11 | 31 | 11 | 9 | 2 | 40 |
| bash 大 | haiku | 1 | 4230 | 13 | 42 | 11 | 7 | 0 | 4 |
| bash 大 | haiku | 2 | 4536 | 14 | 46 | 40 | 7 | 0 | 5 |
| bash 大 | sonnet | 2 | 4355 | 11 | 31 | 9 | 8 | 2 | 39 |
| python 小 | sonnet | 1 | 1166 | 1 | 8 | 1 | 3 | 0 | 6 |
| python 小 | haiku | 1 | 1183 | 3 | 12 | 14 | 4 | 0 | 5 |
| python 小 | haiku | 2 | 1134 | 3 | 13 | 5 | 4 | 0 | 2 |
| python 小 | sonnet | 2 | 1064 | 1 | 7 | 1 | 3 | 1 | 11 |
| python 中 | sonnet | 1 | 2647 | 5 | 20 | 2 | 4 | 2 | 21 |
| python 中 | haiku | 1 | 2379 | 5 | 22 | 6 | 3 | 0 | 2 |
| python 中 | haiku | 2 | 1841 | 3 | 17 | 5 | 4 | 0 | 4 |
| python 中 | sonnet | 2 | 2510 | 5 | 22 | 1 | 5 | 1 | 25 |
| python 大 | sonnet | 1 | 2633 | 6 | 28 | 8 | 7 | 0 | 32 |
| python 大 | haiku | 1 | 5864 | 8 | 52 | 9 | 5 | 0 | 9 |
| python 大 | haiku | 2 | 4201 | 7 | 26 | 16 | 5 | 0 | 3 |
| python 大 | sonnet | 2 | 2860 | 5 | 23 | 4 | 3 | 1 | 32 |

モデルごとのまとめ:

| 項目 | sonnet | haiku |
| --- | --- | --- |
| 最初の文字まで(最小〜最大、秒) | 1.3〜2.1 | 4.3〜34.3 |
| 書き始めてからの速さ(最小〜最大、字/秒) | 169〜261 | 158〜322 |
| 「推測」と明記した回(12回中) | 8 | 0 |
| 太字の数(最小〜最大、平均) | 1〜11、4.2 | 5〜40、13.0 |
| 「です。/ます。」で終わる文の数(平均) | 25.8 | 4.7 |

### 2.4 精度分析(解説文の読み比べ)

読んだ範囲は次のとおり。24回すべてを全文で読み比べたわけではない。

- 全文を読んだもの: bash 小の1回目(両モデル)、python 中の1回目(両モデル)。
- 冒頭・見出し・注意点とまとめを読んだもの: bash 大の1回目(両モデル)、python 大の1回目(両モデル)。
- 冒頭の400字を読んだもの: bash 大の haiku 2回目(先頭が見出しだった回)。
- それ以外: 2.3 の集計だけで比べた。

#### sonnet の特徴

- **実行結果を読み解く**: python 大で、`python3 -` には引数が渡らないので `--apply` が付かず「今回は確認のみで動く」と指摘した。そのうえで「確認のみでもフォルダと DB は作られる」とも書いた。どちらもコードと照らして正しい。
- **設計上の落とし穴に気づく**: bash 大で「ロールバックで戻るのはコードだけで、DB のスキーマは戻らない」「リリースが1つしかないと、ロールバック先に新リリース自身を選んでしまう」と指摘した。どちらもコードと照らして正しい。
- **推測を明示する**: システムプロンプトの「推測で書く場合は、推測であると明記」という指示に従い、12回中8回で「推測」と書いた(haiku は0回)。
- **影響が無いことも書く**: 「ネットワーク通信はありません」「元の CSV は変更されません」のように、心配しなくてよい点も注意点に入れた。
- **文体**: 「〜します。」と文で書き切る。太字は少なめ。
- **長さ**: コードが長くてもステップをまとめ、python 大でも5〜6ステップ、2,600〜2,900字に収めた。

#### haiku の特徴

- **細かく分ける**: 関数1つごとにステップを立てる傾向があり、bash 大は13〜14ステップ(sonnet は11)、python 大は7〜8ステップ(sonnet は5〜6)だった。コードの引用も増えるので、長いコードほど解説が長くなる。
- **注意点は前提条件が中心**: 「sudo の権限が必要」「SSH 鍵の設定が必須」など、実行に必要な条件の列挙が多い。python 大では「SHA256 のハッシュ衝突」という、実用上ほぼ関係のない注意も挙げた。
- **文体**: 体言止めと「**用語** — 説明」の形が多く、太字を多用する(多い回で40か所)。
- **細かい誤り**: 読んだ範囲で次のものがあった。
  - python 大: 重複ファイルの退避先を `~/.duplicates` と記載した(正しくは `~/Pictures/.duplicates`)。
  - python 中: 入力ファイルが無いと「空の summary.csv になる」と記載した(実際はヘッダー行が書かれる。sonnet は正しく書いた)。
  - bash 小: `-mtime +7` を「7日以上前」と説明した(sonnet は「実質8日以上前」と補足した)。
  - python 中: `python3` の途中に見えない文字(ゼロ幅文字)が1つ混入した。
- **指示から外れた回**: bash 大の2回目で、冒頭に `# Bash スクリプト実行確認：アプリデプロイ` という表題を付けた(指示は「前置きは不要」)。

#### 共通点

- 指定した構成(冒頭の要約、ステップ別の詳細解説、注意点、まとめ)は、上の1回を除いてどちらも守った。
- 削除・上書き・`sudo` などの基本的な危険は、どちらも注意点に挙げた。
- bash 小のような短いコマンドでは内容の差は小さく、ほぼ同じ3ステップ構成だった。

### 2.5 追加確認(思考・使用モデル・入力トークン・費用)

「haiku だけが遅いのは、本文の前に思考しているからではないか」という指摘を受けて、bash 小のサンプルで各モデル1回ずつ、届いたイベントの種類と時刻、`usage` を記録した。

| 項目 | sonnet | haiku |
| --- | --- | --- |
| 実際のモデル | `claude-sonnet-5-5` | `claude-haiku-4-5-20251001` |
| 思考ブロック | なし(思考トークン 0) | あり(思考トークン 330) |
| 応答の開始(`message_start`) | 1.5秒 | 2.2秒 |
| 本文の最初の文字 | 1.5秒 | 5.0秒 |
| 完了 | 7.9秒 | 11.0秒 |
| 入力トークン(キャッシュ読み + キャッシュ作成 + 通常) | 799 + 541 + 2 = 1,342 | 30,570 + 1,733 + 10 = 32,313 |
| 出力トークン(うち思考) | 926(0) | 1,083(330) |
| 本文の字数 | 1,238 | 1,003 |
| 本文の生成の速さ | 約145トークン/秒 | 約125トークン/秒 |
| 1回の費用 | 約0.0127ドル(うち haiku の補助呼び出し 0.0011ドル) | 約0.0130ドル |

- sonnet を指定した実行でも、`modelUsage` には haiku の小さな呼び出し(入力976・出力18トークン)が1つ含まれていた。CLI 内部の補助的な呼び出しと見られるが、中身は確認していない。
- haiku のときだけ入力が約32,000トークンになる理由は確認していない。`--system-prompt` と `--tools ""` はどちらのモデルにも同じように付けている。

記録した出力(`usage` と `modelUsage` は長いので要点だけに縮めてある):

`````text
== sonnet ==
    1.5s message_start model=claude-sonnet-5-5 usage={"input_tokens": 2, "cache_creation_input_tokens": 541, "cache_read_input_tokens": 799, ...}
    7.9s message_delta usage={"input_tokens": 2, "cache_creation_input_tokens": 541, "cache_read_input_tokens": 799, "output_tokens": 926, "output_tokens_details": {"thinking_tokens": 0}, ...}
  result: duration_ms=7085 api_ms=7887 ttft_ms=7066
  modelUsage: claude-haiku-4-5-20251001 = 入力 976 / 出力 18 / 0.001066 ドル、claude-sonnet-5-5 = 入力 2 / 出力 926 / キャッシュ読み 799 / キャッシュ作成 541 / 思考 0 / 0.0115878 ドル
  本文 1238 字
  初出   0.8s  system:init  x1
  初出   0.8s  system:status  x1
  初出   1.5s  stream:message_start  x1
  初出   1.5s  stream:content_block_start:text  x1
  初出   1.5s  stream:content_block_delta:text_delta  x191
  初出   1.6s  rate_limit_event  x1
  初出   7.9s  assistant  x1
  初出   7.9s  stream:content_block_stop  x1
  初出   7.9s  stream:message_delta  x1
  初出   7.9s  stream:message_stop  x1
  初出   7.9s  result  x1

== haiku ==
    2.2s message_start model=claude-haiku-4-5-20251001 usage={"input_tokens": 10, "cache_creation_input_tokens": 1733, "cache_read_input_tokens": 30570, ...}
   11.0s message_delta usage={"input_tokens": 10, "cache_creation_input_tokens": 1733, "cache_read_input_tokens": 30570, "output_tokens": 1083, "output_tokens_details": {"thinking_tokens": 330}, ...}
  result: duration_ms=9696 api_ms=10426 ttft_ms=3757
  modelUsage: claude-haiku-4-5-20251001 = 入力 986 / 出力 1097 / キャッシュ読み 30570 / キャッシュ作成 1733 / 思考 330 / 0.012994 ドル
  本文 1003 字
  初出   1.3s  system:init  x1
  初出   1.3s  system:status  x1
  初出   1.3s  rate_limit_event  x1
  初出   2.2s  stream:message_start  x1
  初出   2.2s  stream:content_block_start:thinking  x1
  初出   2.6s  system:thinking_tokens  x4
  初出   2.6s  stream:content_block_delta:thinking_delta  x4
  初出   5.0s  stream:content_block_delta:signature_delta  x1
  初出   5.0s  assistant  x2
  初出   5.0s  stream:content_block_stop  x2
  初出   5.0s  stream:content_block_start:text  x1
  初出   5.0s  stream:content_block_delta:text_delta  x234
  初出  11.0s  stream:message_delta  x1
  初出  11.0s  stream:message_stop  x1
  初出  11.0s  result  x1
`````

#### 指摘された5つの仮説と確認結果

| 仮説 | 結果 |
| --- | --- |
| 1. haiku だけが見えない思考をしている | 確認できた。haiku は 2.2〜5.0秒の間に思考ブロックを出し、その後に本文が始まった。sonnet には思考が無かった。effort `low` が haiku に効いていないのかどうか(原因)までは確認していない |
| 2. 出力速度が同じなのは不自然(計測側の丸め、または本文途中の思考) | 支持する結果は出なかった。本文途中の思考は無く、思考は冒頭の1ブロックだけだった。比べているのは Haiku 4.5 と Sonnet 5.5 で世代が違い、確認した1回では sonnet のほうが本文の生成が速かった。計測側の丸めは否定しきれないが、デルタの数(191個と234個)に一定ペースへ揃えられた様子は無い |
| 3. プロンプトキャッシュの効き方の違い | 「sonnet 側だけ温まっている」という形ではなかった。haiku は約30,600トークンをキャッシュから読んでおり、応答開始の差は0.7秒だった。代わりに、haiku だけ入力が約24倍大きいという違いが見つかった |
| 4. サーバー側の混雑・割り当て | 判断できない。python 大の34秒の外れ値が長い思考なのか混雑なのかは区別できていない |
| 5. 出力が長いこと(完了時間への上乗せ) | そのとおり。完了時間の差を広げた要因で、最初の文字までの時間とは別である |

### 2.6 確認できたこと・できていないこと

確認できたこと:

- 今回の条件では、最初の文字までの時間は24回すべてで sonnet が短い。
- haiku は本文の前に思考ブロックを出し、sonnet は出さない(各1回の確認)。
- 別名は `sonnet` が `claude-sonnet-5-5`、`haiku` が `claude-haiku-4-5-20251001` に解決された。
- haiku のときの入力トークンは sonnet の約24倍で、1回あたりの費用はほぼ同じだった(各1回の確認)。
- 読んだ範囲では、sonnet の解説のほうが正確で、判断に役立つ指摘が多かった。

確認できていないこと:

- haiku が思考する原因(effort の扱い)と、入力が大きくなる原因。
- haiku の思考を切った場合の速度。
- 時間帯による違い、3回以上の繰り返しでのばらつき。
- 24回すべての解説文の全文での読み比べ(一部は集計だけ)。
- 英語の解説、Bash 以外のツール(Write・Edit など)、Windows での動作。
- hooknotice の通知ウィンドウ上での体感(計測は `claude -p` を直接呼んで行い、ウィンドウは開いていない)。
- 追加確認の2回ぶんの解説文は保存していない(字数だけ記録した)。

## 3. 条件

| 項目 | 内容 |
| --- | --- |
| 実施日 | 2026-10-11 |
| OS | macOS(Darwin 27.0.0) |
| Claude Code | 2.1.292 |
| hooknotice | 0.1.8(システムプロンプトは `plugins/hooknotice/messages.py` の `_EXPLAIN_PROMPT_JA`) |
| 比べたモデル | `sonnet`(`claude-sonnet-5-5`)と `haiku`(`claude-haiku-4-5-20251001`) |
| effort | `low`(既定値) |
| 言語 | 日本語 |
| サンプル | bash と python、それぞれ小・中・大の計6種類。すべて Bash ツールの入力(`command` と `description`)として渡した |
| 回数 | 本計測は 6サンプル × 2モデル × 2回 = 24回。追加確認は bash 小で各モデル1回 = 2回 |
| 実行の順番 | 1つずつ順番に実行。同じサンプルの1回目は sonnet → haiku、2回目は haiku → sonnet の順 |
| 作業ディレクトリ | 一時フォルダ(プロジェクトの CLAUDE.md を読み込ませないため。hooknotice と同じ) |
| 環境変数 | `HOOKNOTICE_DISABLED=1`(計測用の claude から通知を出さないため。hooknotice と同じ) |
| 入力の「作業ディレクトリ」欄 | `~/work/sample`(架空) |

呼び出しの引数は、hooknotice 0.1.8 の `notify_window.py`(`_start_explain`)と同じにした。

`````text
claude -p --model <モデル> --effort low \
  --output-format stream-json --verbose --include-partial-messages \
  --tools "" --setting-sources "" --no-session-persistence \
  --system-prompt <システムプロンプト> <入力>
`````

実際の hooknotice との違い:

- hooknotice は Qt の `QProcess` から起動する。計測は Python の `subprocess` から起動した。
- 入力は実際の Hook から届いたものではなく、計測用に書いたサンプルである。python のサンプルは `python3 -c` とヒアドキュメント(`python3 - <<'EOF'`)の形で Bash ツールに渡した。
- サンプルはどれも 8,000字の上限(`EXPLAIN_INPUT_MAX_CHARS`)に収まっており、省略は起きていない。

## 4. 使用したプロンプトと回答

### 4.1 システムプロンプト

`````text
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
`````

### 4.2 入力

入力の書式は hooknotice の `explain.input`(日本語)と同じ。

#### bash 小(1行、55字): 7日より古いログを削除

モデルに渡した入力(JSON の中でコードの改行は `\n` になっています):

`````text
ツール: Bash
作業ディレクトリ: ~/work/sample
入力:
```json
{
  "command": "find . -name '*.log' -mtime +7 -print0 | xargs -0 rm -f",
  "description": "7日より古いログを削除"
}
```
`````

上の `command` の中身(読みやすい形):

`````bash
find . -name '*.log' -mtime +7 -print0 | xargs -0 rm -f
`````

#### bash 中(23行、610字): プロジェクトを世代バックアップ

モデルに渡した入力(JSON の中でコードの改行は `\n` になっています):

`````text
ツール: Bash
作業ディレクトリ: ~/work/sample
入力:
```json
{
  "command": "set -euo pipefail\nSRC=\"$HOME/Documents/projects\"\nDEST=\"/Volumes/Backup/projects\"\nSTAMP=$(date +%Y%m%d_%H%M%S)\nLOG=\"$DEST/backup_$STAMP.log\"\n\nif [ ! -d \"$DEST\" ]; then\n  echo \"バックアップ先が見つかりません: $DEST\" >&2\n  exit 1\nfi\n\nmkdir -p \"$DEST/$STAMP\"\nrsync -a --delete --exclude 'node_modules' --exclude '.venv' \\\n  --link-dest=\"$DEST/latest\" \"$SRC/\" \"$DEST/$STAMP/\" | tee \"$LOG\"\n\nln -sfn \"$DEST/$STAMP\" \"$DEST/latest\"\n\n# 30日より古い世代を消す\nfind \"$DEST\" -maxdepth 1 -type d -name '20*' -mtime +30 -exec rm -rf {} +\n\nCOUNT=$(find \"$DEST\" -maxdepth 1 -type d -name '20*' | wc -l | tr -d ' ')\necho \"完了: $STAMP (保持している世代: $COUNT)\"\n",
  "description": "プロジェクトを世代バックアップ"
}
```
`````

上の `command` の中身(読みやすい形):

`````bash
set -euo pipefail
SRC="$HOME/Documents/projects"
DEST="/Volumes/Backup/projects"
STAMP=$(date +%Y%m%d_%H%M%S)
LOG="$DEST/backup_$STAMP.log"

if [ ! -d "$DEST" ]; then
  echo "バックアップ先が見つかりません: $DEST" >&2
  exit 1
fi

mkdir -p "$DEST/$STAMP"
rsync -a --delete --exclude 'node_modules' --exclude '.venv' \
  --link-dest="$DEST/latest" "$SRC/" "$DEST/$STAMP/" | tee "$LOG"

ln -sfn "$DEST/$STAMP" "$DEST/latest"

# 30日より古い世代を消す
find "$DEST" -maxdepth 1 -type d -name '20*' -mtime +30 -exec rm -rf {} +

COUNT=$(find "$DEST" -maxdepth 1 -type d -name '20*' | wc -l | tr -d ' ')
echo "完了: $STAMP (保持している世代: $COUNT)"

`````

#### bash 大(90行、2096字): アプリをデプロイ

モデルに渡した入力(JSON の中でコードの改行は `\n` になっています):

`````text
ツール: Bash
作業ディレクトリ: ~/work/sample
入力:
```json
{
  "command": "set -euo pipefail\n\nAPP_NAME=\"webapp\"\nDEPLOY_ROOT=\"/srv/$APP_NAME\"\nRELEASES=\"$DEPLOY_ROOT/releases\"\nSHARED=\"$DEPLOY_ROOT/shared\"\nCURRENT=\"$DEPLOY_ROOT/current\"\nKEEP=5\nREPO=\"git@github.com:example/$APP_NAME.git\"\nBRANCH=\"${1:-main}\"\nSTAMP=$(date +%Y%m%d%H%M%S)\nNEW=\"$RELEASES/$STAMP\"\nHEALTH_URL=\"http://127.0.0.1:8080/healthz\"\n\nlog() { printf '[%s] %s\\n' \"$(date +%H:%M:%S)\" \"$*\"; }\ndie() { log \"ERROR: $*\" >&2; exit 1; }\n\nrollback() {\n  local prev\n  prev=$(ls -1 \"$RELEASES\" | sort | tail -n 2 | head -n 1)\n  [ -n \"$prev\" ] || die \"戻せるリリースがありません\"\n  log \"ロールバック: $prev\"\n  ln -sfn \"$RELEASES/$prev\" \"$CURRENT\"\n  sudo systemctl restart \"$APP_NAME\"\n}\n\ncommand -v git >/dev/null || die \"git がありません\"\ncommand -v uv >/dev/null || die \"uv がありません\"\n[ -d \"$SHARED\" ] || die \"$SHARED がありません\"\n\nFREE_KB=$(df -k \"$DEPLOY_ROOT\" | awk 'NR==2 {print $4}')\nif [ \"$FREE_KB\" -lt 1048576 ]; then\n  die \"空き容量が 1GB 未満です\"\nfi\n\nlog \"取得: $REPO ($BRANCH)\"\ngit clone --depth 1 --branch \"$BRANCH\" \"$REPO\" \"$NEW\"\nREV=$(git -C \"$NEW\" rev-parse --short HEAD)\nlog \"リビジョン: $REV\"\n\nlog \"共有ファイルをリンク\"\nln -s \"$SHARED/.env\" \"$NEW/.env\"\nln -s \"$SHARED/uploads\" \"$NEW/uploads\"\nln -s \"$SHARED/log\" \"$NEW/log\"\n\nlog \"依存をインストール\"\n(cd \"$NEW\" && uv sync --frozen --no-dev)\n\nlog \"静的ファイルを生成\"\n(cd \"$NEW\" && uv run python manage.py collectstatic --noinput >/dev/null)\n\nlog \"データベースをバックアップ\"\npg_dump \"$APP_NAME\" | gzip > \"$SHARED/backup/pre_$STAMP.sql.gz\"\n\nlog \"マイグレーション\"\nif ! (cd \"$NEW\" && uv run python manage.py migrate --noinput); then\n  rm -rf \"$NEW\"\n  die \"マイグレーションに失敗しました\"\nfi\n\nlog \"切り替え\"\nln -sfn \"$NEW\" \"$CURRENT\"\nsudo systemctl restart \"$APP_NAME\"\n\nlog \"ヘルスチェック\"\nok=0\nfor i in $(seq 1 10); do\n  if curl -fsS --max-time 3 \"$HEALTH_URL\" >/dev/null; then\n    ok=1\n    break\n  fi\n  sleep 2\ndone\n\nif [ \"$ok\" -ne 1 ]; then\n  log \"ヘルスチェックに失敗しました\"\n  rollback\n  exit 1\nfi\n\nlog \"古いリリースを削除 (残す数: $KEEP)\"\nls -1 \"$RELEASES\" | sort | head -n -\"$KEEP\" | while read -r old; do\n  rm -rf \"${RELEASES:?}/$old\"\ndone\n\nfind \"$SHARED/backup\" -name 'pre_*.sql.gz' -mtime +14 -delete\n\necho \"$STAMP $REV $BRANCH $(whoami)\" >> \"$SHARED/log/deploy.log\"\nlog \"完了: $STAMP ($REV)\"\n",
  "description": "アプリをデプロイ"
}
```
`````

上の `command` の中身(読みやすい形):

`````bash
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

command -v git >/dev/null || die "git がありません"
command -v uv >/dev/null || die "uv がありません"
[ -d "$SHARED" ] || die "$SHARED がありません"

FREE_KB=$(df -k "$DEPLOY_ROOT" | awk 'NR==2 {print $4}')
if [ "$FREE_KB" -lt 1048576 ]; then
  die "空き容量が 1GB 未満です"
fi

log "取得: $REPO ($BRANCH)"
git clone --depth 1 --branch "$BRANCH" "$REPO" "$NEW"
REV=$(git -C "$NEW" rev-parse --short HEAD)
log "リビジョン: $REV"

log "共有ファイルをリンク"
ln -s "$SHARED/.env" "$NEW/.env"
ln -s "$SHARED/uploads" "$NEW/uploads"
ln -s "$SHARED/log" "$NEW/log"

log "依存をインストール"
(cd "$NEW" && uv sync --frozen --no-dev)

log "静的ファイルを生成"
(cd "$NEW" && uv run python manage.py collectstatic --noinput >/dev/null)

log "データベースをバックアップ"
pg_dump "$APP_NAME" | gzip > "$SHARED/backup/pre_$STAMP.sql.gz"

log "マイグレーション"
if ! (cd "$NEW" && uv run python manage.py migrate --noinput); then
  rm -rf "$NEW"
  die "マイグレーションに失敗しました"
fi

log "切り替え"
ln -sfn "$NEW" "$CURRENT"
sudo systemctl restart "$APP_NAME"

log "ヘルスチェック"
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

log "古いリリースを削除 (残す数: $KEEP)"
ls -1 "$RELEASES" | sort | head -n -"$KEEP" | while read -r old; do
  rm -rf "${RELEASES:?}/$old"
done

find "$SHARED/backup" -name 'pre_*.sql.gz' -mtime +14 -delete

echo "$STAMP $REV $BRANCH $(whoami)" >> "$SHARED/log/deploy.log"
log "完了: $STAMP ($REV)"

`````

#### python 小(1行、95字): package.json の名前とバージョンを表示

モデルに渡した入力(JSON の中でコードの改行は `\n` になっています):

`````text
ツール: Bash
作業ディレクトリ: ~/work/sample
入力:
```json
{
  "command": "python3 -c \"import json,sys; d=json.load(open('package.json')); print(d['name'], d['version'])\"",
  "description": "package.json の名前とバージョンを表示"
}
```
`````

上の `command` の中身(読みやすい形):

`````bash
python3 -c "import json,sys; d=json.load(open('package.json')); print(d['name'], d['version'])"
`````

#### python 中(26行、867字): 売上CSVをカテゴリ別に集計

モデルに渡した入力(JSON の中でコードの改行は `\n` になっています):

`````text
ツール: Bash
作業ディレクトリ: ~/work/sample
入力:
```json
{
  "command": "python3 - <<'EOF'\nimport csv\nfrom collections import defaultdict\nfrom pathlib import Path\n\ntotals = defaultdict(float)\ncounts = defaultdict(int)\n\nfor path in sorted(Path(\"data\").glob(\"sales_*.csv\")):\n    with path.open(encoding=\"utf-8\", newline=\"\") as f:\n        for row in csv.DictReader(f):\n            if not row[\"amount\"]:\n                continue\n            totals[row[\"category\"]] += float(row[\"amount\"])\n            counts[row[\"category\"]] += 1\n\nwith open(\"summary.csv\", \"w\", encoding=\"utf-8\", newline=\"\") as f:\n    writer = csv.writer(f)\n    writer.writerow([\"category\", \"count\", \"total\", \"average\"])\n    for category in sorted(totals, key=totals.get, reverse=True):\n        total = totals[category]\n        n = counts[category]\n        writer.writerow([category, n, round(total), round(total / n, 1)])\n\nprint(f\"{len(totals)} カテゴリを summary.csv に書き出しました\")\nEOF",
  "description": "売上CSVをカテゴリ別に集計"
}
```
`````

上の `command` の中身(読みやすい形):

`````bash
python3 - <<'EOF'
import csv
from collections import defaultdict
from pathlib import Path

totals = defaultdict(float)
counts = defaultdict(int)

for path in sorted(Path("data").glob("sales_*.csv")):
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not row["amount"]:
                continue
            totals[row["category"]] += float(row["amount"])
            counts[row["category"]] += 1

with open("summary.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "count", "total", "average"])
    for category in sorted(totals, key=totals.get, reverse=True):
        total = totals[category]
        n = counts[category]
        writer.writerow([category, n, round(total), round(total / n, 1)])

print(f"{len(totals)} カテゴリを summary.csv に書き出しました")
EOF
`````

#### python 大(104行、3278字): 写真を整理して重複を退避

モデルに渡した入力(JSON の中でコードの改行は `\n` になっています):

`````text
ツール: Bash
作業ディレクトリ: ~/work/sample
入力:
```json
{
  "command": "python3 - <<'EOF'\nimport hashlib\nimport json\nimport os\nimport shutil\nimport sqlite3\nimport sys\nfrom datetime import datetime, timedelta\nfrom pathlib import Path\n\nROOT = Path.home() / \"Pictures\" / \"inbox\"\nLIBRARY = Path.home() / \"Pictures\" / \"library\"\nTRASH = Path.home() / \"Pictures\" / \".duplicates\"\nDB = LIBRARY / \"index.sqlite3\"\nEXTS = {\".jpg\", \".jpeg\", \".png\", \".heic\", \".mov\", \".mp4\"}\nDRY_RUN = \"--apply\" not in sys.argv\n\n\ndef sha256(path: Path, chunk: int = 1 << 20) -> str:\n    h = hashlib.sha256()\n    with path.open(\"rb\") as f:\n        while block := f.read(chunk):\n            h.update(block)\n    return h.hexdigest()\n\n\ndef taken_at(path: Path) -> datetime:\n    stat = path.stat()\n    return datetime.fromtimestamp(getattr(stat, \"st_birthtime\", stat.st_mtime))\n\n\ndef unique_name(dest: Path) -> Path:\n    if not dest.exists():\n        return dest\n    for i in range(1, 1000):\n        candidate = dest.with_name(f\"{dest.stem}_{i}{dest.suffix}\")\n        if not candidate.exists():\n            return candidate\n    raise RuntimeError(f\"名前を決められません: {dest}\")\n\n\nLIBRARY.mkdir(parents=True, exist_ok=True)\nTRASH.mkdir(parents=True, exist_ok=True)\ncon = sqlite3.connect(DB)\ncon.execute(\n    \"CREATE TABLE IF NOT EXISTS files (\"\n    \"hash TEXT PRIMARY KEY, path TEXT NOT NULL, size INTEGER, taken TEXT, added TEXT)\"\n)\n\nmoved = duplicates = skipped = 0\nfreed = 0\nactions = []\n\nfor path in sorted(ROOT.rglob(\"*\")):\n    if not path.is_file() or path.name.startswith(\".\"):\n        continue\n    if path.suffix.lower() not in EXTS:\n        skipped += 1\n        continue\n    digest = sha256(path)\n    row = con.execute(\"SELECT path FROM files WHERE hash = ?\", (digest,)).fetchone()\n    size = path.stat().st_size\n    if row and Path(row[0]).exists():\n        duplicates += 1\n        freed += size\n        target = unique_name(TRASH / path.name)\n        actions.append({\"action\": \"duplicate\", \"from\": str(path), \"to\": str(target), \"same_as\": row[0]})\n        if not DRY_RUN:\n            shutil.move(str(path), target)\n        continue\n    when = taken_at(path)\n    folder = LIBRARY / f\"{when:%Y}\" / f\"{when:%Y-%m}\"\n    target = unique_name(folder / f\"{when:%Y%m%d_%H%M%S}{path.suffix.lower()}\")\n    actions.append({\"action\": \"move\", \"from\": str(path), \"to\": str(target)})\n    moved += 1\n    if DRY_RUN:\n        continue\n    folder.mkdir(parents=True, exist_ok=True)\n    shutil.move(str(path), target)\n    con.execute(\n        \"INSERT OR REPLACE INTO files VALUES (?, ?, ?, ?, ?)\",\n        (digest, str(target), size, when.isoformat(), datetime.now().isoformat()),\n    )\n\nif not DRY_RUN:\n    con.commit()\n    limit = datetime.now() - timedelta(days=30)\n    for old in TRASH.iterdir():\n        if datetime.fromtimestamp(old.stat().st_mtime) < limit:\n            old.unlink()\n    for folder in sorted(ROOT.rglob(\"*\"), reverse=True):\n        if folder.is_dir() and not any(folder.iterdir()):\n            folder.rmdir()\ncon.close()\n\nreport = LIBRARY / f\"report_{datetime.now():%Y%m%d_%H%M%S}.json\"\nif not DRY_RUN:\n    report.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding=\"utf-8\")\n\nmode = \"確認のみ\" if DRY_RUN else \"実行\"\nprint(f\"[{mode}] 移動 {moved} 件 / 重複 {duplicates} 件 ({freed / 1e6:.1f} MB) / 対象外 {skipped} 件\")\nif DRY_RUN:\n    print(\"実際に動かすには --apply を付けて実行してください\")\nEOF",
  "description": "写真を整理して重複を退避"
}
```
`````

上の `command` の中身(読みやすい形):

`````bash
python3 - <<'EOF'
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path.home() / "Pictures" / "inbox"
LIBRARY = Path.home() / "Pictures" / "library"
TRASH = Path.home() / "Pictures" / ".duplicates"
DB = LIBRARY / "index.sqlite3"
EXTS = {".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4"}
DRY_RUN = "--apply" not in sys.argv


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


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
    raise RuntimeError(f"名前を決められません: {dest}")


LIBRARY.mkdir(parents=True, exist_ok=True)
TRASH.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(DB)
con.execute(
    "CREATE TABLE IF NOT EXISTS files ("
    "hash TEXT PRIMARY KEY, path TEXT NOT NULL, size INTEGER, taken TEXT, added TEXT)"
)

moved = duplicates = skipped = 0
freed = 0
actions = []

for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path.name.startswith("."):
        continue
    if path.suffix.lower() not in EXTS:
        skipped += 1
        continue
    digest = sha256(path)
    row = con.execute("SELECT path FROM files WHERE hash = ?", (digest,)).fetchone()
    size = path.stat().st_size
    if row and Path(row[0]).exists():
        duplicates += 1
        freed += size
        target = unique_name(TRASH / path.name)
        actions.append({"action": "duplicate", "from": str(path), "to": str(target), "same_as": row[0]})
        if not DRY_RUN:
            shutil.move(str(path), target)
        continue
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

report = LIBRARY / f"report_{datetime.now():%Y%m%d_%H%M%S}.json"
if not DRY_RUN:
    report.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8")

mode = "確認のみ" if DRY_RUN else "実行"
print(f"[{mode}] 移動 {moved} 件 / 重複 {duplicates} 件 ({freed / 1e6:.1f} MB) / 対象外 {skipped} 件")
if DRY_RUN:
    print("実際に動かすには --apply を付けて実行してください")
EOF
`````

### 4.3 回答

24回ぶんの解説文の全文は、長いので別ファイルに分けた: [20261011_explain_model_comparison_answers.md](20261011_explain_model_comparison_answers.md)

追加確認(2.5)の2回ぶんの解説文は保存していない。

## 5. 使用したコード

どのコードも、プロジェクトの外の一時フォルダに置いて実行した。リポジトリには含めていない。

実行したコマンド(`<作業フォルダ>` は一時フォルダ):

`````bash
# 本計測(24回)。引数: プラグインのフォルダ、結果の保存先、繰り返す回数
python3 <作業フォルダ>/bench_explain.py ~/.claude/plugins/cache/hooknotice/hooknotice/0.1.8 <作業フォルダ>/bench_result.json 2

# 解説文の集計
python3 -I <作業フォルダ>/analyze_structure.py <作業フォルダ>/bench_result.json
python3 -I <作業フォルダ>/analyze_excerpts.py <作業フォルダ>/bench_result.json

# 追加確認(速さの再計算と、各モデル1回の呼び出し)
python3 <作業フォルダ>/probe.py ~/.claude/plugins/cache/hooknotice/hooknotice/0.1.8 <作業フォルダ>/bench_result.json
`````

集計の2つは、実際にはファイルにせず、同じ内容をその場で `python3 -I -` に渡して実行した。

### bench_explain.py

`````python
"""hooknotice の「解説」と同じ引数で claude -p を呼び、モデルごとの応答速度を測る。"""
import json
import os
import subprocess
import sys
import tempfile
import time

PLUGIN = sys.argv[1]
OUT = sys.argv[2]
RUNS = int(sys.argv[3]) if len(sys.argv) > 3 else 2
sys.path.insert(0, PLUGIN)
import messages  # noqa: E402

PROMPT = messages._EXPLAIN_PROMPT_JA
INPUT_FMT = "ツール: {tool}\n作業ディレクトリ: {cwd}\n入力:\n```json\n{input}\n```"

BASH_S = "find . -name '*.log' -mtime +7 -print0 | xargs -0 rm -f"

BASH_M = r"""set -euo pipefail
SRC="$HOME/Documents/projects"
DEST="/Volumes/Backup/projects"
STAMP=$(date +%Y%m%d_%H%M%S)
LOG="$DEST/backup_$STAMP.log"

if [ ! -d "$DEST" ]; then
  echo "バックアップ先が見つかりません: $DEST" >&2
  exit 1
fi

mkdir -p "$DEST/$STAMP"
rsync -a --delete --exclude 'node_modules' --exclude '.venv' \
  --link-dest="$DEST/latest" "$SRC/" "$DEST/$STAMP/" | tee "$LOG"

ln -sfn "$DEST/$STAMP" "$DEST/latest"

# 30日より古い世代を消す
find "$DEST" -maxdepth 1 -type d -name '20*' -mtime +30 -exec rm -rf {} +

COUNT=$(find "$DEST" -maxdepth 1 -type d -name '20*' | wc -l | tr -d ' ')
echo "完了: $STAMP (保持している世代: $COUNT)"
"""

BASH_L = r"""set -euo pipefail

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

command -v git >/dev/null || die "git がありません"
command -v uv >/dev/null || die "uv がありません"
[ -d "$SHARED" ] || die "$SHARED がありません"

FREE_KB=$(df -k "$DEPLOY_ROOT" | awk 'NR==2 {print $4}')
if [ "$FREE_KB" -lt 1048576 ]; then
  die "空き容量が 1GB 未満です"
fi

log "取得: $REPO ($BRANCH)"
git clone --depth 1 --branch "$BRANCH" "$REPO" "$NEW"
REV=$(git -C "$NEW" rev-parse --short HEAD)
log "リビジョン: $REV"

log "共有ファイルをリンク"
ln -s "$SHARED/.env" "$NEW/.env"
ln -s "$SHARED/uploads" "$NEW/uploads"
ln -s "$SHARED/log" "$NEW/log"

log "依存をインストール"
(cd "$NEW" && uv sync --frozen --no-dev)

log "静的ファイルを生成"
(cd "$NEW" && uv run python manage.py collectstatic --noinput >/dev/null)

log "データベースをバックアップ"
pg_dump "$APP_NAME" | gzip > "$SHARED/backup/pre_$STAMP.sql.gz"

log "マイグレーション"
if ! (cd "$NEW" && uv run python manage.py migrate --noinput); then
  rm -rf "$NEW"
  die "マイグレーションに失敗しました"
fi

log "切り替え"
ln -sfn "$NEW" "$CURRENT"
sudo systemctl restart "$APP_NAME"

log "ヘルスチェック"
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

log "古いリリースを削除 (残す数: $KEEP)"
ls -1 "$RELEASES" | sort | head -n -"$KEEP" | while read -r old; do
  rm -rf "${RELEASES:?}/$old"
done

find "$SHARED/backup" -name 'pre_*.sql.gz' -mtime +14 -delete

echo "$STAMP $REV $BRANCH $(whoami)" >> "$SHARED/log/deploy.log"
log "完了: $STAMP ($REV)"
"""

PY_S = """python3 -c "import json,sys; d=json.load(open('package.json')); print(d['name'], d['version'])\""""

PY_M = r"""python3 - <<'EOF'
import csv
from collections import defaultdict
from pathlib import Path

totals = defaultdict(float)
counts = defaultdict(int)

for path in sorted(Path("data").glob("sales_*.csv")):
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not row["amount"]:
                continue
            totals[row["category"]] += float(row["amount"])
            counts[row["category"]] += 1

with open("summary.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "count", "total", "average"])
    for category in sorted(totals, key=totals.get, reverse=True):
        total = totals[category]
        n = counts[category]
        writer.writerow([category, n, round(total), round(total / n, 1)])

print(f"{len(totals)} カテゴリを summary.csv に書き出しました")
EOF"""

PY_L = r"""python3 - <<'EOF'
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path.home() / "Pictures" / "inbox"
LIBRARY = Path.home() / "Pictures" / "library"
TRASH = Path.home() / "Pictures" / ".duplicates"
DB = LIBRARY / "index.sqlite3"
EXTS = {".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4"}
DRY_RUN = "--apply" not in sys.argv


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


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
    raise RuntimeError(f"名前を決められません: {dest}")


LIBRARY.mkdir(parents=True, exist_ok=True)
TRASH.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(DB)
con.execute(
    "CREATE TABLE IF NOT EXISTS files ("
    "hash TEXT PRIMARY KEY, path TEXT NOT NULL, size INTEGER, taken TEXT, added TEXT)"
)

moved = duplicates = skipped = 0
freed = 0
actions = []

for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path.name.startswith("."):
        continue
    if path.suffix.lower() not in EXTS:
        skipped += 1
        continue
    digest = sha256(path)
    row = con.execute("SELECT path FROM files WHERE hash = ?", (digest,)).fetchone()
    size = path.stat().st_size
    if row and Path(row[0]).exists():
        duplicates += 1
        freed += size
        target = unique_name(TRASH / path.name)
        actions.append({"action": "duplicate", "from": str(path), "to": str(target), "same_as": row[0]})
        if not DRY_RUN:
            shutil.move(str(path), target)
        continue
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

report = LIBRARY / f"report_{datetime.now():%Y%m%d_%H%M%S}.json"
if not DRY_RUN:
    report.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8")

mode = "確認のみ" if DRY_RUN else "実行"
print(f"[{mode}] 移動 {moved} 件 / 重複 {duplicates} 件 ({freed / 1e6:.1f} MB) / 対象外 {skipped} 件")
if DRY_RUN:
    print("実際に動かすには --apply を付けて実行してください")
EOF"""

SAMPLES = [
    ("bash", "小", BASH_S, "7日より古いログを削除"),
    ("bash", "中", BASH_M, "プロジェクトを世代バックアップ"),
    ("bash", "大", BASH_L, "アプリをデプロイ"),
    ("python", "小", PY_S, "package.json の名前とバージョンを表示"),
    ("python", "中", PY_M, "売上CSVをカテゴリ別に集計"),
    ("python", "大", PY_L, "写真を整理して重複を退避"),
]
MODELS = ["sonnet", "haiku"]


def run(model: str, text: str) -> dict:
    env = dict(os.environ, HOOKNOTICE_DISABLED="1")
    args = [
        "claude", "-p", "--model", model, "--effort", "low",
        "--output-format", "stream-json", "--verbose", "--include-partial-messages",
        "--tools", "", "--setting-sources", "", "--no-session-persistence",
        "--system-prompt", PROMPT, text,
    ]
    start = time.monotonic()
    proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env, cwd=tempfile.gettempdir())
    first = None
    out = ""
    result = None
    for raw in proc.stdout:
        now = time.monotonic() - start
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if event.get("type") == "stream_event":
            delta = (event.get("event") or {}).get("delta") or {}
            if delta.get("type") == "text_delta":
                if first is None:
                    first = now
                out += delta.get("text", "")
        elif event.get("type") == "result":
            result = event
    proc.wait()
    total = time.monotonic() - start
    err = proc.stderr.read().decode("utf-8", "replace").strip()
    return {
        "ttft": first, "total": total, "chars": len(out), "exit": proc.returncode,
        "api_ms": (result or {}).get("duration_api_ms"),
        "model_used": sorted(((result or {}).get("modelUsage") or {}).keys()),
        "is_error": (result or {}).get("is_error"),
        "stderr": err[:300], "text": out,
    }


rows = []
for lang, size, code, desc in SAMPLES:
    payload = json.dumps({"command": code, "description": desc}, ensure_ascii=False, indent=2)
    text = INPUT_FMT.format(tool="Bash", cwd="~/work/sample", input=payload)
    lines = code.count("\n") + 1
    for i in range(RUNS):
        order = MODELS if i % 2 == 0 else MODELS[::-1]  # 順番の偏りを減らす
        for model in order:
            r = run(model, text)
            r.update(lang=lang, size=size, lines=lines, in_chars=len(code), model=model, run=i + 1)
            rows.append(r)
            ttft = f"{r['ttft']:.1f}" if r["ttft"] is not None else "-"
            print(f"{lang:6} {size} {lines:3}行 {model:6} #{i + 1} 初回表示 {ttft:>5}s 完了 {r['total']:5.1f}s "
                  f"出力 {r['chars']:4}字 exit={r['exit']} {r['model_used']} {r['stderr'][:80]}", flush=True)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
`````

### analyze_structure.py

`````python
"""保存した解説文の構成を数える(字数、ステップ数、箇条書き、太字、注意点の項目数など)。"""
import json, re, sys
rows = json.load(open(sys.argv[1], encoding='utf-8'))
print("lang size model run | 字数 | 冒頭文字数 | ####数 | コードブロック | 箇条書き | 表行 | 太字 | 注意点の項目数 | 規定外の見出し | 前置き/締め")
for r in rows:
    t = r['text']
    intro = t.split('---')[0].strip()
    steps = len(re.findall(r'^#### ', t, re.M))
    code = t.count('```') // 2
    bullets = len(re.findall(r'^\s*[-*] ', t, re.M))
    table = len(re.findall(r'^\|', t, re.M))
    bold = len(re.findall(r'\*\*[^*]+\*\*', t))
    m = re.search(r'^### 注意点\s*\n(.*)', t, re.M | re.S)
    cautions = len(re.findall(r'^[-*] ', m.group(1), re.M)) if m else 0
    heads = [h for h in re.findall(r'^#{1,6} .*', t, re.M) if not h.startswith('#### ') and h not in ('### ステップ別の詳細解説', '### 注意点')]
    print(f"{r['lang']:6} {r['size']} {r['model']:6} #{r['run']} | {len(t):4} | {len(intro):3} | {steps:2} | {code:2} | {bullets:3} | {table:2} | {bold:3} | {cautions:2} | {heads} | 先頭={t[:14]!r}")
def show(lang, size, model, run=1):
    for r in rows:
        if (r['lang'], r['size'], r['model'], r['run']) == (lang, size, model, run):
            print(f"\n{'='*20} {lang} {size} {model} #{run} {'='*20}\n{r['text']}")
for m in ('sonnet', 'haiku'):
    show('bash', '小', m)
for m in ('sonnet', 'haiku'):
    show('python', '中', m)
`````

### analyze_excerpts.py

`````python
"""大サンプルの冒頭・見出し・注意点を抜き出し、「推測」の回数などの文体の傾向を数える。"""
import json, re, sys
rows = json.load(open(sys.argv[1], encoding='utf-8'))
for lang in ('bash', 'python'):
    for model in ('sonnet', 'haiku'):
        for r in rows:
            if (r['lang'], r['size'], r['model'], r['run']) == (lang, '大', model, 1):
                t = r['text']
                intro = t.split('---')[0].strip()
                heads = re.findall(r'^#### .*', t, re.M)
                m = re.search(r'^### 注意点.*', t, re.M | re.S)
                print(f"\n{'='*15} {lang} 大 {model} #1 {'='*15}\n[冒頭]\n{intro}\n[見出し]\n" + "\n".join(heads) + f"\n[注意点以降]\n{m.group(0) if m else '(なし)'}")
# 規定外の見出しがあった回の先頭
for r in rows:
    if r['text'].startswith('#'):
        print("\n===== 先頭が見出しの回:", r['lang'], r['size'], r['model'], r['run'], "=====\n", r['text'][:400])
# 推測の明示、ゼロ幅文字など
for r in rows:
    t = r['text']
    print(r['lang'], r['size'], r['model'], r['run'], '推測:', t.count('推測'), 'ゼロ幅:', len(re.findall('[​‌‍﻿]', t)), '文末です/ます:', len(re.findall(r'(です|ます)。', t)))
`````

### probe.py

`````python
"""解説と同じ引数で1回ずつ呼び、届いたイベントの種類と時刻、usage を記録する。"""
import json, os, subprocess, sys, tempfile, time
sys.path.insert(0, sys.argv[1])
import messages
rows = json.load(open(sys.argv[2], encoding="utf-8"))
print("== 既存24回: 書き始めてからの出力速度(字/秒) と API 時間 ==")
for r in rows:
    gen = r["total"] - r["ttft"]
    print(f"{r['lang']:6} {r['size']} {r['model']:6} #{r['run']} {r['chars'] / gen:5.0f} 字/秒  api={r['api_ms']}ms total={r['total']:.1f}s")
code = "find . -name '*.log' -mtime +7 -print0 | xargs -0 rm -f"
text = "ツール: Bash\n作業ディレクトリ: ~/work/sample\n入力:\n```json\n" + json.dumps(
    {"command": code, "description": "7日より古いログを削除"}, ensure_ascii=False, indent=2) + "\n```"
for model in ("sonnet", "haiku"):
    args = ["claude", "-p", "--model", model, "--effort", "low", "--output-format", "stream-json", "--verbose",
            "--include-partial-messages", "--tools", "", "--setting-sources", "", "--no-session-persistence",
            "--system-prompt", messages._EXPLAIN_PROMPT_JA, text]
    start = time.monotonic()
    p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         env=dict(os.environ, HOOKNOTICE_DISABLED="1"), cwd=tempfile.gettempdir())
    print(f"\n== {model} ==")
    seen = {}
    counts = {}
    for raw in p.stdout:
        now = time.monotonic() - start
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        kind = e.get("type")
        if kind == "stream_event":
            ev = e["event"]
            kind = "stream:" + ev.get("type", "?")
            if ev.get("type") == "content_block_start":
                kind += ":" + ev["content_block"].get("type", "?")
            if ev.get("type") == "content_block_delta":
                kind += ":" + ev["delta"].get("type", "?")
            if ev.get("type") == "message_start":
                print(f"  {now:5.1f}s message_start model={ev['message'].get('model')} usage={json.dumps(ev['message'].get('usage'))[:400]}")
            if ev.get("type") == "message_delta":
                print(f"  {now:5.1f}s message_delta usage={json.dumps(ev.get('usage'))[:400]}")
        elif kind == "system":
            kind = "system:" + str(e.get("subtype"))
        if kind not in seen:
            seen[kind] = now
        counts[kind] = counts.get(kind, 0) + 1
        if e.get("type") == "result":
            print(f"  result: duration_ms={e.get('duration_ms')} api_ms={e.get('duration_api_ms')} ttft_ms={e.get('ttft_ms')}")
            print("  modelUsage=" + json.dumps(e.get("modelUsage"), ensure_ascii=False)[:900])
            print(f"  本文 {len(e.get('result') or '')} 字")
    p.wait()
    for k, t in sorted(seen.items(), key=lambda kv: kv[1]):
        print(f"  初出 {t:5.1f}s  {k}  x{counts[k]}")
`````
