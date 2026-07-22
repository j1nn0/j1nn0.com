---
title: "AIで技術文書をObsidianノートに変換している話"
image: /images/obsidian-pdf-to-note/ogp.png
slug: obsidian-pdf-to-note
date: 2026-07-07
tags:
  - ai
  - obsidian
  - chatgpt
draft: false
---

## この記事で分かること

- PDF を Marker と ChatGPT で Obsidian ノートへ変換する流れ
- RAGを使わずにノートとして読む構成を選んだ理由
- AIレビューを挟んで技術文書を読みやすくする方法

## RAGにしないと決めた

技術文書をAIに食わせてRAG化する、という使い方がある。
「質問すれば答えてくれる」という仕組みは便利そうに聞こえる。
でも自分がやりたいのはそれではなかった。

自分の目的は、文書を「読む」ことだ。
検索して断片を引き出すのではなく、章を追って理解を積み上げていくことだ。
そのためにObsidianでMarkdown化するワークフローを作った。

## PDF → Marker → ChatGPT → Obsidian の流れ

1. PDFをMarkerでMarkdownに変換する
2. ChatGPTに渡して日本語詳細ノートを作る
3. ObsidianのVaultに置いて読む

Webページの場合は最初のMarkerの手順が不要で、そのままChatGPTに渡せる。

### PDFの変換にはMarkerを使う

[Marker](https://github.com/datalab-to/marker)はPythonのCLIツールで、PDFをMarkdownに変換してくれる。
`marker_single`コマンド1つでPDFを処理でき、実行が完了すると出力先のパスが標準出力に表示される。
画像も自動で`assets/`ディレクトリに切り出してくれる。

変換コマンドはこんな感じ。
```sh
marker_single input.pdf
```

変換後のMarkdownには見出し構造が残り、コードブロックも維持される。
AIに渡す前の前処理として、これが一番安定している。

### 逐語翻訳ではなく「実務向け詳細ノート」を作る指示

ChatGPTに渡すとき、逐語翻訳ではなく「実務向け日本語詳細ノート」を作るよう指示している。
毎回ドキュメントの内容に合わせて細かく変えるので、プロンプトをそのまま載せることはしないが、指示に盛り込む要素は概ね決まっている。

- 全章の日本語目次
- 章別の要約
- 用語集と訳語統一表
- 各章の日本語詳細ノート
- 原文コードブロックの維持
- Obsidianリンクマップ

「自分が普段使っている技術スタック向けの補足を加えてほしい」という指示が、自分にとっては一番効く。

### 圏論をC#で読む、言語を変えると概念が届く

形式を整えるだけでは、自分のコンテキストとつながらない。

例えば「プログラマーのための圏論」は元々日本語のWebページだ。
でも例示にHaskellとCが使われていて、普段C#を書いている自分には距離があった。
ChatGPTにC#のコード例を並べて追加してもらうよう指示した。

元のテキストにはこういう例がある。

```haskell
fact n = product [1..n]
```

```c
int fact(int n) {
    int i;
    int result = 1;
    for (i = 2; i <= n; ++i)
        result *= i;
    return result;
}
```

AIに指示した結果、C#の対訳が並んで追記された。

```csharp
// 関数型スタイル
static int Fact(int n) => Enumerable.Range(1, n).Aggregate(1, (acc, x) => acc * x);

// 命令型スタイル
static int Fact(int n)
{
    var result = 1;
    for (var i = 2; i <= n; i++)
        result *= i;
    return result;
}
```

HaskellとCの対比に、C#が加わることで、自分が実際に書く言語で概念を確かめながら読めるようになった。

## AIにレビューさせるサイクルで仕上げる

1回のプロンプトで完成することはほとんどない。

出来上がったものを元の資料と見比べて薄いと感じたら、「読み物として薄すぎる部分はないか」とAI自身にレビューさせる。
どこが足りないかはAIが見つけて改善し、また全体をレビューする。
そのサイクルを何度も回す。

手間はかかるが、改善点を探す目もAIが担ってくれるので、自分は「まだ薄い気がする」という感覚だけ持っていればいい。

OWASP Code Review Guide v2をMarkdown化したときは、レビューの過程でAIが「この節の内容は古く、現在のベストプラクティスと異なる」と指摘してきた。
まだ自分では読んでいない段階だったので、そもそも古いことに気づいていなかった。
AIの指摘を受けて、その箇所を現在の知見でアップデートするよう依頼した。
変換前に品質の問題が見つかるのは、このワークフローならではだ。

手間はかかるが、自分の文脈で読めるノートになる。

## ObsidianのVaultに置いて読む

出来上がったMarkdownはObsidianのVaultに置く。
見出し構造が残っているのでアウトラインで章を俯瞰でき、リンクマップで概念のつながりをグラフ表示できる。

RAGのように「聞けば答えてくれる」状態にはしていない。
自分の手と目で読みたいからだ。
検索で断片を引き出すより、章を順番に読んだほうが、頭に入る。

## 最近Markdown化した資料

- [Agentic Auto-Scheduling: An Experimental Study of LLM-Guided Loop](https://arxiv.org/pdf/2511.00592)
- [Agentic Design Patterns](https://irp.cdn-website.com/ca79032a/files/uploaded/Agentic-Design-Patterns.pdf)
- [OWASP Code Review Guide v2](https://owasp.org/www-project-code-review-guide/assets/OWASP_Code_Review_Guide_v2.pdf)
- [プログラマーのための圏論](https://ktgw0316.github.io/milewski-ctfp-markdown/)

どれも一発で完成したわけではなく、リレーを重ねて今の形になっている。
RAGにしていれば、聞けば答えてくれる状態にはなっていた。
でも圏論をC#で読めるノートは、自分でしか育てられなかった。
