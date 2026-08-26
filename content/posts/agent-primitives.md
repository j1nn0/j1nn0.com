---
title: "設計と指示出しはChatGPT、手を動かすのはエージェント。npmパッケージを6個公開した"
slug: agent-primitives
date: 2026-08-25
summary: "設計判断・プロンプト生成・コードレビューをChatGPTが担い、人間はプロンプトの運搬係に専念した。Claude CodeのOpus 5を指揮官に、piのDeepSeek V4 Flashが調査、GPT-5.6 Lunaが実装を担い、npmパッケージ6個を4日間で公開した記録。"
tags:
  - ai_agents
  - chatgpt
  - pi
images:
  - /images/agent-primitives/ogp.png
cover:
  image: images/agent-primitives/ogp.png
draft: true
---

8月22日の夜、「なんかnpmパッケージを開発したい」とChatGPTに相談したのが始まりだった。
4日後の25日深夜時点で、[j1nn0/agent-primitives](https://github.com/j1nn0/agent-primitives)には69コミットが積まれ、npmには`@j1nn0/`スコープのパッケージが6個並っている。
今も開発は続いている。

この4日間で私が書いたコードは0行だ。
設計の判断もまずChatGPTに預けた。
残った仕事は三つある。
ChatGPTが生成したプロンプトをエージェントへ運ぶこと、GitHubとnpmの画面操作、2FAの確認コードを打つこと。

役割はこう固定した。
設計判断・プロンプト生成・コードレビューがChatGPT。
実装の指揮を取るオーケストレーターがClaude CodeのOpus 5。
調査がpiのDeepSeek V4 Flash、実装がpiのGPT-5.6 Lunaだ。
調査と実装の委譲は、以前の記事で作った[agent-orchestration]({{< ref "agent-orchestration-skill" >}})スキルに丸ごと任せている。

## 作ったもの。compactionで落とす約束を守らせる部品

最初に挙がった案は、OpenAI互換APIの実対応能力を検査するCLI(model-doctor)だった。
相談を重ねるうちに方向が変わり、「特定のフレームワークに依存しない、エージェント能力強化の小さな部品群」に落ち着いた。
リポジトリ名のagent-primitivesもChatGPTの提案だ。

きっかけの問題は、長時間動くエージェントがcontext compactionで大事な約束を落とすことだ。
goalや制約は、圧縮やhandoffの境界で要約に飲み込まれ、意味が薄まる。

第一弾の[@j1nn0/agent-context-guard](https://www.npmjs.com/package/@j1nn0/agent-context-guard)は、この問題に対する判定エンジンだ。
goal、constraint、requirement、decision、factを明示的に登録すると、任意のcontext候補に対して各項目がpreserved、changed、lost、unknownのどれかを返す。

判定できないものを勝手にpreservedへ倒さないのが設計の柱で、verifierの異常はunknownとして見せる。
文字列一致しかしない内蔵verifierはcreateLiteralVerifierと名前を正直に付け、changedのような意味判定は外部のsemantic verifierへ任せた。

ただしcoreをインストールしても、動作中のエージェントは何も守られない。
coreは判定だけをする。
READMEのLayers表のとおりだ。

| Layer | Responsibility |
| --- | --- |
| Core primitive | Decide. 明示的な入力に対して判定をplain dataで返す |
| Harness adapter | 特定ランタイムのlifecycleを監視し、enforce / recoverする |
| MCP adapter | primitiveをcapabilityとして露出する |

適切な瞬間に問うのはadapterの仕事で、pi向けには`@j1nn0/agent-context-guard-pi`を用意した。
session_before_compactでsnapshotを撮り、session_compactの後、次のcontextイベントでeffective contextを検証する。
criticalな喪失だけをcontextへ再注入できるが、このrecoveryはdefault offだ。

同じcore+adapterの型で、作業位置を記録して復元する`@j1nn0/agent-state`、milestoneが本当に増えたかを判定する`@j1nn0/agent-progress`も作った。
25日深夜時点で6パッケージすべてがnpmに公開済みだ。
テストは349件あり、記事執筆時にcloneしてbuild後に再実行して全件passを確認した。

## 開発ループは運搬で回る

構成を図にするとこうなる。

```text
ChatGPT           設計判断 / プロンプト生成 / 実コードレビュー
   ↑ │
   │ ↓             私がプロンプトと報告を運搬
Claude Code        Orchestrator (Opus 5)
   ├─ Explorer     pi DeepSeek V4 Flash : 調査 (read-only)
   └─ Fixer        pi GPT-5.6 Luna      : 実装 (commit + push + CI)
```

1ループの流れはこうだ。
ChatGPTが次フェーズのプロンプトを生成する。
私がそれをClaude Codeのセッションへ貼る。
Orchestratorはagent-orchestrationスキルに従ってExplorerとFixerへ委譲し、commit + push + CI greenまで持っていく。
最終報告を私がChatGPTへ貼る。
ChatGPTは報告で進捗を把握し、レビューはremote mainの実コードに対して行う。
修正点は次のプロンプトへ繰り込まれる。

この会話が4日間で118往復になった。
ChatGPTはウェブ検索で公式ドキュメントやregistryを直接読めるので、プロンプトには調査済みの設計判断が入った状態で届く。
エージェント側へ課すのは「actual stateを優先し、食い違いは報告する」だけだ。

プロンプトの型も定まった。
standalone specificationとして、過去セッションを知らなくても完結する背景、確定済みの設計判断、受入条件、今回固有の禁止事項を書く。
pi adapterのPhase 1では「core packageは原則変更禁止」を置いた。
完了報告は、git diffでcoreへの差分ゼロを証明してきた。

生成されるプロンプトには、こんな節が入る。

```markdown
# Model / provider rule - IMPORTANT

今回以降、live provider/model callで以下のmodelを使う場合は
必ずこのproviderを使用してください。

GPT-5.6 Luna       → openai-codex/gpt-5.6-luna
DeepSeek V4 Flash  → opencode-go/deepseek-v4-flash

使用禁止: command-code/gpt-5.6-luna
model名だけ合っていてもproviderが違えば不可です。
```

## 設計判断は上流に集めた

開始早々に「基本的に設計判断は全てあなたに任せます」とChatGPTへ宣言してから、このスタイルは安定した。
判断の所在が一点に集まるので、プロンプト間で方針がブレない。

ロードマップの判断も上流に置いた。
v0.1のcoreが完成したとき、エージェントは次にAgent Stateというcore primitiveを提案してきた。
ChatGPTはこれを退けて、先にpi adapterを作り実際のcompaction境界でcore APIを検証する順序へ変えた。
理由は「綺麗なprimitiveが増えても、実際に動くAgentにはまだ何も効いていない状態が続く」からだ。

MCPでtoolとして出すだけでは不十分、という切り分けもこの時期に確定した。
compactionの直前と直後を自動観測するには、harness側のlifecycle hookが要る。

## 報告は読む。判定材料はremoteに置く

最初のv0.1完了報告は上出来だった。
テスト27件、publint、Are The Types Wrong、npm pack --dry-runまで確認したと書いてあった。
報告は毎回ちゃんと読む。
進捗の把握も次フェーズの判断も、まず報告から始まる。
それでもChatGPTが最初に指摘したのは、変更が5コミットのままremoteへpushされていないことだった。

ここでループの規律が決まる。
報告は読むが、最終判定の材料は報告文の上に置かない。
push後、ChatGPTはremote mainの実コードを読んでレビューし、以降ずっとそうしてきた。

このスタイルには代償もある。
全部の情報が私の手を経由するので、運搬の往復がレイテンシになり、フェンス抜けのような事故もこの経路で起きた。
対価として得られるのは、判断する者と実装する者が分かれることだ。
最終レビューを実装者と別の存在が実コードに対して行うので、報告の自己評価で終わらない。

## ドキュメントより.d.tsが正だった

Explorerの調査が効いた例が二つある。

一つはpi拡張APIのずれだ。
公式ドキュメントにはsession_compact_failedイベントが載っているが、インストール済みpi 0.84.2の.d.tsには存在しない。
Explorerが2ラウンドの一次調査でこれを確認し、adapterは「存在しないイベントのために型を騙す価値はない」として登録を見送った。
stale snapshotの防止は、beforeで常に上書き、compactで消費、state変更でクリアという3つの構造的不変条件で代わりに守っている。

もう一つはproductionのバグだ。
live smokeでautomatic discoveryがGPT-5.6 Lunaで毎回HTTP 400になった。
原因はpi本体のpi-aiライブラリで、reasoningEffort省略時にthinkingLevelMap.off("none")を送るためだった。

当該タスクのspecはproductionへの変更を禁じていたので、エージェントは修正せず影響範囲を報告した。
次タスクでは「low固定のような対症療法ではなく、Pi 0.84.2の実装契約を調べてprovider-agnosticな最小修正を」という指示になり、pi本体側にfixが入った。

細かい罠もある。
gpt-5.6-lunaという名前が合っていてもproviderが違えば別物で、command-code/gpt-5.6-lunaは400を吐く。
以降のプロンプトにはmodel/provider ruleとして使うproviderを明示し、command-codeを禁止に固定した。

## semantic verifierのモデルは実測で決めた

lost判定のうち「言い換えられても保持されている」を拾うにはLLM呼び出しが要る。
どのモデルをverifierへ向けるかは、実測で決めた。

DeepSeek V4 Flashのdetection F1は0.857で、recallは93.8%まで伸びた。
strict F1が0.343に留まった内訳を見ると、検出15件のうち9件がsuper-span(必要範囲より広く切り取る)で、sub-spanは0件だった。
一方向に偏った問題だ。

GPT-5.6 Lunaはstrict F1が0.051まで落ちる一方、detection F1は0.872でkind accuracyは88.2%だった。
「能力の低いモデルだからspanを外す」のではなく、promptがどこまで切り取るかを規定していない、という診断に両モデルの結果が収束した。

次ラウンドではspan仮説とkind仮説を同時に変えず、A/Bで分離して検証した。
live呼び出しの予算は120のところ119で止め、検証不能なprompt変更をcommitしない規律を守っている。

## フェンス抜け事故とプロンプトの三層分離

運搬係の仕事でも事故は起きた。
プロンプト内部にコードブロックが含まれると、外側のmarkdownフェンス(バッククォート3個)が途中で閉じる。
生成されたプロンプトの下半分が欠けたままエージェントへ渡りそうになったことがある。
以降、外側は~~~markdownで固定するルールになった。

プロンプトの長さも変わった。
初期はforce push禁止やAI trailer禁止まで含めて100項目超あった。
25日に方針を切り替え、共通ルールはリポジトリのAGENTS.mdとskillへ、タスク固有事項だけをプロンプトへ置く三層分離へ移行した。

AGENTS.mdにはSource of truth節を足した。
プロンプトに書かれた期待HEADやテスト数はcontextであってauthorityではない。
actual repository stateが優先され、食い違いは報告される。
ExplorerにDeepSeek V4 Flashを割り当てるような話はskillの責務なので、AGENTS.mdとは二重管理にしない。
二重管理は、将来どこかだけ更新されたときにズレる。

目標はプロンプトを従来の1/3以下へ下げることだ。
重要な指示がチェックリスト消化に埋もれる問題と、「プロンプト側の情報だけが古くなる」リスクを両方減らせる。

公開に向けた作業も全部このループへ乗せた。
GitHub Actionsのrelease pipeline、npm Trusted Publishing(GitHub Actions OIDC、tokenレス)、provenance付与、pnpm 11への移行、SECURITY.md、release guardスクリプト(positive controlに加えてnegative control 15件)だ。

エージェントがどうしても越えられない線が一本残った。
npmの2FAポリシーで、npm publishやnpm trustはワンタイムコードを要求する。
ここだけは私の残務で、ChatGPTは「他のゲートを先に全部済ませてから、コマンドだけお渡しする流れにする」と運用を改めた。

publish直後の404も教訓になった。
registryのread pathはwrite pathより遅れて、publish成功直後の単発npm viewは404を返すことがある。
可視になるまで90〜105秒ほどpollし、versionとshasumをaudit済みartifactと照合してから次のpackageへ進む手順を、bootstrap手順へ書き足した。

## 普段使いのpiに住まわせてdogfoodingする

context-guard-piは普段使いのpi環境へ常駐させている。
開発中は自動captureとrecoveryをOFFにしている。
自分のセッションで、goalが本当に保持されるか、誤検知が出ないか、邪魔にならないかを観察できる。

ただし常駐には副作用のリスクがある。
将来Handoffを作ったとき、本来Handoffが渡すべき情報をContext Guardのrecoveryが偶然補ってしまうと、Handoffの欠陥が隠れる。
そこでintegration validationはclean baselineで行う運用にした。
「入れない」ではなく「実験条件を分離する」だ。

dogfoodingは次の一手も示した。
Progressを使っていて「連続no_progressを数えたい」という欲求が実際に湧き、それはRetry Guardの責務だと整理された。

## 続く

25日深夜時点の姿をまとめる。
npm公開済み6パッケージ(context-guard系は0.1.1、ほかは0.1.0)、テスト349件、CIはNode 22.x / 24.xのマトリクス、リリースはtokenless OIDC経路。
次はRetry Guardで、開発は続いている。

振り返ると、私が判断を入れた場所は分担を選んだ瞬間だけだ。
判断を一点に集め、調査と実装を固定役割へ委譲し、判定材料を実コードに置く。
この三つを守っている限り、運搬係のままでもループは回り続ける。

piへ入れるなら一行で済む。

```bash
pi install npm:@j1nn0/agent-context-guard-pi
```

リポジトリは[j1nn0/agent-primitives](https://github.com/j1nn0/agent-primitives)。
Retry Guardまで積み上がったら、また続編を書く。
