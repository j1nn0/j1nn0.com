---
title: "Claude Code用にカスタマイズしたStatusLineをPiへ移植し、pi-footerを公開した"
slug: pi-footer
date: 2026-10-06
summary: "Claude Code用にカスタマイズしていたStatusLineをPiのフッターへ移植した。pi-minimal-footerをフォークし、使う3プロバイダに絞って公開した。公開後に表示が消えたOpenCode Goのクォータを直した記録を書く。"
tags:
  - ai_agents
  - terminal
  - pi
images:
  - /images/pi-footer/ogp.png
cover:
  image: images/pi-footer/ogp.png
draft: false
---

Claude Codeを使っていたとき、StatusLineを自分好みにカスタマイズしていた。
モデル、コンテキスト使用量、プロンプトキャッシュ、レートリミット、セッション経過時間、Gitブランチ、Context Modeの使用量を2行に並べる設定だ。
スクリプトは[Gist](https://gist.github.com/j1nn0/03bd9a1d054ed32463b0613bbc40fd15)に置いている。

エージェント作業の中心をPiへ移してからも、この情報をフッターで見たかった。
Piの標準フッターは1行で、セッション全体のトークン累計とコスト、コンテキスト使用率、モデル名を出す。
プロバイダのレートリミット、セッションの経過時間、Context Modeの蓄積は出ない。

近いものはあった。
Can Celik氏の[pi-minimal-footer](https://github.com/ogulcancelik/pi-extensions/tree/main/packages/pi-minimal-footer)だ。
2行のフッターにモデル、コンテキストゲージ、サブスクリプションの使用量、Git状態を表示する。
ただ、自分のStatusLineが持っていた情報とは完全には揃わない。

使用量に対応するプロバイダは8種類ある。
自分が使う3つ(openai-codex、opencode-go、command-code)に対して過不足があった。

それなら自分の道具に作り替えようと、フォークして作ったのが[pi-footer](https://github.com/j1nn0/pi-footer)だ。
npmの[`@j1nn0/pi-footer`](https://www.npmjs.com/package/@j1nn0/pi-footer)として公開していて、現在のバージョンはv0.1.1(2026年10月6日時点)。
表示は次の2行になる。

```text
deepseek-v4.1-flash · max · think ON │ ctx ████░░░░░░ 41% · 161.0k/384.0k │ cache R424.0k/W2.1k
5h 22% ↻ 15:03 │ 7d 66% ↻ 10/08 10:00 │ 6h29m │ main * ↑2 │ ctx-mode 426KB
```

## 出発点は、自分でカスタマイズしていたStatusLineだった

移植元のStatusLineは、一行目にモデル、thinking level、コンテキストのゲージと使用トークン、プロンプトキャッシュの読み書きを並べる。
二行目は、サブスクリプションの5時間と7日の使用率、リセット時刻、セッションの経過時間、Gitブランチ、Context Modeの蓄積量だ。

どれも作業中に判断へ使っていた情報だ。
コンテキスト使用率は70%で`!`、85%で`⚠`、95%で`COMPACT`の印が付き、compactionが近いことに気づける。
プロンプトキャッシュの読み書きは、直前の応答でどれだけプロンプトの再計算を省けたかの目安になる。
レートリミットは、その日の残りと相談してペースを変えるために見ていた。
経過時間は、セッションを切り替えるかどうかの判断に使う。

移植にあたっては、表示の意味、警告の閾値、リセット時刻の書式、セグメントの並び順をこのGistのスクリプトのまま引き継いだ。
自分の環境で動いていた挙動が、そのまま仕様になる。
Pi側のAPIで取れない値は、それらしい数字で埋めず、取れないまま表示する方針にした。

## pi-minimal-footerをフォークして、単一パッケージに組み直す

フォーク元は、Can Celik氏が公開している[ogulcancelik/pi-extensions](https://github.com/ogulcancelik/pi-extensions)のモノレポに入っていたpi-minimal-footer 0.1.13だ。
モノレポの依存はPi 0.80系だった。
実装は39KBの単一ファイルで、使用量の対応プロバイダは8種類ある。

作り替えはフェーズを分け、作業はすべてエージェントに渡して進めた。
自分が書いたタスク文をClaude Codeのセッションに置く。
そのセッションがherdr経由でPiの子エージェントを起動し、調査(読み取り専用)と実装を振り分ける形だ。
コミットとレビューはオーケストレーター側に残した。

最初のフェーズは、モノレポからこのパッケージだけをルートへ昇格する作業だ。
単一リポジトリにして、Pi 1.0へ移行した。
フッターの見た目と挙動は変えない条件を付けた。

Pi 1.0が公開されたのは、この作業を始めた日の未明だった。
互換性の判断は、公開済みパッケージの型定義を正とした。
拡張が使うAPIを列挙して、調査役に一つずつ確認させた。
対象は`setFooter`、`getContextUsage`、`thinkingLevel`、`sessionManager`、pi-tuiのヘルパーなどで、すべて互換だった。
移行の前に、当時の表示と通信をそのまま固定するテストを書いた。
そのあとで39KBのファイルを責務ごとに分割した。
イベント配線は`src/index.ts`に残し、描画、セッション、Git、使用量プロバイダを別ファイルに分けている。

フォーク元のMITライセンスと著作権表記はそのまま残した。
package.jsonのcontributorsにCan Celik氏を記載した。
ツールチェーンは先に作った[pi-input-lock](https://github.com/j1nn0/pi-input-lock)と揃えている(pnpm 11、vitest 4、TypeScript 7)。
テストは12ファイル・153件あり、外部ネットワークを使わずに全部通る。

## 2行に何を載せて、何を落とすか

セグメントと値の出どころは次のとおりだ。

| セグメント | 値の出どころ | 取得のタイミング |
| --- | --- | --- |
| モデル、thinking | Piのモデル情報と`ctx.thinkingLevel` | 描画時 |
| コンテキスト | `ctx.getContextUsage()` | 描画時 |
| キャッシュ | 直前の応答のトークン使用量 | 描画時 |
| クォータ | プロバイダごとの使用量API | 開始時、モデル切替時、5分ごと |
| 経過時間 | セッションヘッダの時刻 | 1分ごと |
| Git | `git status --porcelain=v2 --branch` | 開始時、ブランチ変更時、ターン終了時 |
| ctx-mode | `context-mode statusline` | 開始時、ターン終了時 |

描画そのものは通信もプロセス起動もファイル読み込みもしない。
値はイベントをきっかけに裏で更新し、描画は最後のスナップショットを並べるだけだ。

### 分からないときは、分からないと表示する

コンパクションの直後、次の応答が返るまでPiは現在のコンテキストサイズを報告できない。
実際の値が分からないので、ゲージは`ctx ░░░░░░░░░░ ?% · ?/384.0k`と表示する。

キャッシュは、読み取りが0より大きいときだけ`R`を出し、書き込みは1k以上のときだけ`W`を出す。
どちらも無ければセグメントごと出さない。
小さな数字を並べても、判断の材料にはならない。

クォータの窓は、リセット時刻を報告するプロバイダにだけ`↻`付きの時刻を出す。
割合は85%から黄色、92%から赤になる。

### 狭い端末では、優先度を決めて落とす

端末が狭くなっても2行は保ち、落とす順番を決めてある。
一行目はキャッシュ、`think ON`、トークン数、thinking level、ゲージの順に落ちる。
二行目はctx-mode、cwd、経過時間、リセット時刻、クォータ窓の順に落ち、ブランチは最も長く残る。
クォータ窓は後ろのものから消える。

40桁まで狭くなると、次のようにモデルとコンテキスト、クォータとブランチだけになる。

```text
gpt-6-luna · high │ ctx ████░░░░░░ 41%
5h 71% │ 7d 14% │ main * ↑2
```

## 使用量は、自分が使う3プロバイダだけ

フォーク元が持っていた8種類のうち、残したのはopenai-codexとopencode-goだ。
Claude Max、GitHub Copilot、Google Gemini、MiniMax、MiniMax CN、Kimi Codingの6種類は削除した。

残す基準は、自分がPiで使っているかどうかだ。
使わないプロバイダの表示は検証できない。
APIの形が変わっても気づけず、表示が出ないままになる。
フォーク元は、Claude Maxの取得に`claude-code`を名乗る回避策も入れていた。
AnthropicがUser-Agentでレート制限するためだ。
使わないぶんには、抱えなくていい問題だ。

使っている側のCommand Codeは、フォーク元に無いので新しく書いた。
Piではカスタムプロバイダとして`models.json`に設定するため、プロバイダIDは自分で決められる。
モデル名も、複数のプロバイダで共有されうる。
そこで判定にはbaseUrlのホスト(`api.commandcode.ai`)を使う。
認証情報は`cmd` CLIと同じ`~/.commandcode/auth.json`か環境変数から読む。
叩くのはCLIの使用量ビューと同じ読み取り専用のエンドポイント(`/alpha/whoami`と`/alpha/billing/credits`)だ。
月次の使用率はAPIから取得できない。
CLIが内蔵するプラン表で計算している値なので、フッターには出せない。

モデルの切り替えでは、前のプロバイダのクォータを絶対に表示しない。
新しいプロバイダの値がまだ無ければ、取得が終わるまでセグメントを出さない。
同じプロバイダの一時的な失敗のときだけ、前回の値を残す。

## v0.1.0: タグはエージェント、npmへの公開は自分のターミナル

フォークを用意した2026年10月2日のうちに、v0.1.0がnpmに載った。

公開の前に、実際にパッケージされるtarballを展開した。
中身がレビュー済みの19ファイルと一致することを確認した。
タグはエージェントが打ったが、npmへの公開は自分のターミナルで行った。
2要素認証が要る公開は、非対話のエージェントセッションからは実行できない。
npmでは公開が段階的公開(staged publishing)の扱いになった。
`0.0.0-stage`という仮のバージョンが作られ、そのあと0.1.0が公開された。

公開を確認したあと、GitHub Releaseの作成とREADMEのインストール手順の更新はエージェントに任せた。

## v0.1.1: OpenCode Goの窓が消えた

公開から数日、opencode-goのモデルを使うと、クォータの窓が出ないことに気づいた。
期待する表示は`5h 12% ↻ 13:20 │ 7d 45% ↻ 10/09 12:00 │ mo 7% ↻ 11/01 12:00`の並びだ。
実際は経過時間とブランチしか出ていなかった。

調査は読み取り専用のエージェントに任せ、OpenCode側の現行ソースを一次情報として確認させた。
[packages/console/app/src/routes/zen/go/v1/usage.ts](https://github.com/anomalyco/opencode/blob/907b3bc/packages/console/app/src/routes/zen/go/v1/usage.ts)を読むと、応答は次のネストした形に変わっていた。

```json
{
  "usage": {
    "rolling": { "status": "ok", "percent": 12.3, "resetsAt": "2026-10-05T04:20:00.000Z" },
    "weekly": { "status": "ok", "percent": 45.6, "resetsAt": "2026-10-09T03:00:00.000Z" },
    "monthly": { "status": "ok", "percent": 7.8, "resetsAt": "2026-11-01T03:00:00.000Z" }
  }
}
```

フォーク元由来のパーサは、`rollingUsage`の中に`usagePercent`と`resetInSec`がある古い形を期待していた。
該当するフィールドが無いため、クォータを1つも取り出せなかった。

直し方は4つだ。
`usage.rolling`、`usage.weekly`、`usage.monthly`を5h、7d、moの窓へマップする。
`percent`が数値でない窓は無視する。
`resetsAt`が不正でも割合は残し、リセット時刻だけ省略する。
どの窓も取得できなければ「データなし」を返し、前回の表示を消さない。

修正後、実アカウントで5h、7d、moの3窓が表示されることを確認した。
テストはこの修正で153件になった。

同じタイミングで、リリース作業もGitHub Actionsへ移した。
タグをpushすると、チェック、npm publish(Trusted Publishing/OIDC)、レジストリ検証、GitHub Releaseの順に進むワークフローだ。
npmのトークンはリポジトリに置かない。
GitHub Releaseをnpm公開の後に置くのは、先にReleaseだけが残る状態を避けるためだ。
構成はpi-input-lockと揃えている。

2026年10月5日の午前、v0.1.1がGitHub Actionsから公開された。
npmのprovenance(SLSA)が付いている。

## 使い方

インストールはPiの拡張コマンドで行う。

```bash
pi install npm:@j1nn0/pi-footer
```

Pi 1.0以降とNode.js 22.19.0以降が必要で、依存はPiが提供するpeer dependencyだけだ。

設定は環境変数4つで、読み込みは拡張のロード時に行われる。

- `PI_FOOTER_SHOW_CWD`: 作業ディレクトリを表示する(既定は0)
- `PI_FOOTER_SHOW_BRANCH`: Gitブランチと変更マーカーを表示する(既定は1)
- `PI_FOOTER_SHOW_PROVIDER`: `provider/model-id`の形で表示する(既定は0)
- `PI_FOOTER_SHOW_CONTEXT_MODE`: ctx-modeセグメントを表示する(既定は1)

旧名の`PI_MINIMAL_FOOTER_*`もフォールバックとして動く。
Context Modeを使っていない環境では、ctx-modeセグメントは自動で消える。

npmのkeywordsに`pi-package`があるので、[pi.dev](https://pi.dev/packages/@j1nn0/pi-footer)のパッケージ一覧にも自動で載っている。

## 既知の制約

クォータのAPIはどれも非公開で、予告なく変わる。
実際にOpenCode Goで起きた。
応答の形が変わったときは、クォータの表示が消えるだけだ。
エラーは表示されない。

Command Codeの月次使用率は、CLI内蔵のプラン表が必要なため出せない。
ctx-modeセグメントは、Context Modeのセッション保存場所の配置に依存している(1.0.169時点)。
仕様が変われば表示が消える。

資格情報がない、またはリクエストが失敗した場合、そのプロバイダの窓は表示されず、エラーも出ない。
標準フッターを置き換える拡張なので、無効化するには拡張を外す。

2行レイアウトとクォータ取得は、フォーク元のCan Celik氏の実装から始めた。
その実装があったから、自分の情報を載せ替える部分に集中できた。

- [GitHub: j1nn0/pi-footer](https://github.com/j1nn0/pi-footer)
- [npm: @j1nn0/pi-footer](https://www.npmjs.com/package/@j1nn0/pi-footer)
- [Gist: statusline.sh](https://gist.github.com/j1nn0/03bd9a1d054ed32463b0613bbc40fd15)
- [フォーク元: pi-minimal-footer](https://github.com/ogulcancelik/pi-extensions/tree/main/packages/pi-minimal-footer)

クォータの表示が消えたら、プロバイダ側のAPIが変わったと考えてよい。
非公開APIに依存しているので、そうなったら直す前提で使ってほしい。
不具合や気になる点があれば、GitHubのissueで教えてほしい。
