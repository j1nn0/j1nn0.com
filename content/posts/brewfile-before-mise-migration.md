---
title: "miseのbrew backendを試す前に、Brewfileを先に作る"
slug: brewfile-before-mise-migration
date: 2026-07-10
tags:
  - mac
  - homebrew
  - mise
  - dotfiles
  - terminal
draft: true
---

miseにHomebrewとdotfilesを集約できないか、ここ数日ずっと考えている。
言語ランタイムはmise、macOSのアプリとCLIツールはHomebrewという二重管理が、単純に面倒になってきたからだ。

調べてみると、miseにはHomebrew formulaとcaskを直接扱う`brew:`と`brew-cask:`がある。
既存のHomebrewと共存できるので、移行か現状維持かの二択ではなかった。

ただし、いきなり管理元を切り替えるのはやめた。
先にBrewfileで現在の状態を固定し、formulaだけをmiseへ取り込んで差分を見るほうが安全だった。

## miseのbrew backendはHomebrewのprefixを共有する

miseはNode.jsやPythonのように、プロジェクトごとに異なるバージョンを使いたいツールの管理に向いている。
`.tool-versions`との互換性があったので、自分もanyenvとasdfから移行してきた。

miseのbrew backendは、formulaをHomebrewの標準prefixへ入れる。
Apple SiliconのmacOSでは`/opt/homebrew`である。

miseが入れたformulaは、通常の`brew list`、`brew upgrade`、`brew uninstall`からも見える。
逆に、Homebrewが入れたformulaをmiseの状態確認は認識する。

同じprefixを使うからといって、miseがHomebrewのファイルを勝手に上書きするわけではない。
リンク先が衝突したときは失敗し、衝突しているファイルを表示する。

この共存は、段階的に試せる点がよい。
一方で、どちらがどのformulaを宣言しているかを曖昧にすると、管理元を見失う。

## BrewfileはMacに入れたものの宣言になる

Homebrew Bundleは、`Brewfile`に書かれたformula、cask、tapなどをまとめて復元する仕組みである。
`brew bundle dump`を使うと、すでに入っている対象をBrewfileへ書き出せる。

dotfilesリポジトリにBrewfileを置くなら、最初の一回は次のコマンドでよい。

```zsh
brew bundle dump --file="$HOME/dotfiles/Brewfile" --force
```

`$HOME/dotfiles`は自分のdotfilesリポジトリの場所に置き換える。
この時点では何も削除されない。
インストール済みのHomebrewパッケージを宣言ファイルへ写すだけだ。

生成後のBrewfileは、使っていないツールを見つける一覧にもなる。
自分の場合は、GUIアプリ、普段使うCLIツール、試しに入れたまま忘れていたformulaが同じ場所に並んだ。
Homebrewの状態を「何となく入っているもの」から、見直せるテキストへ変えられる。

## formulaだけをmise.tomlへ取り込んで比較する

次に、既存のHomebrew formulaをmiseの設定へ取り込む。

```zsh
mise bootstrap packages import --manager brew
```

このコマンドは、Homebrew prefixの`opt`リンクを読み、利用者が明示的に入れたformulaを`[bootstrap.packages]`へ書き出す。
依存として入ったformulaまで取り込みたいなら、`--all`を付ける。

設定は次の形になる。

```toml
[bootstrap.packages]
"brew:ffmpeg" = "latest"
"brew:postgresql@17" = "latest"
```

ここでBrewfileを消さない。
miseのimportとpruneは、現時点ではformulaだけが対象である。
macOSアプリを含むcaskはBrewfileに残るため、BrewfileはMac全体の棚卸しとして引き続き使える。

まず取り込んだ`mise.toml`の差分を読む。
そのformulaをmiseから更新したいのか、従来どおりHomebrewに任せたいのかを一つずつ決める。

## Brewfileの差分だけを確認する小さな関数

パッケージを入れるたびにBrewfileを手で直すと、そのうち忘れる。
自分は書き出しと差分確認を一つの関数にして、`.zshrc`へ置くことにした。

設定はこんな感じ。

```zsh
brewfile-dump() {
  local dotfiles_dir="$HOME/dotfiles"
  local brewfile="$dotfiles_dir/Brewfile"

  brew bundle dump --file="$brewfile" --force
  git -C "$dotfiles_dir" diff -- Brewfile
}
```

`brewfile-dump`を実行すると、現在のインストール状態でBrewfileを更新し、その差分を表示する。
差分を見てからコミットするので、一時的な検証用ツールまでdotfilesへ残すかを判断できる。

実行前に`dotfiles_dir`がGitリポジトリであることだけ確認してほしい。
リポジトリ外にBrewfileを置くなら、最後の`git`の行は削除すればよい。

## HOMEBREW_CASK_OPTSを使っているcaskは移さない

自分のHomebrewでは、caskの配置を次のように変えている。

```zsh
export HOMEBREW_CASK_OPTS="--appdir=~/Applications --fontdir=/Library/Fonts"
```

GUIアプリはユーザーの`~/Applications`へ置き、フォントは`/Library/Fonts`へ置きたいからだ。
この配置はMacを使い続けるうえで小さくない。

miseの`brew-cask:`は、Homebrewの`brew`コマンドを呼び出さない。
Cask APIからメタデータを取り、mise自身がダウンロードと展開を行う。

そのため、`HOMEBREW_CASK_OPTS`はmiseには渡らない。
対応するapp caskは`/Applications`へ入るので、`--appdir=~/Applications`は効かない。

さらに、miseが対応しているcask artifactはapp bundle、binary、単純なpkg installerに限られる。
font artifactはこの範囲に入らないため、`--fontdir=/Library/Fonts`を引き継ぐ方法もない。

ここは移行の境界として明快だった。
formulaはmiseへ取り込んで共存を試し、caskはHomebrewとBrewfileで管理し続ける。

## 復元と削除は別の作業として扱う

新しいMacでBrewfileの内容を入れるコマンドは次になる。

```zsh
brew bundle --file="$HOME/dotfiles/Brewfile"
```

Homebrew Bundleは、Brewfileにあるものが足りなければインストールし、既存の対象は通常アップグレードする。
新しいマシンを組むときには便利だが、作業中のMacで気軽に叩くコマンドではない。

もっと危ないのは`brew bundle cleanup --force`である。
これはBrewfileに書かれていない管理対象を削除する。
「Brewfileを正とする」運用には必要になることもあるが、棚卸しが終わるまでは使わないほうがよい。

mise側にも、設定にないformulaを削除する`mise bootstrap packages prune --manager brew`がある。
これはHomebrewが入れたformulaも削除対象にする。
試すなら必ず`--dry-run`を付け、削除予定が意図どおりかを確認してからにする。

まずは書き出す。
次に差分を読む。
復元と削除は、Brewfileと`mise.toml`の内容に納得してからにする。

## 集約するかどうかは、Brewfileとmise.tomlが落ち着いてから決める

Homebrewをmiseへ集約する案は、まだ捨てていない。
dotfilesを含めて一つの入口から開発環境を作れるなら、管理する場所が減る利点はある。

ただし、miseのbrew backendには制約もある。
`brew services`は未対応で、caskはapp bundle、binary、単純なpkg installerなどに対応範囲が限られる。

そのため、サービスや対応していないcaskまで一度に移行する理由はない。
まずformulaを取り込んで共存させ、不満がない範囲だけmiseの設定を正にすればよい。

今はmiseに言語ランタイムと一部のformulaを任せ、Homebrewにはcaskとサービスを任せる形を試している。
二つが同じprefixで共存できるとわかるだけで、移行の心理的な重さはかなり減った。

Homebrew Bundleの詳しい書式と挙動は、[公式ドキュメント](https://docs.brew.sh/Brew-Bundle-and-Brewfile)を参照してほしい。
miseのHomebrew対応の仕様と制約は、[公式ドキュメント](https://mise.jdx.dev/bootstrap/packages/brew.html)にまとまっている。
