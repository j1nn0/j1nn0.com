---
title: "委譲先は CLI でなく役割で固定する。OMP と Codex を pi に置き換えた"
slug: agent-orchestration-pi
date: 2026-08-12
summary: "agent-orchestration スキルの調査役 OMP と実装役 Codex を、どちらも pi に置き換えた。モデルと役割はそのまま、委譲先の CLI を1本に寄せた理由と、動作確認で見つかった3つの問題と対処を書く。"
tags:
  - ai_agents
  - agent_skills
  - pi
images:
  - /images/agent-orchestration-pi/ogp.png
cover:
  image: images/agent-orchestration-pi/ogp.png
draft: false
---

前回の記事で、調査と実装だけを委譲する [`agent-orchestration`](https://github.com/j1nn0/skills) スキルを作った([前回の記事]({{< ref "agent-orchestration-skill" >}}))。その委譲先、OMP(oh-my-pi)と Codex を、どちらも pi に置き換えた。

役割もモデルも同じままだ。変わったのは動かす CLI だけ。理由は単純で、委譲先が重かったからだ。

## 重さの正体は3つ

### OMP は pi のフォークで機能過多

OMP は Mario Zechner の [pi](https://github.com/earendil-works/pi) を [can1357](https://github.com/can1357/oh-my-pi) がフォークしたもので、IDE 連携、LSP、ブラウザ、デバッガ、サブエージェントなどを足した「全部入り」だ。

調査と実装の委譲先に、これらの機能は要らない。むしろ、設定と拡張の管理コストだけが増える。base の pi で足りる。

### 設定・権限・状態が CLI ごとに別々

OMP と Codex は別の CLI なので、設定ファイルも権限システムもセッション管理も2本立てになる。旧スキルは「モデルと思考レベルの割り当てを CLI の設定ファイルに頼るな」と明記し、起動時のフラグで固定していた。

そのフラグ自体が CLI ごとに違う体系だった。OMP は `--thinking xhigh`、Codex は `-c model_reasoning_effort=max`。同じ「最上位の思考」を、別の名前と別のフラグで指定していた。

### 動かすとノイズが出る

委譲先を起動すると、拡張の再インストールが走り、警告が並び、権限の確認ダイアログが出る。詳しくは後述の動作確認で触れるが、起動のたびにこれが付きまとうのは地味に重い。

一方、モデルは最初から pi から使えた。`opencode-go/deepseek-v4-flash` は pi のモデルカタログにあり、`gpt-5.6-luna` も `openai-codex` プロバイダ経由で同じものが使える。

つまり重かったのはモデルではなく、CLI の側だった。

## CLI でなく役割で固定する

置き換え後の構成はこうなった。オーケストレーターの固定もやめた。初版のスキルは Claude Code と Opus 5 を前提に書いていたが、今は「現在のエージェント」とだけ書く。固定するのは役割とモデルだけだ。

| 役割 | 変更前 | 変更後 |
| --- | --- | --- |
| 判断とレビュー | Claude Code(Opus 5) | 現在のエージェント(固定しない) |
| 調査と研究(読み取り専用) | OMP(kind `omp`) | pi `explorer` |
| 実装 | Codex(kind `codex`) | pi `fixer` |

起動コマンドは、こう変わった。

```bash
# 変更前
herdr agent start omp --kind omp --pane <pane-id> -- \
  --model opencode-go/deepseek-v4-flash \
  --thinking xhigh

herdr agent start codex --kind codex --pane <pane-id> -- \
  --model gpt-5.6-luna \
  -c model_reasoning_effort=max
```

```bash
# 変更後
herdr agent start explorer --kind pi --pane <pane-id> -- \
  --model opencode-go/deepseek-v4-flash \
  --thinking max \
  --no-autoformat \
  --no-autofix

herdr agent start fixer --kind pi --pane <pane-id> -- \
  --model openai-codex/gpt-5.6-luna \
  --thinking max \
  --no-autoformat \
  --no-autofix
```

ここで1つ注意したいのが、`xhigh` と `max` の関係だ。OMP の `xhigh` は DeepSeek の `reasoning_effort=max` にマップされる値で、pi の `max` も同じ値を指す([DeepSeek API の互換マッピング](https://api-docs.deepseek.com/guides/thinking_mode))。思考レベルが一段上がったわけではない。名前の体系が pi に揃っただけだ。

### 見送った案: ツールの allowlist による読み取り専用の強制

pi には `--tools read,grep,find,ls` のように、使えるツールを制限する仕組みがある。調査役の読み取り専用を、プロンプトの指示でなく構造で強制できる。最初はこれを入れるつもりだった。

やめた理由は、allowlist のメンテナンスだ。新しいスキルやツールを追加するたびに、explorer 側にも同じリストを足さないといけなくなる。役割の分離は、引き続きプロンプトの指示で行うことにした。スキルには「explorer は読み取り専用。ファイルの変更は fixer だけ」とだけ書いてある。

## 動作確認で見つかった3つの問題

切り替えて実際に調査と実装を委譲してみて、3つの問題が見つかった。どれも最終版の構成で解消した。

### 1. 拡張の起動ごと再インストール

最初の版は、委譲先に専用の拡張構成を指定していた。すると起動のたびに拡張のインストールが走り、136パッケージを9秒かけて入れ直すログと、`allow-scripts` の警告が並んだ。スキル定義の衝突表示も出た。

対処は、委譲先も通常の pi 構成にすることだ。拡張とスキルの自動ロードに任せ、コマンドから拡張指定を外した。スキルには「委譲先は通常の pi の拡張・スキル・ツールを使う」とだけ書く。これで再インストールも警告も消えた。

### 2. 権限の確認ダイアログ

pi は本体には権限ダイアログを持たず、[pi-permission-system](https://github.com/gotgenes/pi-packages/tree/main/packages/pi-permission-system) という拡張が `allow / ask / deny` の判定と確認UIを足している。委譲先でも `ask` 判定のたびにダイアログが出て、往復が増えた。

これをスキルで回避しようとすると、スキルが肥大化する。設定で解決した。`yoloMode: true` にして、`ask` だけ自動承認にする。`rm -rf` や `sudo` などの `deny` ルールは残るので、危険操作の拒否は維持される。

### 3. herdr agent read に thinking が混ざる

これがいちばん効いた気づきだ。pi は思考ログを端末に書くので、`herdr agent read` が推論をそのまま拾う。長い調査だと、報告本文の前に思考が混ざり、最終回答の切り出しに注意が要る。

対処として、委譲先の報告を必ず専用ブロックで終わらせるルールをスキルに足した。

```text
<HERDR_RESULT>
結論と根拠
</HERDR_RESULT>
```

読み手は最後の完全な `HERDR_RESULT` ブロックだけを引き継ぎ結果として扱い、前の thinking や進行ログは無視する。ブロックが見えない場合は、作業をやり直させず最終回答だけを再出力させる。長すぎる調査報告も、調査の再実行ではなく短いブロックの再出力で対応する。

## 残る制約

切り替え後、このスキルを前提にした [continuous-improvement-loop](https://github.com/j1nn0/skills/blob/main/skills/continuous-improvement-loop/SKILL.md) を作り、laravel-encrypted-s3 を [v1.0.0-RC3](https://packagist.org/packages/j1nn0/laravel-encrypted-s3) まで改善した。

調査と実装の委譲は、その自律改善ループの中で実際に回っている。

ただ、切り替えてからまだ1日だ。この記事で報告できるのは、動作確認で見つけた3つの問題と対処までで、長期運用の実績はまだない。

thinking の混入はブロック規約で回避しているが、オーケストレーターが読み取るコスト自体は残る。前回の記事で書いた「ハブ&スポークのボトルネック」と「実装の待機時間」も、そのままだ。

## 委譲先を選ぶときの基準

スキルは [`j1nn0/skills`](https://github.com/j1nn0/skills) で公開している。

```sh
npx skills@latest add j1nn0/skills -s agent-orchestration
```

今回の変更で得た基準は一つ。「委譲先は、CLI の機能の多さで選ばない。役割とモデルを固定できるかで選ぶ」。調査と実装に必要なのは、モデルの指定と思考レベルの指定が確実に効くことだけだ。その2つが固定できるなら、CLI はオーケストレーターと同じ1本でいい。
