---
title: "LaravelのS3をクライアント側暗号化するドライバを作った。設計判断を書く"
slug: laravel-encrypted-s3
date: 2026-08-20
summary: "AWS S3 のクライアント側暗号化(CSE V3)を Laravel のファイルシステムドライバとして提供する laravel-encrypted-s3 を作った。SSE との違いと、暗号化を確実に守るための設計判断を書く。"
tags:
  - laravel
  - aws
  - php
  - ai_agents
images:
  - /images/laravel-encrypted-s3/ogp.png
cover:
  image: images/laravel-encrypted-s3/ogp.png
draft: false
---

S3 に置くファイルが、平文のまま保存されている。このままでは、S3 のデータを読める人には、ファイルの中身も読まれてしまう。

AWS のサーバー側暗号化(SSE-S3 / SSE-KMS)は、S3 の内部で暗号化する。S3 に届いたデータを AWS の管理する鍵で暗号化するが、復号も同じ鍵でできる。クライアント側暗号化(CSE)は違う。アプリケーションの側で暗号化してから S3 に送り、読むときはアプリケーション側で復号する。S3 には暗号文しか置かれない。

この CSE を Laravel のファイルシステムドライバとして提供するパッケージ、[`laravel-encrypted-s3`](https://github.com/j1nn0/laravel-encrypted-s3) を作った。暗号化の実装は AWS SDK for PHP の `S3EncryptionClientV3` と `KmsMaterialsProviderV3` に任せ、このパッケージが受け持つのは、暗号化を確実に守るための設計判断だ。この記事では、その設計判断を書く。

## CSE V3 が何をするか

CSE の書き込みは、ざっくり次の流れになる。

1. KMS に `GenerateDataKey` を呼び、データ暗号化キー(DEK)と、KMS が暗号化した DEK の2つを受け取る
2. DEK で AES-256-GCM により本文を暗号化する
3. 暗号化した DEK と暗号化パラメータ(「エンベロープ」)を、オブジェクトのメタデータとして S3 に保存する
4. 読み込み時はエンベロープを取り出し、`kms:Decrypt` で DEK を復号してから本文を復号する

読み込みはこれの逆順だ。

この「エンベロープをどこに置くか」に2つの方式がある。オブジェクトメタデータに置く `HeadersMetadataStrategy` と、別ファイル(instruction file)に置く方式だ。メタデータ方式に固定している。後述するが、この固定は脆弱性の回避と直結している。

## CSE V3 の安全設定を外せなくする

CSE V3 には、書き込み時のコミットメントポリシーとセキュリティプロファイルという安全設定がある。V3 の暗号文には「鍵コミットメント」(この暗号文がどの鍵で暗号化されたかを、後から確かめられる仕組み)が含まれる。このパッケージが受け付けるのは、安全な側の設定だけだ。

- `commitment_policy` は `REQUIRE_ENCRYPT_REQUIRE_DECRYPT` が既定。鍵コミットメントなしで書き込む `FORBID_ENCRYPT_ALLOW_DECRYPT` は、設定しようとすると例外で拒否する
- `security_profile` は `V3` のみ。V1/V2 形式の読み書きを許す `V3_AND_LEGACY` は拒否する

拒否の理由は、どちらも鍵コミットメントのない古い形式が、AWS SDK の脆弱性 GHSA-x8cp-jf6f-r4xh(CVE-2025-14761、Invisible Salamanders)の攻撃面を広げるためだ。この脆弱性は、暗号文を差し替える(EDK replacement)ことで、攻撃者が選んだ鍵で暗号化された平文を復号させてしまうというもの。`V3_AND_LEGACY` を設定すると AWS SDK が警告を出すが、Laravel ではその警告が `ErrorException` になる。だから設定段階で拒否する。

設定ミスを実行時ではなく「ディスク構築時に失敗させる」方針も、ここから来ている。`encryption` と `kms` ブロックの想定外のキー、対応していない put オプションは、最初の読み書きではなく `Storage::disk('encrypted-s3')` を呼んだ時点で例外にする。セキュリティに関わる設定のタイポは、静かにデフォルトへ落ちるより、大きな音を立てて止まるべきだ。

## デフォルトで ACL を送らない

最初の設計では、ディスクの visibility からデフォルトの ACL を put オプションに注入していた。これをやめた。

2023年4月以降に作成された S3 バケットは Object Ownership が `Bucket owner enforced` になり、ACL が無効化されている。ACL 無効バケットに `x-amz-acl: private` を付けて PutObject すると HTTP 400 `AccessControlListNotSupported` で失敗する。ACL を省略すれば成功する。そして ACL を省略してもアクセスは広がらない。S3 オブジェクトは既定でプライベートで、canned `private` ACL が追加で許可することは何もない。

ここで面白いのは、素の Laravel + Flysystem はこの問題を抱えていることだ。`AwsS3V3Adapter::upload()` は常に `determineAcl()` で ACL を解決し、そのデフォルトは `Visibility::PRIVATE` なので、素の `s3` ディスクも ACL 無効バケットでは失敗する。暗号化パスだけ、デフォルトの ACL 送信をやめた。

## ディレクトリとコピーは暗号化をすり抜けない

暗号化パッケージの落とし穴は、本文の書き込みだけ暗号化して、周辺操作が平文のまま残ることだ。`createDirectory()`、`copy()`、`move()` も暗号化の経路に通した。

### ディレクトリマーカー

Flysystem の `createDirectory()` は、キーの末尾に `/` を付けたゼロバイトオブジェクトを置く。この背後で動く `PortableVisibilityConverter` はディレクトリの既定 visibility が `public` で、ACL 有効バケットでは `x-amz-acl: public-read` の「誰でも読めるディレクトリマーカー」が、暗号化パッケージの操作で静かに作られていた。実際のリクエストトレースで確認した。

対策は、ディレクトリマーカーも暗号化された put パスに通すことだ。`makeDirectory()` は暗号化済みの trailing-slash マーカーを書く。コストはマーカー1回につき KMS `GenerateDataKey` が1回。ディレクトリ作成は低頻度で、S3 はディレクトリマーカーを必須としないので、これは受け入れられる。

### copy は平文オブジェクトをコピーしない

`copy()` は S3 サーバーサイドコピーを使う。暗号文とエンベロープをそのままコピーするので、再暗号化は起きない。ここに穴があった。

コピー前に、コピー元が CSE V3 オブジェクトであることを検証していなかった。別経路でバケットに置かれた平文オブジェクトをコピーすると、暗号化ディスクの上に平文のコピー先が作られてしまう。これも実リクエストトレースで確認した。README の「コピーは暗号化エンベロープを保持する」という記載と矛盾する。

対策は、コピーの前に `HeadObject` を発行して、メタデータが CSE V3 エンベロープの全フィールドを含み、V2 フィールドを一切含まないことを確認することだ。V2 を除外するのは、V3 の読み取りパスが V2 フィールドのあるオブジェクトを拒否するからだ。読み取りできないコピー先を作ってはいけない。

平文、V1、V2、V2/V3 混在、エンベロープ不完全のソースは、コピー先を作る前に拒否される。`move()` はコピーが成功したあとだけソースを削除する。

さらに `MetadataDirective` は `COPY` に固定し、`REPLACE` は拒否する。`REPLACE` はソースのメタデータを置き換えてしまい、CSE V3 エンベロープを消して、読めないコピー先を作るからだ。

### コピーはデフォルトで ACL を送らない

コピーは `S3Client::copy()` を直接呼び、ACL 引数が指定されなければ `null` を渡す。`aws/aws-sdk-php` の REST シリアライザは、値が null のヘッダーを省略する。この省略の挙動が最初に現れたのが 3.382.2 で、パッケージの最低バージョンはそこに固定されている。3.368 は脆弱性の修正が入った最低ラインだが、コピーで ACL ヘッダーを省略する挙動はまだない。

## URL を無効化する

`url()`、`temporaryUrl()`、`temporaryUploadUrl()` は常に `UnsupportedOperationException` を投げる。

署名付き GET URL は、クライアント側復号を通さずに暗号文を配信してしまう。署名付き PUT URL は、CSE を通さずに平文が S3 に到達する経路を作る。どちらも暗号化をすり抜けるので、使えなくするしかない。`providesTemporaryUrls()` は `false` を返す。

## エラーメッセージから平文を締め出す

暗号化パッケージの失敗は、平文や鍵の情報をメッセージに含むことがある。SDK の例外メッセージには、平文、認証情報、KMS の鍵、エンベロープの中身が入る。

構築するエラーメッセージは、例外クラスの短い名前と AWS エラーコードだけに絞る。`SafeFailureReason` が例外チェーンを辿り、`AwsException` のエラーコードだけを取り出す。平文はスタックトレースの引数に残ることがある。そこはパッケージの外側なので、README に `zend.exception_ignore_args=On` と書いてある。

## Content-Length は暗号文サイズから測らない

Laravel の `FilesystemAdapter::response()` は `Content-Length` ヘッダーに `size()` を使う。`size()` は S3 メタデータの暗号文サイズを返すので、そのままでは復号後の平文と長さが食い違う。

`response()` をオーバーライドし、復号ストリームを開いてから `fstat()` で長さを測り、同じハンドルをストリーミングする。`download()` と `serve()` はどちらも `response()` を呼ぶので、この修正がそのまま効く。

「暗号文サイズから16バイト引けば平文サイズ」という算術は採用しなかった。現在の方式では16バイトの GCM タグが付くが、この計算は攻撃者に改ざんされたオブジェクトの形式を、検証なしに決めつけることになる。認証済みの復号ボディを実測するほうが、改ざん時に復号が失敗して fail closed になる。ストリームは一度だけ開く。測り直しのために開き直すと、レスポンスごとに S3 `GetObject` と KMS 復号がもう一回走る。

## 既知の制約: 平文がローカル一時ファイルにこぼれる

存在理由は「平文を S3 に置かない」ことだが、AWS SDK は平文をローカルの一時ファイルに書き出すことがある。

Guzzle の `Utils::streamFor()` は `php://temp` を開く。PHP はこれを2MiB(2,097,152バイト)未満はメモリで保ち、2MiB 以上なら実ファイルに書き出す。ファイルはモード0600で `sys_get_temp_dir()` に作られる。`stream_get_meta_data()` は書き出されたあとも `php://temp` と報告するので、ストリームのメタデータからは、ファイルができたかどうか分からない。

影響を受けるのは、文字列の `put()` / `write()`、復号後の `get()` / `read()` と `readStream()`、`response()` / `download()` / `serve()` だ。`readStream()` が返すリソースは切り離されているので、閉じるのは呼び出し側の責任で、異常終了(SIGKILL、OOM kill、セグフォ)では平文ファイルが残ることがある。

この制約に対して、書き込みだけ `php://memory` に寄せる案は検討したが採用しなかった。読み取り側には同じ仕組みがなく、SDK が復号後に内部で `php://temp` を作るからだ。運用側の対処として、`sys_temp_dir` を tmpfs か暗号化ボリュームに向けることを README に書いている。全体の安全性を変えられない書き込み専用の対策を足すより、制約として記録する方を選んだ。

## 使い始める

```sh
composer require j1nn0/laravel-encrypted-s3
```

`config/filesystems.php` にディスクを追加する。

```php
'encrypted-s3' => [
    'driver' => 'encrypted-s3',
    'key'    => env('AWS_ACCESS_KEY_ID'),
    'secret' => env('AWS_SECRET_ACCESS_KEY'),
    'region' => env('AWS_DEFAULT_REGION'),
    'bucket' => env('AWS_BUCKET'),
    'kms' => [
        'key_id' => env('AWS_ENCRYPTED_S3_KMS_KEY_ID'), // Required.
    ],
],
```

IAM は最低限 `kms:GenerateDataKey` と `kms:Decrypt`(設定した KMS キーに対して)、`s3:PutObject`、`s3:GetObject`、`s3:DeleteObject`、`s3:ListBucket` が必要。visibility 操作を使うなら `s3:GetObjectAcl` と `s3:PutObjectAcl` も要る。リソースはバケットとプレフィックス、KMS キーに絞る。

サーバーサイドコピーは `HeadObject` を2回使う(1回はエンベロープ検証、1回は SDK のコピー戦略選択)が、`s3:CopyObject` という IAM アクションは不要で、`s3:GetObject` と `s3:PutObject` で足りる。

## 設計判断は9件の ADR に残した

設計判断は `docs/adr/` に9件の ADR として残した。この記事で書いた判断のほとんどは、実際のリクエストトレースで問題を確かめてから、当初の設計を書き直して入ったものだ。

デフォルト ACL は2回方針が変わった(ADR 0002 → 0004 → 0008)。コピーの fail closed は、平文ソースのコピーを実トレースで確認してから入った(ADR 0009)。セキュリティパッケージでは、安全性を静かに弱める変更が diff の上では正しく見える。だから判断を「なぜ」まで含めて記録し、テストで固定する。

テストは Unit + Feature で138件。CI は PHP 8.2〜8.5 × Laravel 12/13 のマトリクスで回している。実 S3/KMS 互換の確認には Moto コンテナを使う統合スイートを用意したが、Moto はモックなので、最終的には実 AWS で確かめるしかないと README に書いてある。

今は Packagist に v1.0.0-RC3 まで出していて、実 AWS での確認が終わり次第 v1.0.0 をリリースする予定だ。安定版を待つ場合はそのタイミングまで待ってほしい。

このパッケージは、[`agent-orchestration` スキル]({{< ref "agent-orchestration-skill" >}})を実際に使いながら開発した。スキルとリポジトリの話は前回の記事に書き、ここではパッケージの中身を書いた。

ソースは [GitHub](https://github.com/j1nn0/laravel-encrypted-s3)、[Packagist](https://packagist.org/packages/j1nn0/laravel-encrypted-s3) で公開している。現在は RC の段階で、本番投入は v1.0.0 のリリース後を検討してほしい。
