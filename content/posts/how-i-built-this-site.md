---
title: "Hugo + PaperMod + Cloudflare Pages で個人サイトを作りました"
slug: how-i-built-this-site
date: 2026-06-26
tags:
  - hugo
  - papermod
  - cloudflare-pages
draft: false
---

## はじめに

サイトを作りました。正確には作り直した。

前も個人サイトは持ってたんだけど、放置してたので今回ちゃんと作り直すことにした。せっかくだから構成も記録に残しておく。

## 技術選定

■ Hugo
以前も使ったことがあったから。新しい言語やフレームワークを覚えるより、知ってるやつでサクッとやろうと。

Astro もちょっと気になってた。けど、調べるのが面倒になってやめた。ビルドは確かに速いし、不満はない。

■ PaperMod
Hugo のテーマはいくつかあるけど、PaperMod で良かった。ミニマルで読みやすく、ダークモード、検索、アーカイブとブログに欲しい機能が最初から揃ってる。設定で要素の ON/OFF もできる。

テーマをそのまま使うより、必要に応じて CSS やテンプレートを拡張する使い方を想定。あとで書くけど、フォントの調整と OGP 設定くらいしかカスタムしてない。

■ Cloudflare Pages
無料枠がでかい（帯域無制限、ビルド500回/月）。以前は GitHub Pages を使ってたんだけど、Cloudflare Pages は評判も良さそうだし、シンプルに使ってみたかった。

Hugo との相性もいいし、ドキュメントも揃ってる。今のところ不満はない。

## セットアップ

手順はほぼ公式のまま。

```sh
brew install hugo
hugo new site j1nn0.com
cd j1nn0.com
git init
git submodule add https://github.com/adityatelange/hugo-PaperMod themes/PaperMod
```

テーマの有効化は `hugo.yaml` に1行。

```yaml
theme: ["PaperMod"]
```

ここでは特にハマらなかった。

基本設定もこんな感じ。日本語サイトなので `hasCJKLanguage: true` を忘れずに。これを設定しないと、日本語の記事で文字数カウントや自動要約が正しく動かない。

```yaml
baseURL: https://j1nn0.com/
title: j1nn0
theme: ["PaperMod"]

defaultContentLanguage: ja
hasCJKLanguage: true

params:
  description: "Japanese programmer / Vue, PHP, C#, AWS"
  defaultTheme: auto
  author: j1nn0
```

目次やパンくずリストといった表示オプションも hugo.yaml で設定してる。この記事の投稿に合わせて ON にした。

## デプロイ

Cloudflare Pages の連携は3分で終わる。

1. Cloudflare Dashboard → Pages で GitHub リポジトリと連携
2. ビルド設定を入れる

| 項目 | 設定値 |
|---|---|
| Build command | `hugo --minify` |
| Build output directory | `public` |
ここで、環境変数（Environment variables）の `HUGO_VERSION` にローカルの Hugo バージョン（例：`0.163.3`）を指定しておく。Cloudflare のデフォルトバージョンは古いため、指定しないと PaperMod のビルドが通らない。

あとは GitHub に push すれば自動でデプロイ。初回ビルドが通ったら公開完了。

### HTTP ヘッダー

`static/_headers` でセキュリティヘッダーを設定してる。CSP も一緒に入れた。Google Fonts と PaperMod のスクリプトが動くように絞った。

```text
/*
  X-XSS-Protection: 1; mode=block
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'

https://:project.pages.dev/*
  X-Robots-Tag: noindex

https://*.:project.pages.dev/*
  X-Robots-Tag: noindex
```

Cloudflare Pages のプレビュー環境（`*.pages.dev`）は検索エンジンにインデックスさせないようにしている。

## サイトカスタマイズ

### フォント

PaperMod のデフォルトフォントは欧文基準。日本語で読むとちょっとアレだったので、Noto Sans JP をあててる。

```css
body {
  font-family:
    "Noto Sans JP",
    "Hiragino Kaku Gothic ProN",
    "Hiragino Sans",
    Meiryo,
    sans-serif;
  font-size: 16px;
  line-height: 1.6;
}
```

Google Fonts の読み込みは `layouts/partials/extend_head.html` に link タグを追加。

### OGP / Twitter Card

SNS でシェアされたときにテキストだけだと寂しいので、最低限の OGP 設定を入れた。

```html
<meta property="og:image" content="{{ with .Params.image }}{{ . }}{{ else }}{{ site.Params.defaultImage }}{{ end }}">
<meta name="twitter:creator" content="@{{ .Site.Params.twitter }}">
<meta name="twitter:image" content="{{ with .Params.image }}{{ . }}{{ else }}{{ site.Params.defaultImage }}{{ end }}">
```

デフォルトの OGP 画像は `static/images/ogp-default.png`。記事ごとに変える仕組みはまだ用意してない（そのうちやる）。

### CSS のカスタム

PaperMod 本体は触らず、`assets/css/extended/custom.css` にカスタムスタイルを書いてる。日本語フォントの指定、見出しのサイズ調整、コードブロックとモバイル表示の微調整をしてる。

テーマ本体を触らない運用にしてるので、PaperMod のアップデートは submodule の pull だけで済む。

## おわりに

そんなわけで、個人サイトができた。

まだ投稿はこの1記事だけ。少しずつ増やしていくつもり。Hugo + PaperMod + Cloudflare Pages の組み合わせは、運用コストの低さが魅力。少なくとも私は「ブログ放置しちゃった……」を繰り返さないための布石として選んだ。

個人サイトを作りたい人の参考になれば嬉しい。
