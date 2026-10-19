# 調査知見

- 対象は `Z-88RGB109` / `Z88RGB109JP`、USB `258A:0049`、Interface 1。直接RGBは `Col08`/Report 8、ISP commandは `Col05`/Report 5、転送は `Col06`/Report 6。VID/PIDは別機種も使うためdescriptor一式と実発色で識別する。
- Report 8は `08 0A 7A 01` + 126 slotのR-G-Bで全長382 bytes。動画mode開始には全slot 0を16ms間隔で3回送る。単発送信は成功byte数を返しても消灯するだけなので、実発色を確認する。終了後は `Fn+M` で内蔵発光modeへ戻せる。
- 126 slotとJIS 109 keyの完全対応は未確定。現状は全体色だけに使い、key単位機能は対応表を実測してから追加する。
- firmwareは61,440 bytes、SHA-256 `0de319edb11a4a532bf27cc263a6491b4a98e666a627b0df6cd51a547f9fabe8`、識別文字列 `CK 8907 3.0` / `CK 8907 5.0`。退避経路は `0x75`、`0x52`、`0x5A` だけを許可し、`0x55`/`0x57`/`0x45` を拒否する。
- `sinowisp read` は読取り前に破壊的な `0x55` を送り得るため使わない。退避後はUSBが切断状態になることがあり、物理的な抜差しで通常modeへ戻す。
- Codex Hooksはinstall後に定義を確認して信頼し、新しく開いたtaskで初回検証する。現在taskが自動reloadすると仮定しない。複数taskでは最後のSessionStart/UserPromptSubmitを優先し、tab focusだけでは切り替わらない。
- LED連携失敗でCodex本体を止めず、専用logへ残す。SessionEndは消灯、処理/完了/承認/失敗は既定の青/緑/黄/赤へ対応する。
- `tests/test_documentation.py` とrelease builderが `findings.md` の識別値・初期化条件・復帰操作・firmware hashを参照する。文書を再配置するときはtestと配布ZIPの明示listも同時更新する。
