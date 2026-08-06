---
title: "ZedのLaravel拡張を公式版に移行した。拡張IDとLSPのIDが逆にねじれている"
images:
  - /images/zed-laravel-official-extension/ogp.png
cover:
  image: images/zed-laravel-official-extension/ogp.png
slug: zed-laravel-official-extension
date: 2026-08-06
summary: "ZedのLaravel拡張を公式版(laravel/zed-extension)に移行した。拡張IDとLSPのIDが公式・コミュニティ版で逆になっている点と、devcontainer環境でのphpCommand設定をまとめた。"
tags:
  - development_environment
  - devcontainer
  - editor
  - laravel
draft: false
---

Zedに[Laravelの公式拡張](https://github.com/laravel/zed-extension)(`laravel/zed-extension`)が公開された。
今まで使っていた[コミュニティ拡張](https://github.com/mike-bronner/zed-laravel)(`mike-bronner/zed-laravel`)をアンインストールし、公式版に乗り換えた。

拡張を入れ替えるだけの作業だと思っていたが、`settings.json` の `language_servers` を素直に読み替えると事故る落とし穴があった。
拡張のIDと、実際に登録されるLanguage ServerのIDが、公式版とコミュニティ版で逆にねじれている。

## この記事で分かること

- 拡張IDとLanguage Server IDが、公式・コミュニティ版で逆になっている実態と、`settings.json` での書き方
- 公式版とコミュニティ版で、Laravelプロジェクトの情報をどう取得しているかの違い
- Dev Container越しにPHPを実行している環境で、公式LSPの `phpCommand` をどう書いたか

## 拡張IDとLSPのIDが逆になっている

それぞれの `extension.toml` を見ると、名前の対応がこうなっている。

| | 拡張ID | Language Server ID |
| --- | --- | --- |
| Laravel (Official) | `laravel-official` | `laravel` |
| Laravel (Community Edition) | `laravel` | `laravel-lsp` |

公式版の拡張IDは `laravel-official` なのに、そこに登録されるLanguage Server IDは `laravel`。
コミュニティ版の拡張IDは `laravel` なのに、Language Server IDは `laravel-lsp`。

`settings.json` の `languages.PHP.language_servers` に書くのはLanguage Server IDの方なので、公式版だけを使うなら `laravel` と書く。
拡張の名前から連想して `laravel-official` と書くと、存在しないサーバーを指定したことになる。

両方インストールした状態を試す人もいるだろうから、書いておく。
コミュニティ版を無効化するつもりで、その拡張IDと同じ `!laravel` と書いてしまうと、実際に無効化されるのはLanguage Server IDが `laravel` の公式版の方になる。
無効化したいコミュニティ版のLanguage Server IDは `laravel-lsp` なので、`!laravel-lsp` と書く必要がある。

自分は移行にあたってコミュニティ版をアンインストールしたので、今の `settings.json` に `!laravel-lsp` のような除外設定は残っていない。
両方を並行稼働させる予定がある人だけ気にすればいい話ではある。

## 公式版とコミュニティ版、情報の取得方法が違う

拡張を入れ替える前に、この2つが同じことをしているのか気になって、それぞれのソースを見た。

コミュニティ版のREADMEには、静的解析であることがはっきり書かれている。

> Everything is parsed statically with tree-sitter: the extension reads your files, it never runs them.

一方、公式の[Laravel LSP](https://github.com/laravel/lsp)(`laravel/lsp`)は、プロジェクトの情報を取得するときに実際に `artisan tinker` を叩いている。
`app/Lsp/ScriptRunner.php` に、その実装がある。

```php
public function run(string $code): ?string
{
    $command = [
        ...$this->command,
        '-d',
        'error_reporting=E_ALL & ~(' . self::WARNING_ERROR_TYPES . ')',
        'artisan',
        'tinker',
        '--execute',
        $this->code($code),
    ];

    $process = proc_open($command, [
        1 => ['pipe', 'w'],
        2 => ['pipe', 'w'],
    ], $pipes, $this->path);
    // 以降、$pipes から出力を読んで返す処理が続く
}
```

`$this->command` の部分に、設定した `phpCommand` がそのまま展開される。
つまり公式版は、ルート、Config、Viewといった情報を、実際にLaravelアプリを起動して取得している。

`artisan` 経由である以上、Service Providerの `boot()` も普通に呼ばれる。
起動時にメール送信や外部APIアクセスをしているアプリでは、そのぶんの副作用が起きる前提で使うことになる。

コミュニティ版のREADMEは、この違いを「どちらを選ぶか」という比較表にまとめている。
half-applied migrationや `.env` 未設定のブランチでも動く方が欲しいならコミュニティ版、実際に動いているアプリの状態をそのまま知りたいなら公式版、という住み分けだった。
自分の環境はDev Container側でアプリが常に起動できる状態なので、公式版の前提と合っている。

## Dev Container越しの `phpCommand`

自分の開発環境は、PHPとNode.jsをDev Container CLIで起動したコンテナ側に置き、Zed本体はmacOSのホスト側で動かしている。
[以前の記事](/posts/zed-oxfmt-devcontainer/)でoxfmt・oxlintのLSPを `devcontainer exec` 越しに動かしたのと同じ構成だ。

公式のLaravel LSPは、`phpEnvironment` の自動検出でHerd・Valet・Sail・Lando・DDEV・ローカルPHPを順に試す。
どれも自分の環境には該当しないので、`initialization_options.phpCommand` に実行コマンドを配列で明示する。

```jsonc
{
  "lsp": {
    "laravel": {
      "initialization_options": {
        "phpCommand": [
          "/Users/j1nn0/.local/share/mise/installs/npm-devcontainers-cli/latest/bin/devcontainer",
          "exec",
          "--workspace-folder",
          ".",
          "php"
        ]
      }
    }
  }
}
```

`phpCommand` はドキュメント上も文字列の配列で、ここに書いた内容がそのまま `artisan tinker` の手前に展開される。
`devcontainer` は絶対パスで書いた。
以前oxfmt・oxlintのLSPで、`devcontainer` を相対パスのまま渡して起動に失敗した経験があったからだと思うが、正直そこまではっきり覚えていない。
いずれにせよ、今回は最初から絶対パスで書いている。

`--remote-env AI_AGENT=1` は、[AIエージェントからDev Container内のコマンドを実行するときの記事](/posts/ai-agent-devcontainer-exec/)で使っていたフラグだが、LSPの起動はAIエージェントによる実行ではないので、今回の `phpCommand` には付けていない。

## 動作確認

まず `devcontainer exec` 越しに、公式LSPが実行するのと同じ形でLaravelが起動できるか確認した。

```sh
devcontainer exec \
  --workspace-folder . \
  php artisan tinker --execute='echo app()->version();'
```

バージョンが表示されることを確認してから、Zedのコマンドパレットで `editor: restart language server` を実行する。
`initialization_options` はLSP起動時に一度だけ送られるので、設定を変えたら再起動が必要になる。

`route('...')` や `view('...')` の補完、`config('...')` の補完が効くことを確認した。

## 使ってみて

移行したばかりで、まだ使い込んだとは言えない。
`laravel/lsp` のREADMEにある機能表を見ると、対応しているのはCompletions・Hover・Diagnostics・Document links・Code actionsで、コミュニティ版にあったRename、Find References、Code Lensの記載はない。

コミュニティ版のREADMEも、機能表は双方ともリリースのたびに変わりうると自ら釘を刺しているので、今後追加される可能性はある。
それでも少なくとも今は、コミュニティ版だけが持っている機能ということになる。
このあたりで不足を感じるかどうかは、もう少し使ってから判断することになる。

拡張IDとLanguage Server IDのねじれだけは、使う前に知っておいて損はない話だと思う。
