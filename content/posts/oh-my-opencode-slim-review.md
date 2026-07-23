---
title: "AIサブスクを3つ使い分けてレート制限に悩まなくなった話"
images:
  - /images/oh-my-opencode-slim-review/ogp.png
slug: oh-my-opencode-slim-review
date: 2026-06-30
tags:
  - ai
  - ai_agents
  - opencode
  - oh_my_opencode_slim
---

OpenCode のレート制限を避けるために、月額AIサブスクを3つに分けて使っている。
各エージェントにモデルを割り当てる `oh-my-opencode-slim` の設定と、v1でプリセットが活きなかった理由、v2での変化を書く。

## この記事で分かること

- OpenCode のレート制限に対して、3つのAIサブスクをどう使い分けるか
- `oh-my-opencode-slim` でエージェントごとにモデルを割り振る設定
- v1でプリセットが活きなかった理由と、v2での変化

## OpenCode を使い始めてすぐ制限に当たった

OpenCode を使い始めてすぐに気づいたのが、レート制限の問題だ。
AIコーディングツールは一度使い始めると消費量がかなり多い。
1つのサブスクに頼っていると、あっという間に制限に当たる。

制限に引っかかるたびに作業が止まる。
それが積み重なると、ツールに払っているお金の価値が半減する。

## 月¥8,000前後で3プロバイダーを使い分ける構成に落ち着いた

解決策として考えたのが、複数の安価なサブスクを組み合わせて消費を分散させることだ。
特定のサブスクに消費が集中しなければ、それぞれの制限に当たりにくくなる。

ただし、月のコストは¥10,000以内に収めたい。
高額プランに課金すれば制限は緩和されるが、それでは本末転倒だ。

試行錯誤の過程で GitHub Copilot Pro や NanoGPT なども試した。
最終的に落ち着いたのが、現在の3サブスク構成だ。

| サブスク | 月額 |
|---|---|
| OpenCode Go | $10 |
| ChatGPT Plus | ¥3,000 |
| Ollama Cloud Pro | $20 |

合計は為替によって変動するが、¥8,000前後に収まっている。

ただし OpenCode Go だけは月の利用上限がある。他の2つにはない制限だ。

この分散を実現するために使っているのが oh-my-opencode-slim だ。

## oh-my-opencode-slim でエージェントごとにモデルを割り振れる

oh-my-opencode-slim は OpenCode の設定を拡張するツールだ。
類似のものに oh-my-openagent があるが、oh-my-opencode-slim はそれよりシンプルでスリムな設計になっている。

プリセット機能では、Orchestrator、Oracle、Librarian といった各エージェントに、使うモデルとスキル、MCP を一括で設定できる。
multiplexer は複数のペインを並列表示する機能で、作業の進捗を画面で確認できる。
設定ファイルには JSON スキーマが定義されているので、エディタの補完が効いて書きやすい。

## v1 では Orchestrator が全部やってしまい、プリセットが活きなかった

oh-my-opencode-slim は v2 で大きく変わった。

v1 の頃は、Orchestrator が計画から実装までほとんどの作業を担ってサブエージェントにはあまり作業を委譲していなかった。
専門のサブエージェントはほとんど使われず、Orchestrator に設定していたモデルの消費が集中していた。

v2 では、Orchestrator の役割が「計画、委譲、整合、検証」に絞られた。
実装は Fixer、UI/UX は Designer、調査は Explorer や Librarian といった専門サブエージェントが担う。

この変化が、複数モデルへの均等な分散を可能にした。
Orchestrator だけに消費が集中するのではなく、作業の種類によって適切なサブエージェントと、そこに紐づくモデルが使われる。

## プリセット「go-ollama-chatgpt」の設定

現在使っているプリセットの名前は `go-ollama-chatgpt` だ。
OpenCode Go、Ollama Cloud、ChatGPT（OpenAI）という3つのプロバイダーを組み合わせていることを示している。

設定はこんな感じ。

| エージェント | モデル | 主な用途 |
|---|---|---|
| Orchestrator | opencode-go/minimax-m3 | 計画、委譲、整合、検証 |
| Oracle | openai/gpt-5.5 | アーキテクチャ判断とデバッグ |
| Council | opencode-go/deepseek-v4-pro | 複数モデルの比較と統合 |
| Librarian | opencode-go/minimax-m3 | リサーチとドキュメント調査 |
| Explorer | opencode-go/deepseek-v4-flash | コード探索と構造把握 |
| Designer | ollama-cloud/kimi-k2.6 | UI/UX 実装 |
| Fixer | ollama-cloud/kimi-k2.7-code | コード実装と修正 |

Orchestrator は普段 `minimax-m3` を使っているが、`grill-with-docs` などのスキルを使う場合は、より「強い技術判断ができる司令塔」として `deepseek-v4-pro` に切り替えている。
スキルの種類によって Orchestrator だけモデルを変える、という運用だ。

Oracle に GPT-5.5 を割り当てているのは、アーキテクチャの判断や難しいデバッグには性能のいいモデルを使うべきだと考えたからだ。
精度が求められる場面に絞って使うことで、ChatGPT Plus のサブスクを有効活用できる。

OpenCode Go と Ollama Cloud は利用できるモデルが重なっているため、どちらに何を割り当てるかはコストのバランスで決めた。
DeepSeek V4 は Ollama Cloud より OpenCode Go のほうがコスパがいいので、DeepSeek V4 を使うエージェントは OpenCode Go に寄せる。
その分 Kimi は Ollama Cloud に割り振ることで、2つのサブスクの消費をバランスよく分散させている。

定義全体を載せておく。

```json
"go-ollama-chatgpt": {
  "orchestrator": {
    "model": "opencode-go/minimax-m3",
    "variant": "high",
    "skills": ["*"],
    "mcps": ["*", "!context7"]
  },
  "oracle": {
    "model": "openai/gpt-5.5",
    "variant": "high",
    "skills": ["simplify"],
    "mcps": []
  },
  "council": {
    "model": "opencode-go/deepseek-v4-pro",
    "variant": "high",
    "skills": [],
    "mcps": []
  },
  "librarian": {
    "model": "opencode-go/minimax-m3",
    "skills": [],
    "mcps": ["websearch", "context7", "gh_grep"]
  },
  "explorer": {
    "model": "opencode-go/deepseek-v4-flash",
    "variant": "medium",
    "skills": [],
    "mcps": []
  },
  "designer": {
    "model": "ollama-cloud/kimi-k2.6",
    "skills": [],
    "mcps": []
  },
  "fixer": {
    "model": "ollama-cloud/kimi-k2.7-code",
    "skills": [],
    "mcps": []
  }
}
```

## 使い始めは preset を1行指定するだけ

詳細なインストール手順や利用可能なプリセットの一覧は[公式リポジトリ](https://github.com/alvinunreal/oh-my-opencode-slim)を参照してほしい。

設定ファイルは `~/.config/opencode/oh-my-opencode-slim.json` に置く。
最小限の構成は以下の通りで、`preset` にプリセット名を指定するだけで動き始める。

```json
{
  "$schema": "https://unpkg.com/oh-my-opencode-slim@latest/oh-my-opencode-slim.schema.json",
  "preset": "go-ollama-chatgpt"
}
```

`$schema` を指定しておくと、エディタでの補完が効くようになる。
設定の全体像を把握しながら書けるので、試行錯誤のコストが下がる。

## 使ってみて

1サブスクに集中させていた頃は、制限に引っかかるたびに手が止まっていた。
3つに分散させてから、止まることがほぼなくなった。
月¥10,000以内に収まっているのも想定通り。

oh-my-opencode-slim のプリセット機能は、どのエージェントがどのプロバイダーを使うか一目でわかるのが気に入っている。
試行錯誤も設定の書き換えだけで済む。

v2 になって Orchestrator が委譲に徹するようになったのが、個人的には一番大きい変化だった。
v1 のときはプリセットをいくら細かく設定しても Orchestrator が全部自分でやってしまうので、正直あまり意味がなかった。

設定の詳細や他のプリセットは[公式リポジトリ](https://github.com/alvinunreal/oh-my-opencode-slim)にまとまっている。
