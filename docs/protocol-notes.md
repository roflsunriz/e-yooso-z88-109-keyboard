# Z88 109 HIDプロトコル調査記録

## 実機識別

- USB VID/PID: `258A:0049`
- Manufacturer: `BY Tech`
- Product: `Gaming Keyboard`
- Interface 1にReport ID `5`、`6`、`8`を含むvendor-defined HID collectionが存在する。
- Report 8の全長は382バイト、Report 6の全長は1032バイトである。

VID/PIDだけでは機種を特定できない。同じ値はRedragon K617などでも使われているため、他機種向けパケットを互換とみなしてはならない。

## 2026-08-23 Report 8実機試験

[Sinodragon](https://github.com/EvanSunde/Sinodragon)および[fizz-rgb](https://github.com/MrSchrodingers/fizz-rgb)でK617向けに検証されている次のReport 8形式を試験した。

- ヘッダー: `08 0A 7A 01`
- 全長: 382バイト
- 本文: RGB 3バイト組
- 送信先: Interface 1の`Col08`

結果は次のとおり。

1. 全スロットへ赤 `(16, 0, 0)` を送信すると、色は表示されず即時消灯した。
2. 赤を`32`、`255`へ上げても、色は表示されず即時消灯した。
3. `Col03`経由のReport 8送信は送信長`-1`で拒否された。
4. Report 5へK617向けハンドシェイク`05 83 B6 00 00 00`を送ってから最大赤を送信しても、即時消灯した。
5. Report 5は試験前の`05 01 02 00 00 00`へ復元できた。
6. 各試験後は`Fn+M`でキーボード内蔵の発光モードへ復帰できた。

単一パケットだけでは発色しなかったが、BYK916動画モードの初期化としてゼロ色Report 8を16ms間隔で3回送信した後は、最大赤を正常表示できた。したがってReport 8形式は互換であり、[同系統BYK916の実装](https://www.reddit.com/r/SignalRGB/comments/1rop4lx/release_havit_kb885l_byk916_native_60fps/)と同じ3回の初期化シーケンスが必須である。HID APIが382バイトを受理したことだけでなく、実際のLED発色を受入条件とする。

## 2026-08-23 ファームウェア退避

- LJMP変更`0x55`、書込み`0x57`、消去`0x45`を送信しない独自読出し経路で、61,440バイトを取得した。
- SHA-256: `0de319edb11a4a532bf27cc263a6491b4a98e666a627b0df6cd51a547f9fabe8`
- ファームウェア識別文字列: `CK 8907 3.0`、`CK 8907 5.0`
- Windowsでは再起動命令後にUSBデバイスが切断状態となり、ケーブルの抜き差しで通常モードへ復帰した。

## 次の調査対象

1. 126個のRGBスロットとJIS 109キーの対応を割り出す。
2. Codexのエージェント状態を取得し、Report 8の色・アニメーションへ変換する。
3. Report 6が内蔵エフェクト設定だけか、キー別色データも保持するかを補助的に解析する。

K617用のReport 6テンプレートを、そのまま本機へ送信してはならない。
