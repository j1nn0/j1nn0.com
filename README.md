# j1nn0.com

個人サイト [j1nn0.com](https://j1nn0.com/) のソースコードです。
静的サイトジェネレーターに [Hugo](https://gohugo.io/) を使用し、テーマには [PaperMod](https://github.com/adityatelange/hugo-PaperMod) を採用しています。
サイトの言語設定は日本語で、Cloudflare Pages へのデプロイを前提にしています。

## 技術構成

- Hugo Extended
- PaperMod theme
- Cloudflare Pages

主な設定は `hugo.yaml` に集約しています。サイト URL、テーマ、言語、OGP/Twitter Card などのメタデータを変更する場合は、まずこのファイルを確認してください。

## ディレクトリ構成

```text
.
├── hugo.yaml                 # Hugo のサイト設定
├── content/                  # 固定ページと投稿
│   ├── archives.md
│   ├── search.md
│   └── posts/
├── assets/css/extended/      # PaperMod に対する CSS 拡張
├── layouts/partials/         # head/footer などのテンプレート拡張
├── static/                   # そのまま公開される静的ファイル
│   └── images/
└── themes/PaperMod/          # PaperMod テーマ
```

## ローカル開発

Hugo をインストールしてから作業します。

```sh
brew install hugo
```

開発サーバーを起動します。

```sh
hugo server -D
```

本番相当のビルドを確認します。

```sh
hugo --minify
```

生成物は `public/` に出力されます。`public/` はビルド成果物なので、通常は直接編集しません。

## コンテンツ追加

投稿は `content/posts/` に Markdown で追加します。

```sh
hugo new content/posts/my-post.md
```

ファイル名は URL になることを意識して、英小文字とハイフンを使うのを基本にします。画像や OGP 用ファイルは `static/images/` に配置します。

## スタイルとテンプレート

PaperMod 本体を直接編集するのではなく、まず拡張用のファイルを使います。

- CSS の調整: `assets/css/extended/custom.css`
- `<head>` の拡張: `layouts/partials/extend_head.html`
- フッター周辺の拡張: `layouts/partials/extend_footer.html`

テーマ側のファイルを変更すると、テーマ更新時に差分管理が難しくなるため注意してください。

## デプロイ

Cloudflare Pages での公開を想定しています。基本設定は次の通りです。

- Build command: `hugo --minify`
- Build output directory: `public`
- Root directory: `/`
- Hugo version: Cloudflare Pages の環境変数 `HUGO_VERSION` で固定することを推奨

HTTP ヘッダーなどの静的設定は `static/_headers` に置きます。

### Google Analytics

Google Analytics 4 の測定 ID は Git にコミットせず、Cloudflare Pages の環境変数で管理します。

Cloudflare Pages の Production 環境に次の変数を設定します。

```text
HUGO_SERVICES_GOOGLEANALYTICS_ID=G-XXXXXXXXXX
```

Hugo は `HUGO_` で始まる環境変数を設定値として読み込みます。
PaperMod は Hugo 標準の Google Analytics partial を呼び出しているため、テンプレートへ `gtag` スクリプトを直接追加する必要はありません。

ローカルで生成 HTML を確認するときは、一時的に環境変数を付けて production build を実行します。

```sh
HUGO_SERVICES_GOOGLEANALYTICS_ID=G-XXXXXXXXXX hugo --environment production --destination /tmp/j1nn0-ga-check
```

測定 ID は公開 HTML には出力されます。
ただし、リポジトリと Git 履歴には残さない方針です。

## テーマのアップデート

PaperMod は `themes/PaperMod` に配置されています。更新時はテーマディレクトリで upstream を取得し、ルートに戻って差分をコミットします。

```sh
cd themes/PaperMod
git fetch origin
git checkout master
git pull origin master
cd ../..
git add themes/PaperMod
git commit -m "Update PaperMod theme to latest version"
```

更新後は `hugo --minify` を実行し、レイアウト、OGP、検索ページ、アーカイブページに崩れがないか確認してください。
