---
title: "Vortex Keyboard M0110のVIAキーマップ"
images:
  - /images/m0110-via-keymap/ogp.png
slug: m0110-via-keymap
date: 2026-07-16
tags:
  - keyboard
  - m0110
draft: false
---

## この記事で分かること

- Vortex Keyboard M0110のキーマップをVIAで設定する理由
- レイヤー0〜3の構成と、実際に使っているのはどこまでか
- 登録している4つのマクロの用途とキー割り当て

キーボード自体は[2026年の開発環境](/posts/dev-environment-2026/)で紹介した。
今回はそのキーマップの中身を記録しておく。

## VIAでキーマップを組む

[Vortex Keyboard M0110](https://vortexgear.store/en-jp/products/m0110-qmk-via-vial-version)はQMK、VIA、Vialの3方式でキーマップを変更できる。
QMKはファームウェアをビルドして書き込む方式で、Vialは専用アプリから設定する方式だ。
自分はブラウザだけで完結する[VIA](https://caniusevia.com/)を使っている。

VIAはレイヤーごとにキー配列を画面上で編集でき、変更はキーボードに即座に反映される。
ビルド環境を用意する必要がないので、キー配列を試行錯誤する分にはこれで十分だった。

## レイヤー構成

レイヤーは0から3まで4つある。

レイヤー0は通常のHHKB配列そのもので、特に変えていない。

![レイヤー0のキー配列](/images/m0110-via-keymap/layer0.webp)

レイヤー1はHHKBのFnキーとの組み合わせに相当するレイヤーで、矢印キーやファンクションキーをここに割り当てている。
こちらも標準的なHHKB配列に沿った構成で、CapsLockキーは不要なので配置していない。

![レイヤー1のキー配列](/images/m0110-via-keymap/layer1.webp)

レイヤー2にはマウス操作といくつかのマクロを割り当てているが、実際にはほぼ使っていない。
用意はしたものの、トラックパッドで事足りてしまっている。

![レイヤー2のキー配列](/images/m0110-via-keymap/layer2.webp)

レイヤー3は完全に未使用のまま残っている。

![レイヤー3のキー配列](/images/m0110-via-keymap/layer3.webp)

## マクロ

マクロはM0からM3まで4つ登録している。
仮想マシンでWindows 11を動かしているときに使う、Windows側のショートカットキーだ。
ただし実際に使っているのはM0とM1の2つで、M2とM3は登録しただけで使っていない。

| マクロ | キー割り当て | 用途 |
| --- | --- | --- |
| M0 | Alt+F4 | Windowsをすぐシャットダウンしたいときに使う |
| M1 | Ctrl+Alt+Delete | タスクマネージャーなどを呼び出す |
| M2 | Ctrl+Alt+Insert | 登録しただけで使っていない |
| M3 | Ctrl+Alt+Esc | 登録しただけで使っていない |

Mac本体のキーボードだけではこの4つの組み合わせを一発で押せないため、マクロにしてある。

![M0のマクロ設定](/images/m0110-via-keymap/m0.webp)
![M1のマクロ設定](/images/m0110-via-keymap/m1.webp)
![M2のマクロ設定](/images/m0110-via-keymap/m2.webp)
![M3のマクロ設定](/images/m0110-via-keymap/m3.webp)

## まとめ

レイヤー0と1はHHKB配列のままで、実際に手を入れているのはレイヤー2の一部とマクロのM0、M1だけだ。
派手な設定ではないが、仮想マシンをシャットダウンするM0だけは地味に手放せない。

VIAでの設定を試すなら[caniusevia.com](https://caniusevia.com/)から対応キーボードを確認できる。
