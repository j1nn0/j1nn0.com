---
title: "AIエージェントをコンテナに入れず、devcontainer execで動かしている話"
images:
  - /images/ai-agent-devcontainer-exec/ogp.png
cover:
  image: images/ai-agent-devcontainer-exec/ogp.png
date: 2026-07-07
draft: false
tags:
  - ai_agents
  - development_environment
  - devcontainer
---

## この記事で分かること

- ホストで動かすAIエージェントから Dev Container 内の PHP と Node.js を実行する方法
- `devcontainer exec` を使うときの実行ルールとサンドボックスの扱い
- コンテナ内にAIエージェントを入れない構成を選んだ理由

Laravel と Vue を使った Web アプリの開発環境は、Dev Container CLI で起動する Docker Compose コンテナの中に置いている。
PHP や Node.js のランタイムもコンテナ内にある。
一方で、AI エージェントはホストマシン上で動かしている。
そのため、エージェントが `php artisan` や `pnpm run build` をそのまま実行すると、エラーになる。

今は、エージェントには必ず `devcontainer exec` 経由でコマンドを実行させるようにしている。
コンテナ内にエージェントを入れる案も一度考えたが、アップデートや認証情報や設定の管理が面倒になりそうだった。
少なくとも自分の運用では、エージェントはホストで管理し、言語ランタイムだけ Dev Container 越しに叩く形がいちばん扱いやすかった。

## ホストのエージェントから Dev Container 内のランタイムを叩く

構成はこんな感じ。

| 対象 | 実行場所 |
| --- | --- |
| AI エージェント | ホストマシン |
| PHP | Docker Compose コンテナ |
| Composer | Docker Compose コンテナ |
| Node.js | Docker Compose コンテナ |
| pnpm と npm | Docker Compose コンテナ |
| Laravel のコマンド | Docker Compose コンテナ |

実行の流れはこうなる。

```text
AI agent on host
  -> devcontainer exec --remote-env AI_AGENT=1
  -> Docker Compose container
  -> php / composer / pnpm / npm / vendor/bin/*
```

この構成にすると、エージェントのファイル編集とコード読解はホスト側で完結する。
ただし、実行だけはコンテナ内に入る必要がある。
Laravel や Vue のプロジェクトでは、依存パッケージも環境変数もコンテナ側に寄っているので、ホストでコマンドを叩くと別の環境を見てしまう。

## AGENTS.md ではコマンド例より実行ルールを優先させる

そこで、AGENTS.md にコマンド実行のルールを書いている。
エージェントが迷わないように、例外を増やさず一律の形にした。

設定はこんな感じ。

````md
## Command Execution

- PHP and Node.js runtimes are inside Docker Compose containers, not on the host machine.
- Always run `php`, `composer`, `node`, `pnpm`, `npm`, and `vendor/bin/*` through `devcontainer exec --remote-env AI_AGENT=1`.
- These command execution rules override all command examples below, including Laravel Boost examples. When an example shows `php artisan`, `composer`, `node`, `pnpm`, `npm`, or `vendor/bin/*`, run it through `devcontainer exec --remote-env AI_AGENT=1`.
- The `devcontainer` command itself must be executed outside the agent's sandbox environment.

Examples:

```sh
devcontainer exec --remote-env AI_AGENT=1 php artisan route:list
devcontainer exec --remote-env AI_AGENT=1 composer install
devcontainer exec --remote-env AI_AGENT=1 pnpm install --frozen-lockfile
devcontainer exec --remote-env AI_AGENT=1 pnpm run build
devcontainer exec --remote-env AI_AGENT=1 vendor/bin/pint --dirty --format agent
devcontainer exec --remote-env AI_AGENT=1 php artisan test --env=testing --compact
```
````

ポイントは、コマンド例そのものよりも「下に出てくる例よりこのルールを優先する」と明記しているところだ。
Laravel Boost などのツールが `php artisan` の例を出しても、エージェントには `devcontainer exec` を付けて実行してほしい。
この上書き関係を書かないと、エージェントは近くにあるコマンド例を素直に実行しがちだ。

## `devcontainer` 自体はサンドボックスの外で動かす

もうひとつ面倒なのが、`devcontainer` コマンド自体の扱いだ。
プロジェクトの PHP や Node.js はコンテナ内にあるが、コンテナへ入るための `devcontainer` コマンドはホスト側で実行する。
エージェントのサンドボックス内から無理に実行しようとすると、Docker や Dev Container CLI に届かないことがある。

そのため、AGENTS.md には `devcontainer` コマンド自体はエージェントのサンドボックス外で実行する、と書いている。
これは少しややこしい。
コマンドの目的地はコンテナ内だが、入口はホスト側にある。

## `AI_AGENT=1` は Laravel PAO に向けた目印

`--remote-env AI_AGENT=1` は、Laravel PAO にエージェント実行だと認識させるために付けている。
PAO 側がエージェントによるコマンド実行だと分かると、それに合わせた挙動を取れる。
この記事では PAO の内部挙動までは扱わない。

正直に言うと、上の例で `AI_AGENT=1` が意味を持つのは主に `php artisan` だ。
`composer install` や `pnpm run build` に付けても、ほとんど意味はない。
ただ、コマンドごとに付けたり外したりするルールにすると、エージェントにも自分にも余計な分岐が増える。

なので一律で付けている。
少し雑だが、運用ルールとしてはそのほうが壊れにくい。

## コンテナ内にエージェントを入れる案はやめた

最初は、コンテナ内にエージェントをインストールしてしまえば話が早いのでは、と思った。
PHP も Node.js もコンテナ内にあるなら、エージェントも同じ場所に置けばコマンド実行で悩まない。
考え方としては自然だ。

ただ、自分の運用ではすぐに面倒になりそうだった。
エージェント本体のアップデートをコンテナごとに考える必要がある。
認証情報や設定ファイルの置き場所も増える。
開発コンテナを作り直したときに、エージェント側の状態まで気にしないといけない。

それなら、エージェントはホストに置いたままにしておくほうがよかった。
ホスト側のエージェントを普段どおり更新し、プロジェクト固有の実行だけ `devcontainer exec` に寄せる。
役割が分かれるので、トラブルの切り分けもしやすい。

## 使ってみて

この運用にしてから、エージェントに実行させるコマンドの事故は減った。
少なくとも、ホストに PHP や Node.js がないことを忘れて失敗するパターンは避けやすい。
AGENTS.md に書いたルールが効けば、`php artisan test` も `pnpm run build` も同じ形でコンテナ内に流れる。

もちろん、これが最終形だとは思っていない。
`AI_AGENT=1` を全コマンドに付けているところは雑だし、`devcontainer` をサンドボックス外で動かす扱いも環境によって差が出そうだ。
それでも、今の自分の Laravel と Vue の開発環境では、この形でかなり落ち着いている。

他の人が、AI エージェントと Dev Container の距離感をどうしているのかは気になっている。
