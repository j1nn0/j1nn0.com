# 記事冒頭の「この記事で分かること」設計

## 目的

記事を開いた時点で扱う範囲を把握できるようにする。
とくに複数の道具や設定を横断する記事で、タイトルだけでは伝わらない範囲を補う。

## 対象

`content/posts/` の Markdown 記事8本を対象にする。

## 配置と形式

各記事の front matter の直後、最初の H2 見出しの前に `## この記事で分かること` を置く。
その直下に、本文で実際に扱う事項を3点以内の箇条書きで書く。
項目は抽象的な効果ではなく、読者が記事内で得られる判断、構成、手順を具体名で示す。

本文が4,000文字を超える記事では、このセクションの前に2〜3行の概要を追加する。
概要は既存の導入を置き換えず、記事の対象範囲を一文ずつ補足する。

## 記事ごとの要点

| 記事 | 読者に示す範囲 |
| --- | --- |
| `ai-agent-devcontainer-exec.md` | Dev Container とホスト側AIエージェントの接続方法、実行経路、運用上の利点 |
| `brew-daily-update.md` | Homebrew更新の非同期実行、失敗時の安全性、zshでの設定 |
| `dev-environment-2026.md` | USB-Cドック、エディタ、ターミナル、フォントとテーマ、miseとHomebrewの役割分担 |
| `how-i-built-this-site.md` | Hugo、PaperMod、Cloudflare Pagesによるサイト構成と公開方法 |
| `lazygit-aicommit2.md` | Lazygitの選定理由、aicommit2連携、コミットメッセージ生成の流れ |
| `obsidian-pdf-to-note.md` | PDFからObsidianノートにする処理、RAGを選ばなかった理由、使い方 |
| `oh-my-opencode-slim-review.md` | AIサブスクの役割分担、レート制限への対処、oh-my-opencode-slimの設定 |
| `vanilla-autokana-npm.md` | vanilla-autokanaのフォーク理由、半角カナ対応、IME追跡の実装 |

## 検証

各記事に見出しが1つだけ追加されていることを確認する。
`hugo --minify` と `git diff --check` を実行する。

## 自己レビュー

対象、配置、長文の判定基準、記事ごとの記述内容、検証手順を明記した。
未決定事項やプレースホルダーは残していない。
