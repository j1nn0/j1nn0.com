# タグ内部値と表示名の分離

## 目的

Hugo記事のfront matterにあるタグ値を、SNSハッシュタグとURL向けの小文字・アンダースコア形式に統一する。

読者向けの正式名称は、タグtermのメタデータで別に管理する。

## 対象範囲

- `content/posts/` の全記事にあるタグ値
- `content/tags/<内部値>/_index.md` のtermメタデータ
- 旧 `ai_agent` URLのCloudflare Pagesリダイレクト
- HugoとPaperModのタグ表示、OGP、X共有リンクの検証

記事本文、タイトル、公開日、slug、ファイル名、PaperMod本体は変更しない。

## データモデル

記事は内部値を保持する。

```yaml
tags:
  - ai_agents
  - cloudflare_pages
```

各termのbranch bundleは表示名を保持する。

```yaml
---
title: AIエージェント
---
```

この構成では、Hugoは記事の内部値から `/tags/ai_agents/` を生成する。

PaperModが使用するterm pageの `LinkTitle` と、既存OGPテンプレートが使用するterm pageの `Title` は、branch bundleの `title` を表示する。

X共有リンクは既存のPaperModテンプレートが `.Params.Tags` を直接 `hashtags` パラメータへ渡すため、表示名ではなく内部値を使用する。

## タグ方針

- 英字の内部値は小文字にする。
- 複数語はアンダースコアで結合する。
- ハイフンとスペースは内部値に使わない。
- `ai_agent` は分野タグの `ai_agents` に統合する。
- 主題でない単発タグは削除する。
- パッケージ自体が記事の主題である `oh_my_opencode_slim` と `vanilla_autokana` は単発でも維持する。

## URL移行

`ai_agent` のterm URLは `ai_agents` に変わる。

`static/_redirects` に `/tags/ai_agent/` から `/tags/ai_agents/` への301を追加する。

削除するタグは、そのtag pageに含まれていた記事へ301リダイレクトする。

広い分類に統合する `ai_agent`、`mac`、`開発環境` は、対応する新しいtag pageへ301リダイレクトする。

## 検証

1. 全記事のタグ値が小文字・アンダースコア規則を満たすことを確認する。
2. `hugo --minify` が成功することを確認する。
3. 22個のタグterm pageが生成され、タグ一覧・記事末尾・OGPに正式な表示名が出ることを確認する。
4. 代表記事のX共有URLで、内部値のハッシュタグだけが重複なく生成されることを確認する。
5. 生成された `/tags/ai_agent/` リダイレクトが301で `/tags/ai_agents/` を指すことを確認する。
6. 差分にタグ、termメタデータ、リダイレクト、関連設定以外の変更がないことを確認する。
