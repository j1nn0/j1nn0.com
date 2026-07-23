---
title: "ターミナル起動を1秒も遅くせず、Homebrewを裏で安全に自動更新する"
images:
  - /images/brew-daily-update/ogp.png
slug: brew-daily-update
date: 2026-07-03
tags:
  - development_environment
  - homebrew
  - macos
draft: false
---

Homebrew の更新をターミナル起動時に同期実行すると、起動が遅くなる。
この構成では更新確認だけを裏で走らせ、更新が必要なときだけ通知から実行する。

## この記事で分かること

- Homebrew の更新確認を1日1回だけ非同期で実行する仕組み
- Caskの更新で `sudo` が必要になったとき、macOSの認証ダイアログを使う設定
- ターミナル起動を待たせない更新確認と、更新が見つかったときの通知

## 同期実行の遅さと自動更新の壊れやすさを避ける

ターミナル起動時に毎回「brew update」を同期実行すると、シェルの起動が遅くて耐えられない。

かといって、バックグラウンドでの完全自動更新を導入すると、開発作業中に予期しないパッケージ更新が走り、環境が突然壊れる。

この問題を解決するため、半自動の更新システムを導入した。
毎日の初回起動時にバックグラウンドで静かに更新確認だけを行い、実際のアップグレードは通知をクリックしたときだけ実行する仕組みだ。
これなら、ターミナルの起動速度を落とさずに、安全かつ適切なタイミングでパッケージを最新に保てる。

## パスワード入力を不要にするmacOSの認証設定

導入にあたって前提となる動作環境と設定を整理しておく。

自分の環境は、Apple Silicon MacとZshの組み合わせだ。
Homebrewのパスは「/opt/homebrew/bin/brew」を前提とする。

XDG Base Directoryの仕様に準拠するため、Zshの構成ディレクトリである「$ZDOTDIR」は「~/.config/zsh」に設定されている。
スクリプトは「$ZDOTDIR/scripts/」配下に保存する。

### 通知ツールのインストール

macOSのデスクトップ通知をコマンドラインから送るために「terminal-notifier」を使う。
事前にインストールしておく。

```sh
brew install terminal-notifier
```

### macOSの認証ダイアログでのsudo認証の有効化

一部のCaskパッケージは、アップグレード時に管理者権限が必要になるため「sudo」が走る。
バックグラウンド処理中でターミナル上にパスワードを入力できない状態でも、安全に認証を通すためにMacの認証ダイアログを利用する。
「/etc/pam.d/sudo_local」を編集してこの設定を有効化しておく。

設定ファイルのテンプレートがある場合はコピーして使う。

```sh
sudo cp /etc/pam.d/sudo_local.template /etc/pam.d/sudo_local
```

「/etc/pam.d/sudo_local」を開き、次の行を追加するかコメントアウトを解除する。

```text
auth       sufficient     pam_tid.so
```

これで「sudo」実行時にターミナルでの入力を求められず、macOSの認証ダイアログがポップアップするようになる。

## 1日1回だけバックグラウンドで実行する更新チェックスクリプト

毎日の初回起動時にパッケージの更新を確認するスクリプトを書く。
「$ZDOTDIR/scripts/brew-update.sh」として保存する。

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

BREW_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/brew"
mkdir -p "$BREW_CACHE_DIR"

BREW_UPDATE_FLAG="$BREW_CACHE_DIR/update_$(date +%Y-%m-%d)"
BREW_LOG="$BREW_CACHE_DIR/update.log"

trap 'notify_error $LINENO "$BASH_COMMAND"' ERR

notify_error() {
    set +e
    {
        echo "Update failed at $(date '+%Y-%m-%d %H:%M:%S %Z')"
        echo "Error at line $1: $2"
    } >>"$BREW_LOG"

    if command -v terminal-notifier >/dev/null 2>&1; then
        terminal-notifier \
            -title "Homebrew" \
            -message "Update failed. Check log." \
            -open "file://$BREW_LOG"
    fi

    exit 1
}

# 古いログ削除
find "$BREW_CACHE_DIR" -type f -name "update_*" -mtime +30 -delete
find "$BREW_CACHE_DIR" -type f -name "*.log" -mtime +30 -delete

if [[ ! -f "$BREW_UPDATE_FLAG" ]]; then
    : >"$BREW_LOG"

    if [[ -x /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo "brew not found" >>"$BREW_LOG"
        exit 1
    fi

    echo "[brew] Running update in background..."

    nohup bash <<EOF >>"$BREW_LOG" 2>&1 &
set -Eeuo pipefail

BREW_LOG="$BREW_LOG"

log() {
  echo "\$@" >>"\$BREW_LOG"
}

notify_error() {
  set +e
  log "Background update failed at \$(date '+%Y-%m-%d %H:%M:%S %Z')"

  if command -v terminal-notifier >/dev/null 2>&1; then
    terminal-notifier \
      -title "Homebrew" \
      -message "Update failed. Check log." \
      -open "file://\$BREW_LOG"
  fi

  exit 1
}

trap notify_error ERR

log "----------------------------------------"
log "Update started at \$(date '+%Y-%m-%d %H:%M:%S %Z')"

brew update >>"\$BREW_LOG" 2>&1

OUTDATED=\$(brew outdated 2>>"\$BREW_LOG" || true)

log "\$OUTDATED"

if [[ -z "\$OUTDATED" ]]; then
  MSG="All formulae are up-to-date 🎉"

  if command -v terminal-notifier >/dev/null 2>&1; then
    terminal-notifier \
      -title "Homebrew Update" \
      -message "\$MSG"
  fi
else
  COUNT=\$(echo "\$OUTDATED" | wc -l | tr -d ' ')
  MSG="Outdated (\$COUNT):"
  MSG+="
\$OUTDATED"

  if command -v terminal-notifier >/dev/null 2>&1; then
    terminal-notifier \
      -title "Homebrew" \
      -message "\$MSG" \
      -execute "zsh -c \$ZDOTDIR/scripts/brew-upgrade.sh"
  fi
fi

log "Update finished at \$(date '+%Y-%m-%d %H:%M:%S %Z')"
EOF

    disown

    touch "$BREW_UPDATE_FLAG"

fi
```

### スクリプトの解説

「update_YYYY-MM-DD」という日付を埋め込んだファイルをフラグに使う。
このファイルが存在しない場合だけ更新チェックを実行する。
これで、1日に2回目以降の起動時はすべての処理がスキップされる。

更新チェックは「nohup」で非同期に実行する。
そのため、ターミナル起動が待たされることはない。
更新がない場合は最新である旨が通知され、更新がある場合はパッケージ一覧とともにボタン付きの通知が届く。

## 通知から呼び出す実際のパッケージ更新スクリプト

通知をクリックしたときに呼び出されるアップグレード用のスクリプトを書く。
「$ZDOTDIR/scripts/brew-upgrade.sh」として保存する。

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

BREW_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/brew"
mkdir -p "$BREW_CACHE_DIR"

# ログファイル
BREW_LOG="$BREW_CACHE_DIR/update.log"

# エラーが発生したらnotify_error関数を呼び出す
trap 'notify_error $LINENO "$BASH_COMMAND"' ERR

notify_error() {
    set +e
    echo "Upgrade failed at $(date '+%Y-%m-%d %H:%M:%S %Z')" >>"$BREW_LOG"
    echo "Error at line $1: $2" >>"$BREW_LOG"

    if command -v terminal-notifier >/dev/null 2>&1; then
        terminal-notifier \
            -title "Homebrew" \
            -message "Upgrade failed. Check log." \
            -open "file://$BREW_LOG"
    fi

    exit 1
}

# brew upgrade 実行 & ログ保存
if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "brew not found at /opt/homebrew/bin/brew" >>"$BREW_LOG"
    exit 1
fi

export HOMEBREW_CASK_OPTS="--appdir=~/Applications --fontdir=/Library/Fonts"

{
    echo "----------------------------------------"
    echo "Upgrade started at $(date '+%Y-%m-%d %H:%M:%S %Z')"
    brew upgrade -y
    echo "Upgrade finished at $(date '+%Y-%m-%d %H:%M:%S %Z')"
} >>"$BREW_LOG" 2>&1

# 完了通知（ログファイルを表示）
if command -v terminal-notifier >/dev/null 2>&1; then
    terminal-notifier \
        -title "Homebrew" \
        -message "Upgrade finished." \
        -open "file://$BREW_LOG"
fi
```

### パーミッションの付与

作成した2つのスクリプトに実行権限を付与する。
保存場所に合わせてパスは調整してほしい。

```sh
chmod +x $ZDOTDIR/scripts/brew-update.sh
chmod +x $ZDOTDIR/scripts/brew-upgrade.sh
```

## ターミナル起動時にフックを仕込む

ターミナル起動時に自動で更新チェックスクリプトを読み込むようにする。
Zshの設定ファイルである「.zshrc」（XDG仕様に準拠している場合は「$ZDOTDIR/.zshrc」）の末尾に次の設定を追加する。

```zsh
if [[ -f $ZDOTDIR/scripts/brew-update.sh ]]; then
    source $ZDOTDIR/scripts/brew-update.sh
fi
```

## 起動時の非同期処理とログの監視方法

設定が終わったら動作を確認してみる。

### 初回起動のシミュレート

同じ日付のフラグファイルがあると動作しないため、検証時は事前に削除しておく。

```sh
rm -f ~/.cache/brew/update_*
```

削除した状態で新しいターミナルを開く。
「[brew] Running update in background...」と表示され、プロンプトが即座に返ってくれば成功だ。

### ログファイルの監視

バックグラウンド処理の進捗はログを監視するとわかりやすい。

```sh
tail -f ~/.cache/brew/update.log
```

数秒から数十秒ほどで処理が完了し、完了通知か更新対象通知が届く。
更新対象通知をクリックすると実際のアップグレードが始まる。
認証ダイアログが出たら認証を行う。
アップグレードが終わると再度完了通知が届く。

実際にこの運用を始めてから、朝のターミナル起動時のもっさり感がなくなり、快適になった。
アップグレードの実行タイミングを自分でコントロールできるのも精神衛生上よい。
