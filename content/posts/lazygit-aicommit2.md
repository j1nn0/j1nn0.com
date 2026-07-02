---
title: "Lazygit × aicommit2 で AI コミットメッセージ生成を組み込む"
slug: lazygit-aicommit2
date: 2026-07-02
tags:
  - lazygit
  - aicommit2
  - git
  - 開発環境
draft: false
---

{{< rawhtml >}}
<div class="callout">
  この記事は AI を活用して執筆しました。<br>
  記事の構成を考える際や、文章を整える際に、AI の提案を参考にしています。
</div>
{{< /rawhtml >}}

## Lazygit を選んだ経緯

VSCode の "Generate Commit Message" に慣れきっていたせいで、エディタを乗り換えたとき、コミットメッセージの自動生成も一緒に消えた。
`fix` や `wip` で逃げる日が増えたが、aicommit2 と Lazygit の customCommands を組み合わせて解決した。
Ctrl+a で候補を 2 件生成し、選んでエディタで確認してコミットするところまで 1 操作で完結する。

移行のきっかけは 2026年5月に起きた VSCode 拡張機能のサプライチェーン攻撃で GitHub が侵害された件だ。
重さは以前から感じていたが、セキュリティの懸念が踏ん切りになった。
いくつかのエディタを試す間は Lazygit で Git 操作を続けていた。

今は Zed に落ち着いたが、Zed の Git パネルは使い勝手がよくないので Lazygit はそのまま使い続けている。
コミットメッセージの生成先を探して見つけたのが aicommit2 だ。

## aicommit2 とは

aicommit2 は diff を読んでコミットメッセージを生成する CLI ツールで、Conventional Commits 形式で出力する。
GPT、Claude、Gemini、Ollama など多数のプロバイダに対応しており、設定ファイルでモデルを切り替えられる。
今回は OpenCode Go のサブスクで使える DeepSeek V4 Flash を使っている。速くて安い。

## インストール

mise でグローバルインストールした。

```sh
mise use -g npm:aicommit2@latest
```

mise を使っていなければ `npm install -g aicommit2` でも入る。

## aicommit2 の設定

`~/.config/aicommit2/config.ini` でモデルと候補数を指定する。
プロバイダごとのセクション名や設定項目は[公式 README](https://github.com/tak-bro/aicommit2) を参照してほしい。

```ini
generate=2

[OPENCODE_GO]
compatible=true
url=https://opencode.ai/zen/go
path=/v1
model[]=deepseek-v4-flash
key=sk-...
```

`generate=2` が候補を 2 件生成させる設定だ。
自分の環境に合わせてプロバイダのセクションだけ差し替えれば動く。

## Lazygit との連携

[公式 README の Lazygit セクション](https://github.com/tak-bro/aicommit2#lazygit)をベースに、`~/.config/lazygit/config.yml` に customCommands を追加する。

```yaml
customCommands:
  - key: <c-a>
    context: "files"
    description: "Generate commit message with aicommit2"
    prompts:
      - type: "menuFromCommand"
        title: "Select commit message"
        key: "Commit"
        command: "aicommit2 --output json"
        filter: '"subject":"(?P<subject>[^"]+)","body":"(?P<body>[^"]*)"'
        valueFormat: "{{ .subject }}<SEP>{{ .body }}"
        labelFormat: "{{ .subject }}"
    output: "terminal"
    command: bash -c 'MSG="{{ .Form.Commit }}" && SUBJ="${MSG%%<SEP>*}" && BODY="${MSG#*<SEP>}" && git commit -e -m "$SUBJ" ${BODY:+-m "$BODY"}'
```

`menuFromCommand` タイプのプロンプトが候補選択の肝で、`aicommit2 --output json` の出力を `filter` の正規表現でパースしてメニューに並べる仕組みだ。
`<SEP>` は subject と body の区切り文字で、末尾の `command` のシェルで `${MSG%%<SEP>*}` と `${MSG#*<SEP>}` に分解している。

`git commit -e` を指定しているので、コミット前にテキストエディタが開く。
AI が生成したメッセージを確認・修正してから保存するとコミットが完了する。

## 実際の動き

ステージングエリアにファイルを追加して Ctrl+a を押す。
aicommit2 が diff を読んでメッセージを 2 件生成し、Lazygit のメニューに候補が並ぶ。

![Lazygitで候補選択メニューが表示されている画面](/images/lazygit-aicommit2/01-candidate-menu.png)

1 件を選ぶとテキストエディタが開き、subject と body が入力済みの状態になっている。

![テキストエディタでコミットメッセージを確認・編集している画面](/images/lazygit-aicommit2/02-editor-edit.png)

保存して閉じればコミット完了だ。
VSCode のボタンと大差ない。むしろエディタが変わっても同じ操作でいいので、逆に使いやすくなった。

## 参考にしたリンク

Zed に移行してからも Lazygit は使い続けているので、コミットメッセージの生成先が変わっただけで普段のワークフローはほとんど変わらなかった。
lazygit の customCommands がここまで柔軟とは思っていなかったので、他にも自動化できる操作がないか試したくなってる。

GPT でも Gemini でも Ollama でも動くので、モデルに縛られなくていいのが地味に助かってる。

他に何が自動化できるか、公式のコンペンディウムを眺めてみると面白い。

- [aicommit2](https://github.com/tak-bro/aicommit2)
- [Lazygit Custom Commands Compendium](https://github.com/jesseduffield/lazygit/wiki/Custom-Commands-Compendium)
