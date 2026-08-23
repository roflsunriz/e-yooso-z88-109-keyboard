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

以上から、K617向けReport 8直接RGB方式は本機では非互換と判断する。HID APIが382バイトを受理したことだけを成功扱いせず、実際のLED発色を受入条件とする。

## 次の調査対象

1. 本機専用ソフトウェアまたはUSBキャプチャからReport 6の実パケットを取得する。
2. Report 6が内蔵エフェクト設定だけか、キー別色データも保持するかを解析する。
3. 本機の現在ファームウェアを安全に読み出せる手段と復旧方法を確保してから、8051コード内のReport 6/8処理を解析する。

K617用のReport 6テンプレートを、そのまま本機へ送信してはならない。
